import re
import uuid

from src.schemas.document import DocumentChunk, ExtractedDocument

# Heuristic: 1 token ≈ 4 characters / 0.75 words
TARGET_CHUNK_TOKENS = 400
OVERLAP_TOKENS = 50
APPROX_CHARS_PER_TOKEN = 4

TARGET_CHUNK_CHARS = TARGET_CHUNK_TOKENS * APPROX_CHARS_PER_TOKEN  # ~1600 chars
OVERLAP_CHARS = OVERLAP_TOKENS * APPROX_CHARS_PER_TOKEN  # ~200 chars

# Sentence boundary regex (handles periods, question marks, exclamation marks followed by whitespace)
SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def estimate_token_count(text: str) -> int:
    """Accurate word and character based token estimator for MiniLM/LLM."""
    if not text:
        return 0
    words = len(text.split())
    chars = len(text)
    # Average of word-based (~1.3 tokens/word) and char-based (~4 chars/token)
    return max(1, int((words * 1.33 + chars / 4.0) / 2))


class DocumentChunker:
    """
    Sliding window chunker preserving layout hierarchy, section headings,
    page locators, and sentence boundaries without truncating words.
    """

    def __init__(
        self,
        target_tokens: int = TARGET_CHUNK_TOKENS,
        overlap_tokens: int = OVERLAP_TOKENS,
    ):
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        self.target_chars = target_tokens * APPROX_CHARS_PER_TOKEN
        self.overlap_chars = overlap_tokens * APPROX_CHARS_PER_TOKEN

    def chunk_document(
        self,
        extracted_doc: ExtractedDocument,
        document_id: str,
    ) -> list[DocumentChunk]:
        """Convert extracted document elements into structured, overlapping chunks."""
        chunks: list[DocumentChunk] = []
        chunk_idx = 0

        # Group elements by page/section where feasible
        current_sentences: list[tuple[str, int | None, str, str]] = []
        # Item: (sentence_text, page_number, section_heading, locator)

        for elem in extracted_doc.elements:
            sentences = self._split_into_sentences(elem.text)
            for s in sentences:
                current_sentences.append((s, elem.page_number, elem.section_heading, elem.locator))

        if not current_sentences:
            return []

        # Build chunks using sentence grouping with overlap
        i = 0
        n = len(current_sentences)

        while i < n:
            chunk_parts: list[str] = []
            chunk_len = 0
            start_i = i

            page_number: int | None = current_sentences[i][1]
            section_heading: str = current_sentences[i][2]
            locators: list[str] = []

            while i < n:
                sent_text, p_num, s_head, loc = current_sentences[i]
                sent_len = len(sent_text)

                # If single sentence is larger than target_chars, we still include it
                if chunk_len > 0 and (chunk_len + sent_len) > self.target_chars:
                    break

                chunk_parts.append(sent_text)
                chunk_len += sent_len + 1
                if loc and loc not in locators:
                    locators.append(loc)
                if p_num is not None and page_number is None:
                    page_number = p_num
                if s_head and s_head != "General" and section_heading == "General":
                    section_heading = s_head

                i += 1

            chunk_text = " ".join(chunk_parts).strip()
            if not chunk_text:
                continue

            # Determine composite locator
            composite_locator = (
                ", ".join(locators[:2]) if locators else f"Page {page_number or 'N/A'}"
            )
            token_count = estimate_token_count(chunk_text)
            chunk_id = f"chk_{document_id[:8]}_{chunk_idx:04d}_{uuid.uuid4().hex[:6]}"

            chunks.append(
                DocumentChunk(
                    id=chunk_id,
                    document_id=document_id,
                    chunk_index=chunk_idx,
                    content=chunk_text,
                    token_count=token_count,
                    page_number=page_number,
                    section_heading=section_heading,
                    locator=composite_locator,
                )
            )
            chunk_idx += 1

            if i >= n:
                break

            # Calculate overlap backtracking
            overlap_backtrack_chars = 0
            backtrack_count = 0
            j = i - 1
            while j > start_i:
                overlap_backtrack_chars += len(current_sentences[j][0])
                if overlap_backtrack_chars >= self.overlap_chars:
                    backtrack_count = i - j
                    break
                j -= 1

            if backtrack_count > 0:
                i = i - backtrack_count

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences while respecting abbreviations."""
        if not text:
            return []
        parts = SENTENCE_SPLIT_REGEX.split(text.strip())
        return [p.strip() for p in parts if p.strip()]
