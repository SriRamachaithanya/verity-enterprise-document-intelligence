import json
import logging

from src.agent.mcp_client import MCPClientManager
from src.agent.models import ExecutionPlan, ToolExecutionResult
from src.agent.planner import PlanningEngine

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Coordinates plan execution through the official MCP Client over STDIO.
    Enforces budget limits, prevents duplicate invocations, and handles iterative refinement.
    """

    def __init__(
        self,
        mcp_client: MCPClientManager,
        planner: PlanningEngine,
        max_tool_calls: int = 5,
    ):
        self.client = mcp_client
        self.planner = planner
        self.max_tool_calls = max_tool_calls

    async def execute_plan(
        self,
        initial_plan: ExecutionPlan,
    ) -> list[ToolExecutionResult]:
        """
        Execute tool calls in bounded iterative rounds.
        Guarantees that total executed calls never exceed max_tool_calls.
        """
        executed_results: list[ToolExecutionResult] = []
        executed_signatures: set[str] = set()

        current_plan = initial_plan

        while not current_plan.is_complete and len(executed_results) < self.max_tool_calls:
            # 1. Execute current round of tool calls
            for planned_call in current_plan.tool_calls:
                if len(executed_results) >= self.max_tool_calls:
                    logger.warning("Reached maximum tool-call budget (%d).", self.max_tool_calls)
                    break

                # Signature deduplication check
                sig = f"{planned_call.tool_name}:{json.dumps(planned_call.arguments, sort_keys=True)}"
                if sig in executed_signatures:
                    logger.info("Skipping duplicate tool call: %s", sig)
                    continue

                executed_signatures.add(sig)

                # Execute over genuine MCP client
                logger.info(
                    "Executing MCP Tool [%d/%d]: %s",
                    len(executed_results) + 1,
                    self.max_tool_calls,
                    planned_call.tool_name,
                )
                res = await self.client.call_tool(
                    tool_name=planned_call.tool_name,
                    arguments=planned_call.arguments,
                )
                executed_results.append(res)

            # 2. Refine plan for next iteration if budget allows
            if len(executed_results) < self.max_tool_calls:
                current_plan = self.planner.refine_plan(
                    current_plan=current_plan,
                    executed_calls=executed_results,
                    executed_signatures=executed_signatures,
                    allowlist=self.client.allowlist,
                )
            else:
                break

        return executed_results
