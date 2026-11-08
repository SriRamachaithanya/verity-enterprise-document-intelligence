import logging

from src.mcp_server.dependencies import get_knowledge_service
from src.schemas.mcp import RelatedKnowledgeResponse

logger = logging.getLogger(__name__)


def get_related_knowledge(
    node_id_or_slug: str,
    depth: int = 1,
) -> RelatedKnowledgeResponse:
    """
    Explore the Obsidian-style knowledge graph to retrieve linked notes, backlinks, and regulatory cross-references.

    Args:
        node_id_or_slug: Note ID or note slug (e.g. 'encryption-standard', 'mfa-policy').
        depth: Graph traversal depth (1 or 2, strict maximum of 2 for MCP tool). Default is 1.

    Returns:
        RelatedKnowledgeResponse with root note, outgoing wiki links, backlinks, and related requirement codes.
    """
    clean_key = node_id_or_slug.strip()
    if not clean_key:
        raise ValueError("Argument 'node_id_or_slug' cannot be empty.")
    if depth < 1 or depth > 2:
        raise ValueError("Argument 'depth' must be either 1 or 2.")

    service = get_knowledge_service()
    return service.get_related_knowledge(node_id_or_slug=clean_key, depth=depth)
