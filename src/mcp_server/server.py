import logging
import sys

from fastmcp import FastMCP

from src.mcp_server.dependencies import cleanup_dependencies
from src.mcp_server.tools import (
    evaluate_compliance,
    gap_analysis,
    get_citation,
    get_document_metadata,
    get_related_knowledge,
    list_documents,
    search_documents,
)

# Crucial for STDIO MCP: stdout is exclusively reserved for JSON-RPC 2.0 frames.
# All logging and diagnostics MUST be routed to stderr.
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("verity.mcp_server")


def create_mcp_server() -> FastMCP:
    """
    Factory function to configure and instantiate the FastMCP server
    with the seven official VERITY document intelligence tools.
    """
    mcp = FastMCP(
        name="verity-compliance-server",
        instructions=(
            "VERITY Enterprise Document Intelligence & Compliance Agent MCP Server. "
            "Provides grounded document retrieval, hybrid search, citation verification, "
            "compliance evaluation, gap analysis, and knowledge graph exploration."
        ),
    )

    # Register the seven MCP tools
    mcp.tool()(list_documents)
    mcp.tool()(search_documents)
    mcp.tool()(get_document_metadata)
    mcp.tool()(get_citation)
    mcp.tool()(evaluate_compliance)
    mcp.tool()(gap_analysis)
    mcp.tool()(get_related_knowledge)

    logger.info("FastMCP server initialized with 7 official tools.")
    return mcp


server = create_mcp_server()


def main() -> None:
    """Entrypoint to launch the FastMCP server over STDIO transport."""
    try:
        logger.info("Starting VERITY FastMCP Server on STDIO transport...")
        server.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server received interrupt signal, shutting down...")
    except Exception as exc:  # noqa: BLE001
        logger.error("FastMCP server terminated with error: %s", exc)
    finally:
        cleanup_dependencies()
        logger.info("Cleanup completed, exiting.")


if __name__ == "__main__":
    main()

