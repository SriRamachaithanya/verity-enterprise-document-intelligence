import json
import logging
from typing import Any

from src.agent.models import ExecutionPlan, IntentResult, ToolCallPlan, UserIntent

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS_BUDGET = 5
MAX_PLANNING_ITERATIONS = 2


class PlanningEngine:
    """
    Deterministic Bounded Planning Engine.
    Constructs multi-step execution graphs adhering to strict budget limits:
    - Maximum 5 tool calls per user turn.
    - Maximum 2 planning iterations.
    - Deduplicates redundant calls.
    - Enforces approved MCP tool schemas.
    """

    def __init__(self, max_tool_calls: int = MAX_TOOL_CALLS_BUDGET):
        self.max_tool_calls = max_tool_calls

    def create_initial_plan(
        self,
        intent_result: IntentResult,
        user_query: str,
        allowlist: set[str],
    ) -> ExecutionPlan:
        """Construct initial execution plan based on resolved intent and extracted entities."""
        entities = intent_result.extracted_entities
        planned_calls: list[ToolCallPlan] = []

        intent = intent_result.intent

        if intent == UserIntent.DOCUMENT_DISCOVERY:
            if "list_documents" in allowlist:
                planned_calls.append(
                    ToolCallPlan(
                        tool_name="list_documents",
                        arguments={"limit": 20, "offset": 0},
                        rationale="List ingested enterprise documents in catalog.",
                        priority=1,
                    )
                )

        elif intent == UserIntent.DOCUMENT_SEARCH:
            search_query = entities.get("query_text") or user_query
            args: dict[str, Any] = {"query": search_query, "top_k": 5}
            if entities.get("document_id"):
                args["document_id"] = entities["document_id"]
            if "search_documents" in allowlist:
                planned_calls.append(
                    ToolCallPlan(
                        tool_name="search_documents",
                        arguments=args,
                        rationale=f"Execute hybrid search for query: '{search_query}'.",
                        priority=1,
                    )
                )

        elif intent == UserIntent.CITATION_VERIFICATION:
            if entities.get("chunk_id") and "get_citation" in allowlist:
                planned_calls.append(
                    ToolCallPlan(
                        tool_name="get_citation",
                        arguments={"chunk_id": entities["chunk_id"], "include_surrounding_context": True},
                        rationale=f"Fetch exact verbatim text and hash verification for chunk '{entities['chunk_id']}'.",
                        priority=1,
                    )
                )
            elif "search_documents" in allowlist:
                planned_calls.append(
                    ToolCallPlan(
                        tool_name="search_documents",
                        arguments={"query": user_query, "top_k": 3},
                        rationale="Search for candidate chunk matching citation query.",
                        priority=1,
                    )
                )

        elif intent == UserIntent.COMPLIANCE_EVALUATION:
            fw_id = entities.get("framework_id", "SOC2")
            req_id = entities.get("requirement_id")
            args = {"framework_id": fw_id}
            if req_id:
                args["requirement_id"] = req_id
            if "evaluate_compliance" in allowlist:
                planned_calls.append(
                    ToolCallPlan(
                        tool_name="evaluate_compliance",
                        arguments=args,
                        rationale=f"Audit compliance requirements for framework '{fw_id}'.",
                        priority=1,
                    )
                )

        elif intent == UserIntent.COMPLIANCE_GAP_ANALYSIS:
            fw_id = entities.get("framework_id", "SOC2")
            args = {"framework_id": fw_id, "severity_filter": entities.get("severity_filter", "All")}
            if "gap_analysis" in allowlist:
                planned_calls.append(
                    ToolCallPlan(
                        tool_name="gap_analysis",
                        arguments=args,
                        rationale=f"Identify compliance gaps and remediation priorities for framework '{fw_id}'.",
                        priority=1,
                    )
                )

        elif intent == UserIntent.KNOWLEDGE_EXPLORATION:
            node_slug = entities.get("node_slug", "mfa-policy")
            if "get_related_knowledge" in allowlist:
                planned_calls.append(
                    ToolCallPlan(
                        tool_name="get_related_knowledge",
                        arguments={"node_id_or_slug": node_slug, "depth": 1},
                        rationale=f"Traverse knowledge graph for concept note '{node_slug}'.",
                        priority=1,
                    )
                )

        else:  # DOCUMENT_QA
            search_query = entities.get("query_text") or user_query
            if "search_documents" in allowlist:
                planned_calls.append(
                    ToolCallPlan(
                        tool_name="search_documents",
                        arguments={"query": search_query, "top_k": 5},
                        rationale=f"Retrieve top relevant evidence chunks for user question: '{search_query}'.",
                        priority=1,
                    )
                )

        # Truncate to maximum budget
        planned_calls = self._deduplicate_and_bound(planned_calls, executed_signatures=set())

        return ExecutionPlan(
            intent=intent,
            tool_calls=planned_calls,
            max_iterations=MAX_PLANNING_ITERATIONS,
            current_iteration=1,
            is_complete=len(planned_calls) == 0,
        )

    def refine_plan(
        self,
        current_plan: ExecutionPlan,
        executed_calls: list[Any],
        executed_signatures: set[str],
        allowlist: set[str],
    ) -> ExecutionPlan:
        """
        Evaluate intermediate results and generate subsequent tool calls (Iteration 2).
        For example: fetching full citations for top chunks retrieved in Iteration 1.
        """
        if current_plan.current_iteration >= current_plan.max_iterations:
            current_plan.is_complete = True
            return current_plan

        remaining_budget = self.max_tool_calls - len(executed_calls)
        if remaining_budget <= 0:
            current_plan.is_complete = True
            return current_plan

        next_calls: list[ToolCallPlan] = []

        # Follow-up for DOCUMENT_QA or DOCUMENT_SEARCH: retrieve verified citation for top result
        for exec_res in executed_calls:
            if exec_res.tool_name == "search_documents" and not exec_res.is_error and exec_res.parsed_data:
                results = exec_res.parsed_data.get("results", [])
                if results and "get_citation" in allowlist:
                    top_chunk = results[0]
                    chunk_id = top_chunk.get("chunk_id")
                    if chunk_id:
                        next_calls.append(
                            ToolCallPlan(
                                tool_name="get_citation",
                                arguments={"chunk_id": chunk_id, "include_surrounding_context": True},
                                rationale=f"Fetch cryptographic citation proof for top retrieved chunk '{chunk_id}'.",
                                priority=2,
                            )
                        )

            # Follow-up for COMPLIANCE_EVALUATION: retrieve citation for evidence chunk
            elif exec_res.tool_name == "evaluate_compliance" and not exec_res.is_error and exec_res.parsed_data:
                findings = exec_res.parsed_data.get("findings", [])
                for f in findings:
                    evidence = f.get("evidence")
                    if evidence and evidence.get("chunk_id") and "get_citation" in allowlist:
                        cid = evidence["chunk_id"]
                        next_calls.append(
                            ToolCallPlan(
                                tool_name="get_citation",
                                arguments={"chunk_id": cid, "include_surrounding_context": False},
                                rationale=f"Verify evidence chunk '{cid}' for requirement '{f.get('requirement_code')}'.",
                                priority=2,
                            )
                        )
                        break  # Bounded: verify top finding evidence

        # Deduplicate against already executed and current calls
        filtered_calls = self._deduplicate_and_bound(
            next_calls,
            executed_signatures=executed_signatures,
            budget=remaining_budget,
        )

        return ExecutionPlan(
            intent=current_plan.intent,
            tool_calls=filtered_calls,
            max_iterations=current_plan.max_iterations,
            current_iteration=current_plan.current_iteration + 1,
            is_complete=len(filtered_calls) == 0,
        )

    def _deduplicate_and_bound(
        self,
        calls: list[ToolCallPlan],
        executed_signatures: set[str],
        budget: int = MAX_TOOL_CALLS_BUDGET,
    ) -> list[ToolCallPlan]:
        """Deduplicate calls by signature and enforce remaining budget."""
        unique_calls: list[ToolCallPlan] = []
        seen = set(executed_signatures)

        for c in calls:
            # Deterministic argument signature
            sig = f"{c.tool_name}:{json.dumps(c.arguments, sort_keys=True)}"
            if sig not in seen and len(unique_calls) < budget:
                seen.add(sig)
                unique_calls.append(c)

        return unique_calls

