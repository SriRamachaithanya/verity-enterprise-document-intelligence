from enum import Enum

from pydantic import BaseModel, Field


class RelationshipType(str, Enum):
    REFERENCES = "references"
    IMPLEMENTS = "implements"
    SATISFIES = "satisfies"
    VALIDATES = "validates"
    EVIDENCES = "evidences"
    REMEDIATES = "remediates"


class ProvenanceType(str, Enum):
    WIKI_LINK = "wiki_link"
    COMPLIANCE_ENGINE = "compliance_engine"
    USER_ASSERTION = "user_assertion"
    MANUAL_AUDIT = "manual_audit"


class ParsedWikiLink(BaseModel):
    raw_match: str = Field(description="Exact bracketed text, e.g. '[[mfa-policy|MFA Policy]]'")
    target_slug: str = Field(description="Normalized target node slug")
    display_text: str = Field(description="Display label or target slug if omitted")
    start_char: int = Field(description="Character index of link start in content")
    end_char: int = Field(description="Character index of link end in content")
    line_number: int = Field(description="1-based line number of the link")
    context_snippet: str = Field(description="Surrounding context sentence snippet")


class ResolvedLink(BaseModel):
    target_slug: str = Field(description="Target node slug")
    display_text: str = Field(description="Display title or slug")
    is_resolved: bool = Field(description="True if target node exists in knowledge base")
    target_node_id: str | None = Field(default=None, description="Database ID of target node if found")
    target_title: str | None = Field(default=None, description="Title of target node if found")
    target_type: str | None = Field(default=None, description="Type of target node if found")


class KnowledgeNodeItem(BaseModel):
    id: str = Field(description="Unique note ID")
    slug: str = Field(description="URL-friendly note slug")
    title: str = Field(description="Note title")
    node_type: str = Field(description="Type: document, requirement, control, evidence, assessment, remediation")
    content_markdown: str = Field(description="Verbatim Markdown body")


class KnowledgeLinkItem(BaseModel):
    target_slug: str = Field(description="Target node slug")
    target_title: str | None = Field(default=None, description="Target node title if resolved")
    link_text: str | None = Field(default=None, description="Visual display link text")
    context_snippet: str | None = Field(default=None, description="Surrounding sentence context")
    relation_type: str = Field(default="references", description="Semantic relationship type")
    provenance: str = Field(default="wiki_link", description="Source/origin of the link")


class BacklinkItem(BaseModel):
    source_slug: str = Field(description="Source note slug linking to target")
    source_title: str = Field(description="Source note title")
    source_type: str = Field(description="Source note type")
    context_snippet: str | None = Field(default=None, description="Context where link occurred")
    relation_type: str = Field(default="references", description="Semantic relationship type")
    provenance: str = Field(default="wiki_link", description="Origin of link")


class TraversalStep(BaseModel):
    hop: int = Field(description="Hop distance from root")
    source_slug: str = Field(description="Origin slug for this hop")
    target_slug: str = Field(description="Target slug reached")
    target_title: str = Field(description="Target node title")
    target_type: str = Field(description="Target node type")
    relation_type: str = Field(default="references", description="Relationship type")


class TraversalGraph(BaseModel):
    root_slug: str = Field(description="Starting node slug")
    max_depth: int = Field(description="Traversed depth")
    nodes_visited: list[str] = Field(description="Slugs of all unique visited nodes")
    steps: list[TraversalStep] = Field(description="Ordered traversal edge steps")
    cycles_detected: list[str] = Field(default_factory=list, description="Slugs where cycles were suppressed")


class OrphanReport(BaseModel):
    total_orphans: int = Field(description="Count of orphan nodes")
    orphan_slugs: list[str] = Field(description="Slugs of nodes with 0 incoming and 0 outgoing links")
    orphan_nodes: list[KnowledgeNodeItem] = Field(description="Full node objects of orphans")

