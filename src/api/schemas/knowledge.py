from pydantic import BaseModel, Field

from src.schemas.mcp import BacklinkItem, KnowledgeLinkItem, KnowledgeNodeItem


class KnowledgeNodeDetailResponse(BaseModel):
    root_node: KnowledgeNodeItem = Field(description="The primary knowledge note")
    outgoing_links: list[KnowledgeLinkItem] = Field(description="Outgoing forward wiki links")
    backlinks: list[BacklinkItem] = Field(description="Inbound references pointing to this note")
    related_requirements: list[str] = Field(description="Regulatory codes referenced")
    depth: int = Field(description="Traversal depth used")


class BacklinksListResponse(BaseModel):
    target_slug: str = Field(description="Target note slug queried")
    total_backlinks: int = Field(description="Count of inbound backlinks")
    backlinks: list[BacklinkItem] = Field(description="Inbound references citing this node")

