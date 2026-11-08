import numpy as np

from src.indexing.chunker import DocumentChunker
from src.indexing.embedding_service import EMBEDDING_DIM
from src.schemas.document import DocumentMetadata, ExtractedDocument, ParsedElement


def test_chunker_sentence_boundaries_and_metadata():
    chunker = DocumentChunker(target_tokens=40, overlap_tokens=10)

    # Synthetic document with multiple sentences
    elements = [
        ParsedElement(
            text="First sentence about data privacy. Second sentence about key encryption.",
            page_number=1,
            section_heading="Section 1: Cryptography",
            locator="Page 1, Para 1",
        ),
        ParsedElement(
            text="Third sentence discusses compliance auditing. Fourth sentence specifies ISO 27001.",
            page_number=2,
            section_heading="Section 2: Auditing",
            locator="Page 2, Para 1",
        ),
    ]

    extracted = ExtractedDocument(
        metadata=DocumentMetadata(
            filename="test.txt",
            file_hash="hash_abc",
            mime_type="text/plain",
            file_size_bytes=200,
        ),
        elements=elements,
    )

    chunks = chunker.chunk_document(extracted, document_id="doc_xyz")

    assert len(chunks) >= 1
    for c in chunks:
        assert c.document_id == "doc_xyz"
        assert c.token_count > 0
        assert len(c.content) > 0
        assert c.section_heading in ["Section 1: Cryptography", "Section 2: Auditing"]
        assert c.locator != ""


def test_embedding_service_dimensions_and_normalization(session_embedding_service):
    svc = session_embedding_service

    texts = [
        "Data at rest must be encrypted using AES-256.",
        "Access control lists must be reviewed on a quarterly cadence.",
    ]

    embeddings = svc.embed_texts(texts)

    assert isinstance(embeddings, np.ndarray)
    assert embeddings.shape == (2, EMBEDDING_DIM)
    assert embeddings.dtype == np.float32

    # Verify L2 normalization (cosine similarity property: norm == 1.0)
    norms = np.linalg.norm(embeddings, axis=1)
    for norm in norms:
        assert np.isclose(norm, 1.0, atol=1e-4)


def test_embedding_query_caching(session_embedding_service):
    svc = session_embedding_service
    q = "audit trail preservation"

    vec1 = svc.embed_query(q)
    vec2 = svc.embed_query(q)

    assert np.array_equal(vec1, vec2)
    assert vec1.shape == (EMBEDDING_DIM,)
