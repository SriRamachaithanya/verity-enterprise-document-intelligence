import logging
import time
import uuid
from pathlib import Path
from typing import Literal

from src.agent.evidence_validator import EvidenceValidator
from src.agent.execution_engine import ExecutionEngine
from src.agent.guardrails import (
    detect_prompt_injection,
    sanitize_log_payload,
    sanitize_user_input,
)
from src.agent.intent_router import IntentRouter
from src.agent.mcp_client import MCPClientManager
from src.agent.models import AgentResponse, UserIntent
from src.agent.planner import PlanningEngine
from src.agent.response_generator import ResponseGenerator
from src.storage.db import DatabaseManager

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Principal Bounded Agent Orchestrator for VERITY.
    Directs the 8-stage bounded lifecycle over genuine MCP Client sessions.
    Guarantees evidence grounding, citation verification, prompt-injection defense,
    and automatic deterministic fallback when local LLM services are offline.
    """

    def __init__(
        self,
        db_manager: DatabaseManager | None = None,
        mcp_client: MCPClientManager | None = None,
        server_module: str = "src.mcp_server.server",
        env: dict[str, str] | None = None,
        cwd: Path | str | None = None,
    ):
        self.db = db_manager or DatabaseManager()
        server_env = dict(env or {})
        if self.db and hasattr(self.db, "db_path"):
            server_env.setdefault("SQLITE_DB_PATH", str(self.db.db_path))
            server_env.setdefault("VERITY_DB_PATH", str(self.db.db_path))
        self.mcp_client = mcp_client or MCPClientManager(
            server_module=server_module,
            env=server_env,
            cwd=cwd,
        )
        self.intent_router = IntentRouter()
        self.planner = PlanningEngine(max_tool_calls=5)
        self.execution_engine = ExecutionEngine(
            mcp_client=self.mcp_client,
            planner=self.planner,
            max_tool_calls=5,
        )
        self.evidence_validator = EvidenceValidator(db_manager=self.db)
        self.response_generator = ResponseGenerator()

    async def run(
        self,
        user_query: str,
        session_id: str | None = None,
    ) -> AgentResponse:
        """
        Execute an end-to-end evidence-grounded agent interaction turn.
        """
        turn_start = time.perf_counter()
        sess_id = session_id or f"sess_{uuid.uuid4().hex[:10]}"

        # ---------------------------------------------------------------------
        # Stage 1: Input Sanitization & Prompt-Injection Guardrail
        # ---------------------------------------------------------------------
        cleaned_query = sanitize_user_input(user_query)
        is_injection, injection_reason = detect_prompt_injection(cleaned_query)

        if is_injection:
            elapsed_ms = int((time.perf_counter() - turn_start) * 1000)
            logger.warning("Adversarial prompt injection intercepted in session %s: %s", sess_id, injection_reason)

            self.db.log_audit_event(
                session_id=sess_id,
                event_type="PROMPT_INJECTION_BLOCKED",
                step_number=1,
                input_payload={"raw_query": user_query, "reason": injection_reason},
                output_payload={"status": "REJECTED"},
                execution_time_ms=elapsed_ms,
            )

            return AgentResponse(
                session_id=sess_id,
                user_query=user_query,
                intent=UserIntent.DOCUMENT_QA,
                answer=(
                    "⚠️ **Security Guardrail Triggered**\n\n"
                    "The query contained phrases matching prohibited prompt-injection patterns "
                    f"({injection_reason}). In accordance with zero-trust defensive guidelines, "
                    "the request was safely intercepted and halted without executing backend tools."
                ),
                citations=[],
                compliance_status=None,
                confidence_score=1.0,
                human_review_required=True,
                tools_executed=[],
                execution_time_ms=elapsed_ms,
                fallback_mode_used=True,
            )

        # ---------------------------------------------------------------------
        # Stage 2: Intent Classification & Entity Extraction
        # ---------------------------------------------------------------------
        intent_result = self.intent_router.route(cleaned_query)
        logger.info(
            "Session %s resolved intent: %s (confidence=%.2f)",
            sess_id,
            intent_result.intent.value,
            intent_result.confidence,
        )

        # ---------------------------------------------------------------------
        # Stage 3 & 4: MCP Client Connection, Planning & Bounded Dispatch
        # ---------------------------------------------------------------------
        should_manage_connection = not self.mcp_client.is_connected
        if should_manage_connection:
            await self.mcp_client.connect()

        try:
            initial_plan = self.planner.create_initial_plan(
                intent_result=intent_result,
                user_query=cleaned_query,
                allowlist=self.mcp_client.allowlist,
            )

            tool_results = await self.execution_engine.execute_plan(initial_plan)
        finally:
            if should_manage_connection:
                await self.mcp_client.disconnect()

        # ---------------------------------------------------------------------
        # Stage 5 & 6: Evidence Harvesting & Citation Verification
        # ---------------------------------------------------------------------
        evidence_items = self.evidence_validator.extract_evidence_items(tool_results)
        validated_citations = self.evidence_validator.validate_citations(tool_results)

        # Compute Compliance Status and Confidence
        compliance_status: Literal["COVERED", "PARTIALLY_COVERED", "MISSING", "NOT_APPLICABLE"] | None = None
        human_review = any(not c.is_valid for c in validated_citations)
        confidence = intent_result.confidence

        for r in tool_results:
            if r.tool_name == "evaluate_compliance" and r.parsed_data and isinstance(r.parsed_data, dict):
                findings = r.parsed_data.get("findings", [])
                if findings:
                    statuses = {f.get("status") for f in findings}
                    if "MISSING" in statuses:
                        compliance_status = "MISSING"
                    elif "PARTIALLY_COVERED" in statuses:
                        compliance_status = "PARTIALLY_COVERED"
                    elif "COVERED" in statuses:
                        compliance_status = "COVERED"

                    if any(f.get("human_review_required") for f in findings):
                        human_review = True
                    conf_scores = [f.get("confidence_score", 0.8) for f in findings]
                    confidence = round(sum(conf_scores) / len(conf_scores), 2)

        # ---------------------------------------------------------------------
        # Stage 7: Grounded Response Synthesis (Ollama or Fallback)
        # ---------------------------------------------------------------------
        answer_text, fallback_used = await self.response_generator.generate_response(
            user_query=cleaned_query,
            intent=intent_result.intent,
            tool_results=tool_results,
            validated_citations=validated_citations,
            evidence_items=evidence_items,
        )

        elapsed_ms = int((time.perf_counter() - turn_start) * 1000)
        tools_executed = [r.tool_name for r in tool_results]

        # ---------------------------------------------------------------------
        # Stage 8: Audit Logging & Trace Assembly
        # ---------------------------------------------------------------------
        self.db.log_audit_event(
            session_id=sess_id,
            event_type="AGENT_TURN_COMPLETED",
            step_number=len(tools_executed) + 1,
            tool_name="AgentOrchestrator",
            input_payload=sanitize_log_payload({
                "user_query": cleaned_query,
                "intent": intent_result.intent.value,
                "planned_tools": [c.tool_name for c in initial_plan.tool_calls],
            }),
            output_payload=sanitize_log_payload({
                "tools_executed": tools_executed,
                "citations_count": len(validated_citations),
                "compliance_status": compliance_status,
                "fallback_mode": fallback_used,
            }),
            execution_time_ms=elapsed_ms,
        )

        return AgentResponse(
            session_id=sess_id,
            user_query=user_query,
            intent=intent_result.intent,
            answer=answer_text,
            citations=validated_citations,
            compliance_status=compliance_status,
            confidence_score=confidence,
            human_review_required=human_review,
            tools_executed=tools_executed,
            execution_time_ms=elapsed_ms,
            fallback_mode_used=fallback_used,
        )
