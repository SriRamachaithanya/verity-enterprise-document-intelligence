import re

from src.knowledge.models import ParsedWikiLink

# Matches [[slug]] or [[slug|display_text]]
WIKI_LINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


class WikiLinkParser:
    """
    Parses Obsidian-style [[Wiki Links]] from markdown documents, extracting
    targets, optional aliases, byte positions, line numbers, and context snippets.
    """

    def parse(self, text: str) -> list[ParsedWikiLink]:
        """
        Scan text and return all parsed wiki links with structural coordinates.
        """
        if not text:
            return []

        results: list[ParsedWikiLink] = []
        for match in WIKI_LINK_PATTERN.finditer(text):
            raw_target = match.group(1).strip()
            alias = match.group(2).strip() if match.group(2) else None

            # Normalize target slug: lowercase, strip leading/trailing spaces
            target_slug = raw_target.strip().lower().replace(" ", "-")
            display_text = alias if alias else raw_target

            start_char = match.start()
            end_char = match.end()

            # Calculate 1-based line number
            line_number = text[:start_char].count("\n") + 1

            # Extract surrounding context snippet (up to 70 characters before and after)
            snippet_start = max(0, start_char - 70)
            snippet_end = min(len(text), end_char + 70)
            raw_snippet = text[snippet_start:snippet_end]
            # Clean up linebreaks into a single coherent sentence snippet
            clean_snippet = " ".join(raw_snippet.split()).strip()

            results.append(
                ParsedWikiLink(
                    raw_match=match.group(0),
                    target_slug=target_slug,
                    display_text=display_text,
                    start_char=start_char,
                    end_char=end_char,
                    line_number=line_number,
                    context_snippet=clean_snippet,
                )
            )

        return results

