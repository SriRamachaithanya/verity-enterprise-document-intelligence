import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_db, get_knowledge_service
from src.api.schemas.knowledge import BacklinksListResponse, KnowledgeNodeDetailResponse
from src.api.security.auth import AuthenticatedUser, require_user
from src.knowledge.graph_service import KnowledgeGraphService
from src.schemas.mcp import BacklinkItem
from src.storage.db import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge", tags=["Obsidian Knowledge Graph"])


@router.get(
    "/{node_slug}",
    response_model=KnowledgeNodeDetailResponse,
    summary="Get Knowledge Note & Graph Neighborhood",
    description="Retrieve a knowledge note, its outgoing forward wiki links, inbound backlinks, and referenced requirements.",
)
def get_knowledge_node_endpoint(
    node_slug: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_user)],
    service: Annotated[KnowledgeGraphService, Depends(get_knowledge_service)],
    depth: Annotated[int, Query(ge=1, le=3, description="Traversal depth")] = 1,
) -> KnowledgeNodeDetailResponse:
    clean_slug = node_slug.strip().lower()
    try:
        response = service.get_related_knowledge(clean_slug, depth=depth)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        ) from val_err

    return KnowledgeNodeDetailResponse(
        root_node=response.root_node,
        outgoing_links=response.outgoing_links,
        backlinks=response.backlinks,
        related_requirements=response.related_requirements,
        depth=response.depth,
    )


@router.get(
    "/{node_slug}/backlinks",
    response_model=BacklinksListResponse,
    summary="Get Node Backlinks",
    description="Retrieve all inbound citations and references pointing to this target node.",
)
def get_node_backlinks_endpoint(
    node_slug: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_user)],
    service: Annotated[KnowledgeGraphService, Depends(get_knowledge_service)],
    db: Annotated[DatabaseManager, Depends(get_db)],
) -> BacklinksListResponse:
    clean_slug = node_slug.strip().lower()
    node = db.get_knowledge_node(clean_slug)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge node '{clean_slug}' not found.",
        )

    backlinks = service.backlink_service.get_backlinks_for_slug(clean_slug)

    items = [
        BacklinkItem(
            source_slug=b.source_slug,
            source_title=b.source_title,
            source_type=b.source_type,
            context_snippet=b.context_snippet,
        )
        for b in backlinks
    ]

    return BacklinksListResponse(
        target_slug=clean_slug,
        total_backlinks=len(items),
        backlinks=items,
    )
