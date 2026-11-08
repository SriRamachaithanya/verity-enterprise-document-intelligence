from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencies import get_hybrid_search
from src.api.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from src.api.security.auth import AuthenticatedUser, require_user
from src.indexing.hybrid_search import HybridSearchEngine

router = APIRouter(prefix="/api/v1/search", tags=["Hybrid Retrieval"])


@router.post(
    "",
    response_model=SearchResponse,
    summary="Execute Hybrid Search",
    description="Query indexed documents using hybrid Reciprocal Rank Fusion (FTS5 BM25 + FAISS Dense Embeddings).",
)
def execute_hybrid_search(
    req: SearchRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_user)],
    search_engine: Annotated[HybridSearchEngine, Depends(get_hybrid_search)],
) -> SearchResponse:
    raw_results = search_engine.search(
        query=req.query,
        top_k=req.top_k,
    )

    # Filter by allowed document IDs if requested
    if req.document_ids:
        allowed = set(req.document_ids)
        raw_results = [r for r in raw_results if r.document_id in allowed]

    items = [
        SearchResultItem(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            document_name=r.document_name,
            page_number=r.page_number,
            section_heading=r.section_heading,
            locator=r.locator,
            content=r.content,
            rrf_score=round(r.rrf_score, 4),
        )
        for r in raw_results
    ]

    return SearchResponse(
        query=req.query,
        total_results=len(items),
        results=items,
    )
