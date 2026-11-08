import asyncio
import json
import logging
import os
import sys
import time
from contextlib import AsyncExitStack
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from src.agent.guardrails import enforce_tool_allowlist
from src.agent.models import ToolExecutionResult

logger = logging.getLogger(__name__)

DEFAULT_TOOL_TIMEOUT_SECONDS = 8.0


class MCPClientManager:
    """
    Asynchronous MCP Client managing an isolated FastMCP STDIO subprocess.
    Provides dynamic tool discovery, allowlist validation, and bounded tool execution.
    """

    def __init__(
        self,
        server_module: str = "src.mcp_server.server",
        env: dict[str, str] | None = None,
        cwd: Path | str | None = None,
    ):
        self.server_module = server_module
        self.custom_env = env or {}
        self.cwd = cwd or Path.cwd()
        self._exit_stack = AsyncExitStack()
        self.session: ClientSession | None = None
        self._tools_cache: dict[str, Any] = {}
        self.allowlist: set[str] = set()
        self.is_connected: bool = False

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        """Spawn the FastMCP server subprocess over STDIO and perform MCP handshake."""
        if self.is_connected:
            return

        merged_env = {
            **os.environ,
            "PYTHONUNBUFFERED": "1",
            **self.custom_env,
        }

        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", self.server_module],
            env=merged_env,
            cwd=str(self.cwd),
        )

        try:
            logger.info("Spawning FastMCP STDIO subprocess (%s)...", self.server_module)
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(params)
            )
            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            # Handshake
            init_res = await self.session.initialize()
            logger.info("MCP Session initialized. Server: %s", init_res.server_info.name)

            # Dynamic tool discovery
            await self.discover_tools()
            self.is_connected = True
        except Exception as exc:
            logger.error("Failed to connect to FastMCP server: %s", exc)
            await self.disconnect()
            raise ConnectionError(f"FastMCP connection failed: {exc}") from exc

    async def discover_tools(self) -> dict[str, Any]:
        """Dynamically discover available tools via tools/list."""
        if not self.session:
            raise RuntimeError("MCP Client is not connected.")

        tools_result = await self.session.list_tools()
        self._tools_cache = {t.name: t for t in tools_result.tools}
        self.allowlist = set(self._tools_cache.keys())
        logger.info("Discovered %d MCP tools: %s", len(self.allowlist), sorted(self.allowlist))
        return self._tools_cache

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: float = DEFAULT_TOOL_TIMEOUT_SECONDS,
    ) -> ToolExecutionResult:
        """
        Execute an approved MCP tool over STDIO with timeout and error containment.
        """
        start_time = time.perf_counter()

        if not self.is_connected or not self.session:
            return ToolExecutionResult(
                tool_name=tool_name,
                arguments=arguments,
                raw_text="",
                is_error=True,
                error_message="MCP Client is not connected.",
                execution_time_ms=0,
            )

        # Enforce allowlist
        if not enforce_tool_allowlist(tool_name, self.allowlist):
            logger.warning("Blocked invocation of non-allowlisted tool: '%s'", tool_name)
            return ToolExecutionResult(
                tool_name=tool_name,
                arguments=arguments,
                raw_text="",
                is_error=True,
                error_message=f"Tool '{tool_name}' is not in the approved MCP allowlist: {sorted(self.allowlist)}",
                execution_time_ms=0,
            )

        try:
            logger.debug("Dispatching MCP tools/call: %s (timeout=%.1fs)", tool_name, timeout)
            res = await asyncio.wait_for(
                self.session.call_tool(tool_name, arguments),
                timeout=timeout,
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            raw_text = res.content[0].text if (res.content and len(res.content) > 0) else ""
            is_err = getattr(res, "is_error", False)

            parsed: dict[str, Any] | list[Any] | None = None
            if raw_text and not is_err:
                try:
                    parsed = json.loads(raw_text)
                except Exception:  # noqa: BLE001
                    parsed = None

            return ToolExecutionResult(
                tool_name=tool_name,
                arguments=arguments,
                raw_text=raw_text,
                parsed_data=parsed,
                is_error=is_err,
                error_message=raw_text if is_err else None,
                execution_time_ms=elapsed_ms,
            )
        except TimeoutError:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("Tool '%s' timed out after %.1fs", tool_name, timeout)
            return ToolExecutionResult(
                tool_name=tool_name,
                arguments=arguments,
                raw_text="",
                is_error=True,
                error_message=f"Execution timed out after {timeout:.1f}s",
                execution_time_ms=elapsed_ms,
            )
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("Error executing tool '%s': %s", tool_name, exc)
            return ToolExecutionResult(
                tool_name=tool_name,
                arguments=arguments,
                raw_text="",
                is_error=True,
                error_message=str(exc),
                execution_time_ms=elapsed_ms,
            )

    async def disconnect(self) -> None:
        """Close MCP session and terminate subprocess."""
        if not self.is_connected and not self.session:
            return
        logger.info("Closing MCP Client connection...")
        try:
            await self._exit_stack.aclose()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error during MCP disconnect: %s", exc)
        finally:
            self.session = None
            self.is_connected = False
            self.allowlist.clear()
            self._tools_cache.clear()
            logger.info("MCP Client disconnected.")
