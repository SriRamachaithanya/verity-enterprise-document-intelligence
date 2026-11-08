import logging

from src.knowledge.models import ParsedWikiLink, ResolvedLink
from src.storage.db import DatabaseManager

logger = logging.getLogger(__name__)


class LinkResolver:
    """
    Resolves parsed wiki links against existing knowledge nodes in SQLite,
    detecting valid references and broken/dangling targets.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def resolve_link(self, parsed_link: ParsedWikiLink) -> ResolvedLink:
        """
        Check if a single parsed wiki link targets an existing knowledge node.
        """
        slug = parsed_link.target_slug
        node = self.db.get_knowledge_node(slug)

        if node:
            return ResolvedLink(
                target_slug=slug,
                display_text=parsed_link.display_text,
                is_resolved=True,
                target_node_id=node["id"],
                target_title=node["title"],
                target_type=node["node_type"],
            )
        else:
            return ResolvedLink(
                target_slug=slug,
                display_text=parsed_link.display_text,
                is_resolved=False,
                target_node_id=None,
                target_title=None,
                target_type=None,
            )

    def resolve_all(self, parsed_links: list[ParsedWikiLink]) -> list[ResolvedLink]:
        """
        Batch resolve a list of parsed links.
        """
        return [self.resolve_link(link) for link in parsed_links]

    def find_broken_links_for_node(self, source_node_id: str) -> list[dict[str, str]]:
        """
        Inspect outgoing links from a node and identify which targets are uncreated.
        """
        outgoing = self.db.get_outgoing_links(source_node_id)
        broken: list[dict[str, str]] = []

        for link in outgoing:
            target_slug = link["target_slug"]
            target_node = self.db.get_knowledge_node(target_slug)
            if not target_node:
                broken.append({
                    "source_node_id": source_node_id,
                    "target_slug": target_slug,
                    "link_text": link.get("link_text") or target_slug,
                    "context_snippet": link.get("context_snippet") or "",
                })

        return broken

