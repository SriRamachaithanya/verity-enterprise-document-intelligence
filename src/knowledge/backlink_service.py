import logging

from src.knowledge.models import BacklinkItem
from src.storage.db import DatabaseManager

logger = logging.getLogger(__name__)


class BacklinkService:
    """
    Computes, queries, and aggregates bi-directional backlinks targeting any knowledge node.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def get_backlinks_for_slug(self, target_slug: str) -> list[BacklinkItem]:
        """
        Query all inbound backlinks pointing to the specified target slug.
        """
        clean_slug = target_slug.strip().lower()
        raw_backlinks = self.db.get_backlinks(clean_slug)

        items: list[BacklinkItem] = []
        for bl in raw_backlinks:
            items.append(
                BacklinkItem(
                    source_slug=bl["source_slug"],
                    source_title=bl["source_title"],
                    source_type=bl["source_type"],
                    context_snippet=bl.get("context_snippet"),
                    relation_type=bl.get("relation_type", "references"),
                    provenance=bl.get("provenance", "wiki_link"),
                )
            )
        return items

    def group_backlinks_by_type(self, target_slug: str) -> dict[str, list[BacklinkItem]]:
        """
        Group inbound backlinks by source archetype (e.g. 'control', 'requirement', 'document').
        """
        backlinks = self.get_backlinks_for_slug(target_slug)
        grouped: dict[str, list[BacklinkItem]] = {}
        for bl in backlinks:
            grouped.setdefault(bl.source_type, []).append(bl)
        return grouped

