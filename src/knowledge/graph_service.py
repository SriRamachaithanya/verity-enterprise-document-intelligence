import logging
import re
import uuid

from src.knowledge.backlink_service import BacklinkService
from src.knowledge.graph_traversal import GraphTraversalService
from src.knowledge.link_resolver import LinkResolver
from src.knowledge.models import (
    KnowledgeNodeItem,
    OrphanReport,
    TraversalGraph,
)
from src.knowledge.wiki_link_parser import WikiLinkParser
from src.schemas.mcp import (
    BacklinkItem,
    KnowledgeLinkItem,
    RelatedKnowledgeResponse,
)
from src.storage.db import DatabaseManager

logger = logging.getLogger(__name__)

REQUIREMENT_MENTION_REGEX = re.compile(r"\[\[([^\]]+)\]\]")


class KnowledgeGraphService:
    """
    Central orchestrator for Obsidian-inspired knowledge graphs, linking markdown
    notes, resolving wiki links, discovering backlinks, and performing cycle-safe traversals.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        self.parser = WikiLinkParser()
        self.resolver = LinkResolver(db)
        self.backlink_service = BacklinkService(db)
        self.traversal_service = GraphTraversalService(db)

    def infer_relation_type(
        self,
        source_type: str,
        target_type: str | None,
    ) -> str:
        """
        Infer semantic relationship type from node archetype interactions:
        - DOCUMENT -> CONTROL / REQUIREMENT: implements
        - CONTROL -> REQUIREMENT: satisfies
        - EVIDENCE -> CONTROL: validates
        - EVIDENCE -> REQUIREMENT: evidences
        - ASSESSMENT -> REMEDIATION: remediates
        - Default: references
        """
        st = source_type.lower()
        tt = (target_type or "").lower()

        if st == "document" and tt in ("control", "requirement"):
            return "implements"
        if st == "control" and tt == "requirement":
            return "satisfies"
        if st == "evidence" and tt == "control":
            return "validates"
        if st == "evidence" and tt == "requirement":
            return "evidences"
        if st == "assessment" and tt == "remediation":
            return "remediates"
        return "references"

    def sync_node_links(
        self,
        node_id: str,
        content_markdown: str,
        provenance: str = "wiki_link",
    ) -> list[str]:
        """
        Parse wiki links in markdown content and synchronize links in SQLite.
        """
        node = self.db.get_knowledge_node(node_id)
        if not node:
            raise ValueError(f"Knowledge node '{node_id}' not found.")

        parsed_links = self.parser.parse(content_markdown)
        added_slugs: list[str] = []

        for pl in parsed_links:
            resolved = self.resolver.resolve_link(pl)
            rel_type = self.infer_relation_type(
                source_type=node["node_type"],
                target_type=resolved.target_type,
            )

            link_id = f"lnk_{uuid.uuid4().hex[:12]}"
            inserted = self.db.insert_knowledge_link(
                link_id=link_id,
                source_node_id=node_id,
                target_slug=pl.target_slug,
                link_text=pl.display_text,
                context_snippet=pl.context_snippet,
                relation_type=rel_type,
                provenance=provenance,
            )
            if inserted:
                added_slugs.append(pl.target_slug)

        return added_slugs

    def create_or_update_node(
        self,
        slug: str,
        title: str,
        node_type: str,
        content_markdown: str,
        sync_links: bool = True,
        provenance: str = "wiki_link",
    ) -> str:
        """
        Insert or update a knowledge note and optionally synchronize outgoing wiki links.
        """
        clean_slug = slug.strip().lower()
        existing = self.db.get_knowledge_node(clean_slug)

        if existing:
            node_id = existing["id"]
            # Delete prior outgoing links from wiki_link provenance to avoid stale references
            # SQLite ON CONFLICT replace or selective update
            # We can update the row via direct execution or re-insertion
            conn = self.db._get_connection()
            with conn:
                conn.execute(
                    """
                    UPDATE knowledge_nodes
                    SET title = ?, node_type = ?, content_markdown = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (title, node_type, content_markdown, node_id),
                )
        else:
            node_id = f"node_{uuid.uuid4().hex[:12]}"
            self.db.insert_knowledge_node(
                node_id=node_id,
                slug=clean_slug,
                title=title,
                node_type=node_type,
                content_markdown=content_markdown,
            )

        if sync_links:
            self.sync_node_links(node_id, content_markdown, provenance=provenance)

        return node_id

    def get_related_knowledge(
        self,
        node_id_or_slug: str,
        depth: int = 1,
    ) -> RelatedKnowledgeResponse:
        """
        Retrieve related knowledge note, outgoing links, backlinks, and regulatory cross-references.
        Supports depth bounds of 1 to 3 with cycle prevention.
        """
        clean_key = node_id_or_slug.strip()
        if not clean_key:
            raise ValueError("Argument 'node_id_or_slug' cannot be empty.")
        if depth < 1 or depth > 3:
            raise ValueError("Argument 'depth' must be between 1 and 3.")

        node = self.db.get_knowledge_node(clean_key)
        if not node:
            raise ValueError(f"Knowledge node '{clean_key}' not found.")

        from src.schemas.mcp import KnowledgeNodeItem as SchemaNodeItem

        root_item = SchemaNodeItem(
            id=node["id"],
            slug=node["slug"],
            title=node["title"],
            node_type=node["node_type"],
            content_markdown=node["content_markdown"],
        )

        # 1-hop outgoing links
        raw_outgoing = self.db.get_outgoing_links(node["id"])
        outgoing_items: list[KnowledgeLinkItem] = [
            KnowledgeLinkItem(
                target_slug=lnk["target_slug"],
                target_title=lnk.get("target_title"),
                link_text=lnk.get("link_text"),
                context_snippet=lnk.get("context_snippet"),
            )
            for lnk in raw_outgoing
        ]

        # Inbound backlinks
        backlink_items = [
            BacklinkItem(
                source_slug=bl.source_slug,
                source_title=bl.source_title,
                source_type=bl.source_type,
                context_snippet=bl.context_snippet,
            )
            for bl in self.backlink_service.get_backlinks_for_slug(node["slug"])
        ]

        # Multi-hop expansion if depth > 1
        if depth > 1:
            traversal: TraversalGraph = self.traversal_service.traverse(
                root_slug=node["slug"],
                max_depth=depth,
            )
            # Add hops > 1 into outgoing_items with hop annotation
            existing_targets = {it.target_slug for it in outgoing_items}
            for step in traversal.steps:
                if step.hop > 1 and step.target_slug not in existing_targets:
                    existing_targets.add(step.target_slug)
                    outgoing_items.append(
                        KnowledgeLinkItem(
                            target_slug=step.target_slug,
                            target_title=step.target_title,
                            link_text=f"[{step.relation_type}] {step.target_title}",
                            context_snippet=f"[Hop {step.hop} via {step.source_slug}] Relation: {step.relation_type}",
                        )
                    )

        # Extract regulatory requirement codes from markdown content
        content = node["content_markdown"]
        matches = REQUIREMENT_MENTION_REGEX.findall(content)
        related_reqs: list[str] = []
        seen_reqs: set[str] = set()

        for m in matches:
            clean_match = m.split("|")[0].strip()
            if any(
                prefix in clean_match.lower()
                for prefix in ("soc", "iso", "cc", "hipaa", "pci", "nist")
            ) and clean_match not in seen_reqs:
                seen_reqs.add(clean_match)
                related_reqs.append(clean_match)

        return RelatedKnowledgeResponse(
            root_node=root_item,
            outgoing_links=outgoing_items,
            backlinks=backlink_items,
            related_requirements=related_reqs,
            depth=depth,
        )

    def detect_orphan_nodes(self) -> OrphanReport:
        """
        Identify knowledge nodes with zero inbound and zero outbound connections.
        """
        raw_orphans = self.db.get_orphan_knowledge_nodes()
        nodes: list[KnowledgeNodeItem] = [
            KnowledgeNodeItem(
                id=o["id"],
                slug=o["slug"],
                title=o["title"],
                node_type=o["node_type"],
                content_markdown=o["content_markdown"],
            )
            for o in raw_orphans
        ]
        slugs = [n.slug for n in nodes]
        return OrphanReport(
            total_orphans=len(nodes),
            orphan_slugs=slugs,
            orphan_nodes=nodes,
        )

    def get_broken_links(self) -> list[dict[str, str]]:
        """
        Identify all links across the vault that point to uncreated target slugs.
        """
        all_nodes = self.db.list_all_knowledge_nodes()
        all_broken: list[dict[str, str]] = []
        for n in all_nodes:
            broken = self.resolver.find_broken_links_for_node(n["id"])
            all_broken.extend(broken)
        return all_broken

