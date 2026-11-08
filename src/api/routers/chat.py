import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from src.agent.orchestrator import AgentOrchestrator
from src.api.config import get_api_config
from src.api.dependencies import get_agent_orchestrator, get_agent_semaphore
from src.api.schemas.chat import ChatRequest, ChatResponse, CitationItem
from src.api.security.auth import AuthenticatedUser, require_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["Agent Chat & Orchestration"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Agent Chat Turn",
    description="Execute an evidence-grounded agent interaction turn over genuine MCP tools with verifiable citations.",
)
async def chat_interaction(
    req: ChatRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_user)],
    agent: Annotated[AgentOrchestrator, Depends(get_agent_orchestrator)],
    semaphore: Annotated[asyncio.Semaphore, Depends(get_agent_semaphore)],
) -> ChatResponse:
    config = get_api_config()
    start_time = time.perf_counter()

    # Bounded concurrency guard to protect CPU & memory
    try:
        async with semaphore:
            agent_task = agent.run(user_query=req.query, session_id=req.session_id)
            result = await asyncio.wait_for(agent_task, timeout=config.agent_timeout_seconds)
    except TimeoutError:
        logger.error("Agent execution exceeded timeout limit of %.1fs", config.agent_timeout_seconds)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Agent reasoning exceeded processing timeout limit ({config.agent_timeout_seconds:.1f}s).",
        ) from None
    except Exception as exc:
        logger.exception("Agent interaction failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while executing the compliance agent.",
        ) from exc

    total_time_ms = int((time.perf_counter() - start_time) * 1000)

    # Format citations
    citations = [
        CitationItem(
            chunk_id=c.chunk_id,
            document_name=c.document_name,
            page_number=c.page_number,
            section_heading=c.section_heading,
            locator=c.locator,
            exact_quote=getattr(c, "exact_quote", getattr(c, "exact_text", "")),
            verified=getattr(c, "verified", getattr(c, "is_valid", True)),
        )
        for c in result.citations
    ]

    intent_val = result.intent.value if hasattr(result.intent, "value") else str(result.intent)

    return ChatResponse(
        session_id=result.session_id,
        query=req.query,
        intent=intent_val,
        answer=result.answer,
        citations=citations,
        compliance_status=result.compliance_status,
        confidence_score=result.confidence_score,
        human_review_required=result.human_review_required,
        execution_time_ms=total_time_ms,
        tools_executed=result.tools_executed,
    )


@router.post(
    "/stream",
    summary="Agent Chat Turn (SSE Stream)",
    description="Server-Sent Events (SSE) streaming endpoint delivering incremental agent tokens and status updates.",
)
async def chat_stream_interaction(
    req: ChatRequest,
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(require_user)],
    agent: Annotated[AgentOrchestrator, Depends(get_agent_orchestrator)],
    semaphore: Annotated[asyncio.Semaphore, Depends(get_agent_semaphore)],
) -> StreamingResponse:
    config = get_api_config()

    async def event_generator() -> AsyncGenerator[str, None]:
        session_id = req.session_id or "ephemeral"
        done_emitted = False
        tokens_emitted = 0

        # Stage 1: Planning status
        logger.info("[SSE Stage 1] Formulating plan for query: '%s' (session_id=%s)", req.query[:80], session_id)
        yield f"event: status\ndata: {json.dumps({'stage': 'planning', 'message': 'Sanitizing query and formulating plan...'})}\n\n"
        await asyncio.sleep(0.01)

        if await request.is_disconnected():
            logger.info("[SSE Disconnect] Client disconnected before agent execution (session_id=%s)", session_id)
            return

        try:
            # Stage 2: Bounded agent execution
            async with semaphore:
                logger.info("[SSE Stage 2] Acquired execution semaphore. Running agent (session_id=%s)...", session_id)
                yield f"event: status\ndata: {json.dumps({'stage': 'execution', 'message': 'Executing MCP tools and verifying evidence...'})}\n\n"

                agent_task = agent.run(user_query=req.query, session_id=req.session_id)
                result = await asyncio.wait_for(agent_task, timeout=config.agent_timeout_seconds)

            logger.info(
                "[SSE Stage 2 Complete] Agent returned answer (%d chars, %d citations, tools=%s, session_id=%s)",
                len(result.answer),
                len(result.citations),
                result.tools_executed,
                result.session_id,
            )

            if await request.is_disconnected():
                logger.info("[SSE Disconnect] Client disconnected after agent execution (session_id=%s)", result.session_id)
                return

            # Stage 3: Answer content streaming
            logger.info("[SSE Stage 3] Streaming answer tokens for session %s...", result.session_id)
            words = result.answer.split(" ")
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                if await request.is_disconnected():
                    logger.info("[SSE Disconnect] Client disconnected during answer stream (session_id=%s)", result.session_id)
                    return
                slice_text = " ".join(words[i : i + chunk_size])
                if i + chunk_size < len(words):
                    slice_text += " "
                yield f"event: token\ndata: {json.dumps({'token': slice_text})}\n\n"
                tokens_emitted += 1
                await asyncio.sleep(0.015)

            # Stage 4: Verified citations streaming
            logger.info("[SSE Stage 4] Streaming %d citations for session %s...", len(result.citations), result.session_id)
            for idx, c in enumerate(result.citations):
                citation_verified = getattr(c, "verified", getattr(c, "is_valid", True))
                citation_quote = getattr(c, "exact_quote", getattr(c, "exact_text", ""))
                c_data = {
                    "chunk_id": c.chunk_id,
                    "document_name": c.document_name,
                    "page_number": c.page_number,
                    "section_heading": c.section_heading,
                    "locator": c.locator,
                    "exact_quote": citation_quote,
                    "verified": citation_verified,
                }
                logger.debug(
                    "[SSE Stage 4] Emitting citation %d/%d (chunk_id=%s, verified=%s)",
                    idx + 1,
                    len(result.citations),
                    c.chunk_id,
                    citation_verified,
                )
                yield f"event: citation\ndata: {json.dumps(c_data)}\n\n"

            # Stage 5: Terminal completion event
            intent_val = result.intent.value if hasattr(result.intent, "value") else str(result.intent)
            done_payload = {
                "session_id": result.session_id,
                "intent": intent_val,
                "confidence_score": result.confidence_score,
                "compliance_status": result.compliance_status,
                "human_review_required": result.human_review_required,
                "tools_executed": result.tools_executed,
            }
            logger.info("[SSE Stage 5] Emitting terminal 'done' event for session %s", result.session_id)
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
            done_emitted = True

        except asyncio.CancelledError:
            logger.info("[SSE Cancelled] Stream cancelled by client or runtime (session_id=%s)", session_id)
            raise
        except TimeoutError:
            logger.error("[SSE Timeout] Agent execution timed out after %.1fs (session_id=%s)", config.agent_timeout_seconds, session_id)
            if not done_emitted:
                yield f"event: error\ndata: {json.dumps({'code': 'TIMEOUT', 'message': 'Agent reasoning timed out.'})}\n\n"
        except Exception as exc:
            logger.exception("[SSE Exception] Uncaught error during chat stream (session_id=%s): %s", session_id, exc)
            if not done_emitted:
                yield f"event: error\ndata: {json.dumps({'code': 'INTERNAL_ERROR', 'message': 'Agent processing failure.'})}\n\n"
            else:
                logger.warning(
                    "[SSE Post-Done] Exception occurred after 'done' event already emitted; suppressed duplicate terminal error (session_id=%s): %s",
                    session_id,
                    exc,
                )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
