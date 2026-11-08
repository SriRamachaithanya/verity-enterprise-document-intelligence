from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000, description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum candidate chunks to return")
    document_ids: list[str] | None = Field(default=None, description="Optional document ID filters")


class SearchResultItem(BaseModel):
    chunk_id: str = Field(description="Unique chunk ID")
    document_id: str = Field(description="Parent document ID")
    document_name: str = Field(description="Parent document filename")
    page_number: int | None = Field(default=None, description="Page number if applicable")
    section_heading: str = Field(default="General", description="Section context")
    locator: str = Field(default="", description="Structural paragraph/section locator")
    content: str = Field(description="Text content excerpt")
    rrf_score: float = Field(description="Reciprocal Rank Fusion score")


class SearchResponse(BaseModel):
    query: str = Field(description="Executed search query")
    total_results: int = Field(description="Total chunks retrieved")
    results: list[SearchResultItem] = Field(description="Ranked candidate chunks")

