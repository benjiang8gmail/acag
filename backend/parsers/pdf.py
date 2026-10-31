"""PDF text extraction shared by the PDF-based connectors (NSW, QLD, ACT).

pdfminer.six is pure Python and MIT-licensed, so it adds no system dependency.
It was chosen over pypdf because pypdf splits words ("t ransport", "third -generation"),
which would break the exact-quote check (spec §9.9).
"""

from __future__ import annotations

import io
import re
from functools import lru_cache

from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams


def pdf_pages(raw: bytes) -> list[str]:
    """Text of each page, in reading order, with runs of spaces collapsed."""
    return list(_pdf_pages(raw))


@lru_cache(maxsize=4)  # extraction takes seconds; a scan or test may read the same PDF twice
def _pdf_pages(raw: bytes) -> tuple[str, ...]:
    # boxes_flow=None keeps strict top-to-bottom order; the default layout analysis moved
    # NSW headings below the paragraph that follows them.
    pages = extract_text(io.BytesIO(raw), laparams=LAParams(boxes_flow=None)).split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return tuple(re.sub(r"[ \t]+", " ", p) for p in pages)


def pdf_layout_lines(raw: bytes, page_numbers: list[int]) -> list[tuple[int, float, str]]:
    """(page index, left x, text) for each text line on the given pages, top to bottom.
    Used where indentation carries meaning, e.g. the ACT contents pages."""
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTTextContainer, LTTextLine

    out = []
    for index, page in zip(page_numbers, extract_pages(io.BytesIO(raw), page_numbers=page_numbers,
                                                        laparams=LAParams(boxes_flow=None))):
        rows = []
        for el in page:
            if isinstance(el, LTTextContainer):
                for line in el:
                    if isinstance(line, LTTextLine) and line.get_text().strip():
                        rows.append((-line.y0, line.x0, re.sub(r"\s+", " ", line.get_text()).strip()))
        out.extend((index, x, text) for _, x, text in sorted(rows))
    return out


def join_lines(lines: list[str], width: int) -> str:
    """Join wrapped lines into paragraphs. A line well short of the page width ends a paragraph;
    a line ending in a hyphen joins the next without a space (a compound split at its hyphen)."""
    out = ""
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        if not out:
            out = line
        elif out.endswith("-") and not out.endswith(" -"):
            out += line
        else:
            # The first line follows the speaker's name, so its length says nothing about paragraphs.
            prev = lines[i - 1].strip()
            out += ("\n" if i > 1 and len(prev) < 0.75 * width else " ") + line
    return out
