import collections
import logging

from src.knowledge.models import TraversalGraph, TraversalStep
from src.storage.db import DatabaseManager

logger = logging.getLogger(__name__)

MAX_ALLOWED_DEPTH = 3


class GraphTraversalService:
    """
    Performs multi-hop graph traversal over knowledge links with strict depth bounds
    and cycle detection to prevent infinite loops.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def traverse(
        self,
        root_slug: str,
        max_depth: int = 1,
    ) -> TraversalGraph:
        """
        Traverse the knowledge graph starting from root_slug using Breadth-First Search.

        Safety constraints:
        - Strict maximum depth of 3 hops.
        - Cycle suppression using visited slug set.
        """
        clean_root = root_slug.strip().lower()
        bounded_depth = max(1, min(max_depth, MAX_ALLOWED_DEPTH))

        root_node = self.db.get_knowledge_node(clean_root)
        if not root_node:
            raise ValueError(f"Root knowledge node '{clean_root}' not found.")

        visited_slugs: set[str] = {clean_root}
        cycles_detected: list[str] = []
        steps: list[TraversalStep] = []

        # Queue contains tuples of: (current_slug, current_hop)
        queue: collections.deque[tuple[str, int]] = collections.deque([(clean_root, 0)])

        while queue:
            curr_slug, curr_hop = queue.popleft()

            if curr_hop >= bounded_depth:
                continue

            curr_node = self.db.get_knowledge_node(curr_slug)
            if not curr_node:
                continue

            outgoing = self.db.get_outgoing_links(curr_node["id"])

            for link in outgoing:
                target_slug = link["target_slug"].strip().lower()
                rel_type = link.get("relation_type", "references")

                target_node = self.db.get_knowledge_node(target_slug)
                target_title = target_node["title"] if target_node else target_slug
                target_type = target_node["node_type"] if target_node else "unresolved"

                if target_slug in visited_slugs:
                    if target_slug not in cycles_detected:
                        cycles_detected.append(target_slug)
                    continue

                # Record successful step
                steps.append(
                    TraversalStep(
                        hop=curr_hop + 1,
                        source_slug=curr_slug,
                        target_slug=target_slug,
                        target_title=target_title,
                        target_type=target_type,
                        relation_type=rel_type,
                    )
                )

                visited_slugs.add(target_slug)
                queue.append((target_slug, curr_hop + 1))

        return TraversalGraph(
            root_slug=clean_root,
            max_depth=bounded_depth,
            nodes_visited=list(visited_slugs),
            steps=steps,
            cycles_detected=cycles_detected,
        )

