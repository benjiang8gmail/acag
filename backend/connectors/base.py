"""Hansard connector interface (spec §6).

One connector per parliament, in `connectors/{code}.py`. A connector knows how
to list sitting days and documents and how to parse a document. It never makes
HTTP requests itself: `fetch` goes through `pipeline.fetch.Fetcher`, which
enforces robots.txt, rate limits and conditional GETs for every connector.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol


class CouldNotCheck(Exception):
    """The sitting calendar could not be read. Must not be treated as "no sittings" (§6, §8.9)."""


@dataclass(frozen=True)
class SittingDayRef:
    source_id: str          # chamber, e.g. "SA-HA"
    sitting_date: date      # local date in the parliament's time zone
    version_hint: str = "unknown"  # proof / final / unknown


@dataclass(frozen=True)
class DocumentRef:
    source_id: str
    sitting_date: date
    url: str
    format: str             # xml / html / pdf / docx / json
    version_hint: str = "unknown"


@dataclass
class ParsedSpeech:
    seq: int
    text: str
    debate_title: str | None = None
    proceeding_type: str | None = None
    speaker_name: str | None = None
    speaker_role: str | None = None
    party: str | None = None
    electorate: str | None = None
    start_time: str | None = None
    page: str | None = None
    anchor_url: str | None = None


@dataclass
class ParsedDocument:
    speeches: list[ParsedSpeech] = field(default_factory=list)
    version: str = "unknown"  # what the document itself says: proof / final / unknown


class HansardConnector(Protocol):
    code: str               # parliament code, e.g. "SA"
    source_ids: tuple[str, ...]

    def list_sitting_days(self, start: date, end: date) -> list[SittingDayRef]:
        """Sitting days in [start, end] for every chamber of this parliament.

        Return [] only when the calendar was read and shows no sittings.
        Raise CouldNotCheck when it could not be read.
        """
        ...

    def list_documents(self, day: SittingDayRef) -> list[DocumentRef]: ...

    def parse(self, raw: bytes, ref: DocumentRef) -> ParsedDocument:
        """Normalise a document into speeches, keeping page numbers or anchors for citations."""
        ...


# Registered connectors by name (`connector` column in config/sources.yaml).
# Real connectors are added in Phase 2 once each source has a real fixture
# (docs/sources.md); until then the registry is empty and every source is disabled.
REGISTRY: dict[str, type] = {}
