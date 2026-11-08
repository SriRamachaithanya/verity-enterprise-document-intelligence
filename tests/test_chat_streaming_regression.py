import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.agent.models import AgentResponse, UserIntent, ValidatedCitation
from src.api.app import create_app
from src.api.dependencies import get_agent_orchestrator


@pytest.fixture
def test_client_with_mocks():
    """Create a FastAPI TestClient with configurable orchestrator mocks."""
    app = create_app()
    mock_agent = MagicMock()
    app.dependency_overrides[get_agent_orchestrator] = lambda: mock_agent
    client = TestClient(app)
    return client, mock_agent


def parse_sse_events(raw_sse_text: str) -> list[dict]:
    """Parse raw SSE text into structured list of event dictionaries."""
    events = []
    chunks = raw_sse_text.strip().split("\n\n")
    for chunk in chunks:
        if not chunk.strip():
            continue
        lines = chunk.strip().split("\n")
        event_type = "message"
        data_str = ""
        for line in lines:
            if line.startswith("event:"):
                event_type = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_str = line[len("data:"):].strip()
        data_json = json.loads(data_str) if data_str else {}
        events.append({"event": event_type, "data": data_json})
    return events


class TestChatStreamingRegression:
    """
    Regression test suite for SSE chat streaming post-generation lifecycle,
    event ordering, citation preservation, and failure mode reporting.
    """

    def test_successful_stream_with_citations_ends_with_done_no_error(self, test_client_with_mocks):
        """
        Acceptance Criteria:
        1. Agent generates a response with citations.
        2. Stream emits status -> tokens -> citations -> done in strict order.
        3. NO error event is emitted after a successfully generated response.
        4. Citations preserve exact_quote, chunk_id, and verified status.
        """
        client, mock_agent = test_client_with_mocks

        # Mock citation with ValidatedCitation schema
        mock_citation = ValidatedCitation(
            chunk_id="chk_access_001",
            document_id="doc_pol_001",
            document_name="Access_Control_Policy.pdf",
            page_number=3,
            locator="Section 2.1, Para 4",
            section_heading="Multi-Factor Authentication",
            exact_text="All workforce users must authenticate with MFA.",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            is_valid=True,
            validation_notes="Cryptographically verified",
        )

        mock_agent_response = AgentResponse(
            session_id="sess_regression_test_1",
            user_query="What does the access control policy require?",
            intent=UserIntent.DOCUMENT_QA,
            answer="The access control policy requires all workforce members to use multi-factor authentication (MFA).",
            citations=[mock_citation],
            compliance_status="COVERED",
            confidence_score=0.95,
            human_review_required=False,
            tools_executed=["search_documents", "get_citation"],
            execution_time_ms=120,
        )

        mock_agent.run = AsyncMock(return_value=mock_agent_response)

        resp = client.post(
            "/api/v1/chat/stream",
            headers={"X-API-Key": "verity-admin-secret-key"},
            json={"query": "What does the access control policy require?"},
        )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        events = parse_sse_events(resp.text)
        event_types = [e["event"] for e in events]

        # 1. Strict sequence checks
        assert "status" in event_types
        assert "token" in event_types
        assert "citation" in event_types
        assert event_types[-1] == "done", f"Stream must end with 'done', but ended with '{event_types[-1]}'"

        # 2. Critical regression check: NO ERROR EVENT after successful tokens
        assert "error" not in event_types, f"Error event unexpectedly found in successful stream: {events}"

        # 3. Verify citation structure
        citation_events = [e for e in events if e["event"] == "citation"]
        assert len(citation_events) == 1
        c_data = citation_events[0]["data"]
        assert c_data["chunk_id"] == "chk_access_001"
        assert c_data["document_name"] == "Access_Control_Policy.pdf"
        assert c_data["locator"] == "Section 2.1, Para 4"
        assert c_data["exact_quote"] == "All workforce users must authenticate with MFA."
        assert c_data["verified"] is True

        # 4. Verify terminal done payload
        done_event = events[-1]
        assert done_event["data"]["session_id"] == "sess_regression_test_1"
        assert done_event["data"]["intent"] == "document_qa"
        assert done_event["data"]["confidence_score"] == 0.95
        assert done_event["data"]["compliance_status"] == "COVERED"

    def test_genuine_failure_is_reported_with_error_event(self, test_client_with_mocks):
        """
        Acceptance Criteria:
        1. When agent execution raises an unhandled internal exception,
           a genuine error event must still be reported.
        2. Terminal event is 'error' with INTERNAL_ERROR code.
        3. No 'done' event is emitted.
        """
        client, mock_agent = test_client_with_mocks

        # Simulate genuine backend failure in agent
        mock_agent.run = AsyncMock(side_effect=RuntimeError("Underlying vector store corrupt"))

        resp = client.post(
            "/api/v1/chat/stream",
            headers={"X-API-Key": "verity-admin-secret-key"},
            json={"query": "Summarize access controls"},
        )

        assert resp.status_code == 200
        events = parse_sse_events(resp.text)
        event_types = [e["event"] for e in events]

        # Verify error is reported
        assert "error" in event_types
        assert "done" not in event_types

        error_event = next(e for e in events if e["event"] == "error")
        assert error_event["data"]["code"] == "INTERNAL_ERROR"
        assert error_event["data"]["message"] == "Agent processing failure."

    def test_timeout_failure_is_reported_with_timeout_code(self, test_client_with_mocks):
        """
        Acceptance Criteria:
        1. When agent execution exceeds timeout limit,
           an error event with code 'TIMEOUT' must be emitted.
        """
        client, mock_agent = test_client_with_mocks

        # Simulate asyncio.TimeoutError
        mock_agent.run = AsyncMock(side_effect=TimeoutError())

        resp = client.post(
            "/api/v1/chat/stream",
            headers={"X-API-Key": "verity-admin-secret-key"},
            json={"query": "Long running query"},
        )

        assert resp.status_code == 200
        events = parse_sse_events(resp.text)
        event_types = [e["event"] for e in events]

        assert "error" in event_types
        assert "done" not in event_types

        error_event = next(e for e in events if e["event"] == "error")
        assert error_event["data"]["code"] == "TIMEOUT"
        assert "timed out" in error_event["data"]["message"].lower()

    def test_synchronous_chat_preserves_citations_and_verified(self, test_client_with_mocks):
        """
        Regression test for non-streaming /api/v1/chat endpoint:
        Ensure CitationItem formatting does not fail with AttributeError on c.verified.
        """
        client, mock_agent = test_client_with_mocks

        mock_citation = ValidatedCitation(
            chunk_id="chk_soc2_002",
            document_id="doc_soc2_001",
            document_name="SOC2_Evidence.pdf",
            page_number=1,
            locator="Page 1, Para 2",
            section_heading="Logical Access",
            exact_text="Access permissions are reviewed quarterly.",
            sha256_hash="abcdef1234567890",
            is_valid=True,
        )

        mock_agent_response = AgentResponse(
            session_id="sess_sync_test",
            user_query="How often are permissions reviewed?",
            intent=UserIntent.DOCUMENT_QA,
            answer="Permissions are reviewed quarterly.",
            citations=[mock_citation],
            confidence_score=0.9,
            tools_executed=["search_documents"],
        )

        mock_agent.run = AsyncMock(return_value=mock_agent_response)

        resp = client.post(
            "/api/v1/chat",
            headers={"X-API-Key": "verity-admin-secret-key"},
            json={"query": "How often are permissions reviewed?"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["citations"]) == 1
        assert data["citations"][0]["chunk_id"] == "chk_soc2_002"
        assert data["citations"][0]["exact_quote"] == "Access permissions are reviewed quarterly."
        assert data["citations"][0]["verified"] is True

