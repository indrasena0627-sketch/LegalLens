"""The seams the M4 pipeline replaces.

Each port is a Protocol with a stub implementation in `app/ingestion/stub/` or a
real one in `app/ingestion/extract/`. The split is deliberate and is the §7.1
decision in BACKEND-TODO:

  REAL today   text extraction for TXT, DOCX and the PDF text layer, with
               per-page character offsets — because citation click-through
               (FR-13) is only truly tested when a span resolves against text
               pulled from a file the user actually uploaded.
  STUB today   OCR, layout QA, classification, embedding and indexing. These are
               BRD §15's expensive half and correctly M4's problem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ParsedPage:
    """One page of extracted text. `char_count` is len(text); offsets handed to
    spans are page-local indexes into `text`."""

    page_no: int
    text: str
    ocr_confidence: float | None = None
    engine: str = "unknown"


@dataclass
class ParseResult:
    pages: list[ParsedPage] = field(default_factory=list)
    # True when the source had no usable text layer and OCR was required (DR-1).
    scanned: bool = False
    engine: str = "unknown"
    warnings: list[str] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def total_chars(self) -> int:
        return sum(len(p.text) for p in self.pages)


@dataclass
class LayoutQaResult:
    """BRD §15: a clause pulled from a mis-ordered two-column page looks
    correct, which is why it is worse than no extraction. The gate quarantines
    rather than indexing text it does not trust."""

    reading_order_score: float
    column_sanity: bool
    table_integrity: bool
    quarantine: bool = False
    reason: str | None = None
    flagged_pages: list[int] = field(default_factory=list)


@dataclass
class Classification:
    doc_type: str  # contract | opinion | pleading | other
    confidence: float


@dataclass
class Chunk:
    """A child chunk plus the parent section it expands to. Offsets are
    page-local to `page_from`; a chunk spanning pages records both ends."""

    page_from: int
    page_to: int
    char_start: int
    char_end: int
    text: str
    section_path: str | None = None
    clause_no: str | None = None
    token_count: int = 0
    parent_key: str | None = None
    is_parent: bool = False


@runtime_checkable
class Parser(Protocol):
    """Format-specific text extraction."""

    name: str

    def supports(self, ext: str) -> bool: ...

    def parse(self, path: str, *, max_pages: int) -> ParseResult: ...


@runtime_checkable
class Ocr(Protocol):
    """STUB in M3. Real engine (Tesseract / PaddleOCR) at M4."""

    name: str

    def run(self, path: str, pages: list[int], *, total_pages: int) -> ParseResult: ...


@runtime_checkable
class LayoutQa(Protocol):
    """STUB in M3. Real reading-order and column checks at M4."""

    name: str

    def check(self, result: ParseResult) -> LayoutQaResult: ...


@runtime_checkable
class Classifier(Protocol):
    """STUB in M3 — heuristics over filename and first-page text. FR-5 only
    requires that a type is shown and overridable, which a heuristic satisfies."""

    name: str

    def classify(self, filename: str, pages: list[ParsedPage]) -> Classification: ...


@runtime_checkable
class Chunker(Protocol):
    """Section-aware chunking. Real in M3 because `chunk_meta` rows and span
    offsets are backend data, not model data."""

    name: str

    def chunk(self, pages: list[ParsedPage], doc_type: str) -> list[Chunk]: ...


@runtime_checkable
class Indexer(Protocol):
    """STUB in M3: stamps an index_version and returns no point IDs. At M4 this
    embeds and upserts into Qdrant, and `delete_document` issues the filtered
    delete that FR-26 needs."""

    name: str
    index_version: str

    def index(self, document_id: str, chunks: list[Chunk]) -> list[str | None]: ...

    def delete_document(self, document_id: str) -> int: ...
