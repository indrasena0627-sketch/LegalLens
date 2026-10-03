"""The six ingestion steps of architecture band 7, each a port call.

    (1) upload & validate    → app/ingestion/validate.py, at the route
    (2) job queue            → app/ingestion/queue.py
    (3) parse: layout + OCR  → extract/* (real) + stub/ocr (stub)
    (4) layout QA gate       → stub/layout_qa
    (5) classify · segment · chunk
    (6) embed & index        → stub/indexer, then status = ready

The status machine is the contract the frontend's upload queue polls, and
`steps_json` is shaped as `IngestionStep[]` so the detail drawer renders it
without translation.

Everything CPU-bound — pypdf, python-docx, chunking, AES — goes through
`asyncio.to_thread`. Everything touching the database stays on the caller's
loop, because an async engine is bound to the loop that created it. Getting
that split wrong is how a 500-page parse stalls every in-flight SSE stream.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.ingestion.extract import parser_for
from app.ingestion.ports import ParsedPage, ParseResult
from app.ingestion.stub import (
    SectionAwareChunker,
    StubClassifier,
    StubIndexer,
    StubLayoutQa,
    StubOcr,
)
from app.models import (
    ChunkMeta,
    Document,
    DocumentPage,
    DocumentSpan,
    IngestionJob,
    UsageTransaction,
)
from app.models.base import prefixed_id, utcnow
from app.services import audit
from app.storage import blob

log = logging.getLogger("legallens.ingest")

OCR = StubOcr()
LAYOUT_QA = StubLayoutQa()
CLASSIFIER = StubClassifier()
CHUNKER = SectionAwareChunker()
INDEXER = StubIndexer()


class IngestionFailure(Exception):
    """A terminal, reportable failure.

    Carries the two-part message the UI shows — a one-line reason and a detail
    naming a next action — plus the step log as it stood when the failure
    happened. The log travels with the exception because the failure handler
    runs in a *different* session: anything merely assigned to the job here
    would be rolled back and never reach the detail drawer.
    """

    def __init__(self, reason: str, detail: str, steps: list[dict[str, Any]] | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail
        self.steps = steps or []


@dataclass
class StepLog:
    """Accumulates `IngestionStep[]` as the pipeline runs, so a document being
    processed shows real progress rather than an indeterminate spinner.

    Always persisted via `snapshot()`. A plain JSON column does not track
    in-place mutation, and assigning the same list object back is invisible to
    the ORM — so appends would silently never reach the database.
    """

    steps: list[dict[str, Any]]

    def snapshot(self) -> list[dict[str, Any]]:
        return [dict(s) for s in self.steps]

    def done(self, label: str, ms: float, detail: str | None = None) -> None:
        self.steps.append(
            {
                "label": label,
                "status": "done",
                "ms": int(ms),
                **({"detail": detail} if detail else {}),
            }
        )

    def active(self, label: str, detail: str | None = None) -> None:
        self.steps.append(
            {"label": label, "status": "active", **({"detail": detail} if detail else {})}
        )

    def failed(self, label: str, ms: float, detail: str | None = None) -> None:
        self.steps.append(
            {
                "label": label,
                "status": "failed",
                "ms": int(ms),
                **({"detail": detail} if detail else {}),
            }
        )

    def pending(self, *labels: str) -> None:
        for label in labels:
            self.steps.append({"label": label, "status": "pending"})

    def replace_active(self, label: str, ms: float, detail: str | None = None) -> None:
        for step in reversed(self.steps):
            if step["status"] == "active":
                step.update(
                    {"label": label, "status": "done", "ms": int(ms)},
                )
                if detail:
                    step["detail"] = detail
                return
        self.done(label, ms, detail)


async def run_pipeline(db: AsyncSession, job: IngestionJob, document: Document) -> None:
    """Run steps 3–6 for one document. Raises IngestionFailure on a terminal
    failure; any other exception is retried by the queue."""
    settings = get_settings()
    t0 = time.perf_counter()
    steps = StepLog(steps=list(job.steps_json or []))
    if not steps.steps:
        steps.done("Uploaded", 0)

    source = await asyncio.to_thread(_decrypt_to_temp, document)
    try:
        # ---- (3) parse: text layer, then OCR where there isn't one ----------
        document.status = "parsing"
        document.progress = 10
        job.step = "parsing"
        job.steps_json = steps.snapshot()
        await db.commit()

        parse_started = time.perf_counter()
        result = await asyncio.to_thread(_parse, source, document, settings.max_pages)
        parse_ms = (time.perf_counter() - parse_started) * 1000

        if result.scanned:
            steps.done("No text layer found", 180, "fell back to OCR")
            document.status = "ocr"
            document.progress = 35
            job.step = "ocr"
            job.steps_json = steps.snapshot()
            await db.commit()

            ocr_pages = [p.page_no for p in result.pages if len(p.text) < 40]
            ocr_result = await asyncio.to_thread(
                OCR.run, str(source), ocr_pages, total_pages=result.page_count
            )
            result = _merge_ocr(result, ocr_result)
            mean = _mean_confidence(result.pages)
            flagged = [
                p.page_no
                for p in result.pages
                if p.ocr_confidence is not None and p.ocr_confidence < settings.ocr_confidence_floor
            ]
            steps.done(
                "OCR complete",
                parse_ms,
                f"mean confidence {mean:.2f}"
                + (f" · {len(flagged)} page(s) flagged" if flagged else ""),
            )
        else:
            steps.done(
                "Text extracted",
                parse_ms,
                f"{result.engine} · {result.total_chars:,} chars over {result.page_count} pages",
            )

        document.pages = result.page_count

        # ---- (4) layout QA gate --------------------------------------------
        qa_started = time.perf_counter()
        qa = await asyncio.to_thread(LAYOUT_QA.check, result)
        qa_ms = (time.perf_counter() - qa_started) * 1000

        if qa.quarantine:
            steps.failed(
                "Layout QA gate — quarantined",
                qa_ms,
                f"reading order {qa.reading_order_score:.2f}",
            )
            steps.pending("Chunked", "Embedded & indexed")
            raise IngestionFailure(
                reason=_quarantine_reason(result, qa),
                detail=qa.reason or "The document did not pass the layout quality gate.",
                steps=steps.snapshot(),
            )

        steps.done(
            "Layout QA passed",
            qa_ms,
            f"reading order {qa.reading_order_score:.2f}"
            + (f" · {len(qa.flagged_pages)} page(s) flagged" if qa.flagged_pages else ""),
        )

        # DR-1: OCR info is recorded whether or not any page was flagged, so the
        # library badge and the viewer's confidence strip have data to show.
        if result.scanned:
            document.ocr_json = {
                "scanned": True,
                "mean_confidence": round(_mean_confidence(result.pages), 2),
                "low_confidence_pages": qa.flagged_pages,
            }

        # ---- (5) classify · segment · chunk --------------------------------
        document.status = "indexing"
        document.progress = 60
        job.step = "indexing"
        job.steps_json = steps.snapshot()
        await db.commit()

        classify_started = time.perf_counter()
        classification = await asyncio.to_thread(CLASSIFIER.classify, document.name, result.pages)
        # FR-5: an override already made by the attorney outranks the classifier.
        if document.type_source != "overridden":
            document.type = classification.doc_type
        document.classifier_confidence = classification.confidence
        steps.done(
            "Classified",
            (time.perf_counter() - classify_started) * 1000,
            "low confidence — review the type"
            if classification.confidence < 0.7
            else f"{classification.doc_type} · {int(classification.confidence * 100)}%",
        )

        chunk_started = time.perf_counter()
        chunks = await asyncio.to_thread(CHUNKER.chunk, result.pages, document.type)
        children = [c for c in chunks if not c.is_parent]
        steps.done(
            "Chunked",
            (time.perf_counter() - chunk_started) * 1000,
            f"{len(children)} chunks · {len([c for c in chunks if c.is_parent])} parent sections",
        )

        # ---- persist pages, spans and chunk rows ---------------------------
        await _persist_pages(db, document, result.pages)
        span_count = await _persist_spans(db, document, chunks)
        await _persist_chunks(db, document, chunks)
        document.progress = 85
        job.steps_json = steps.snapshot()
        await db.commit()

        # ---- (6) embed & index ---------------------------------------------
        index_started = time.perf_counter()
        await asyncio.to_thread(INDEXER.index, document.id, children)
        steps.done(
            "Embedded & indexed",
            (time.perf_counter() - index_started) * 1000,
            f"{INDEXER.index_version} · {span_count} resolvable spans",
        )

        # FR-7: only now does the document enter retrieval.
        document.status = "ready"
        document.progress = 100
        document.failure_reason = None
        document.failure_detail = None
        job.status = "done"
        job.step = "ready"
        job.steps_json = steps.snapshot()
        job.finished_at = utcnow()

        # NFR-8: ≤ $0.50 per document ingested, attributed per request and
        # visible in `GET /api/usage`. A ledger row, not a log line — the
        # budget is only checkable if it can be summed.
        elapsed_ms = (time.perf_counter() - t0) * 1000
        db.add(
            UsageTransaction(
                user_id=document.user_id,
                document_id=document.id,
                kind="ingestion",
                input_tokens=sum(c.token_count for c in children),
                output_tokens=0,
                usd=_ingestion_cost(result.page_count, result.scanned),
                latency_ms=elapsed_ms,
                model=INDEXER.index_version,
            )
        )

        audit.record(
            db,
            action=audit.ACTION_INGEST_COMPLETE,
            user_id=document.user_id,
            document_ids=[document.id],
            index_version=INDEXER.index_version,
            detail={
                "pages": result.page_count,
                "chunks": len(children),
                "spans": span_count,
                "scanned": result.scanned,
                "engine": result.engine,
                "elapsed_ms": int(elapsed_ms),
            },
        )
        await db.commit()
        log.info(
            "ingested %s: %d pages, %d chunks, %d spans in %.1fs",
            document.id,
            result.page_count,
            len(children),
            span_count,
            time.perf_counter() - t0,
        )
    finally:
        await asyncio.to_thread(source.unlink, True)


#: Per-page cost model. M3 has no embedding spend, so this is the parse and
#: storage cost only; M4 replaces it with real token accounting from the
#: embedding call. Deliberately a function so the NFR-8 budget assertion in
#: `tests/test_documents.py` has one place to point at.
COST_PER_PAGE_PARSE_USD = 0.0004
COST_PER_PAGE_OCR_USD = 0.0021


def _ingestion_cost(pages: int, scanned: bool) -> float:
    rate = COST_PER_PAGE_OCR_USD if scanned else COST_PER_PAGE_PARSE_USD
    return round(pages * rate, 6)


def _quarantine_reason(result: ParseResult, qa: object) -> str:
    failed_pages = sum(1 for p in result.pages if len(p.text) < 40)
    if failed_pages and result.page_count:
        return f"Text extraction failed on {failed_pages} of {result.page_count} pages"
    return "The document did not pass the layout quality gate"


def _parse(source: Path, document: Document, max_pages: int) -> ParseResult:
    parser = parser_for(document.ext)
    if parser is None:
        raise IngestionFailure(
            reason=f"No parser for {document.ext}",
            detail="This file type is not supported. Legal Lens accepts PDF, DOCX and TXT.",
        )
    try:
        return parser.parse(str(source), max_pages=max_pages)
    except ValueError as exc:
        raise IngestionFailure(reason="The document could not be read", detail=str(exc)) from exc


def _merge_ocr(base: ParseResult, ocr: ParseResult) -> ParseResult:
    """OCR output replaces only the pages it covered, so a part-scanned PDF
    keeps its machine-readable pages."""
    by_page = {p.page_no: p for p in base.pages}
    for page in ocr.pages:
        existing = by_page.get(page.page_no)
        by_page[page.page_no] = ParsedPage(
            page_no=page.page_no,
            text=page.text or (existing.text if existing else ""),
            ocr_confidence=page.ocr_confidence,
            engine=page.engine,
        )
    return ParseResult(
        pages=[by_page[k] for k in sorted(by_page)],
        scanned=True,
        engine=f"{base.engine}+{ocr.engine}",
        warnings=[*base.warnings, *ocr.warnings],
    )


def _mean_confidence(pages: list[ParsedPage]) -> float:
    scored = [p.ocr_confidence for p in pages if p.ocr_confidence is not None]
    return sum(scored) / len(scored) if scored else 1.0


def _decrypt_to_temp(document: Document) -> Path:
    """The pipeline needs a file on disk; the stored blob is encrypted. The
    plaintext lives in the data dir for the duration of the job and is unlinked
    in a `finally`, so a crashed worker leaves at most one file behind — which
    the next startup sweeps."""
    if not document.blob_key:
        raise IngestionFailure(
            reason="The uploaded file is missing",
            detail="The stored file could not be located. Upload it again.",
        )
    data = blob.read(document.blob_key)
    tmp_dir = get_settings().data_dir / "work"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    path = tmp_dir / f"{document.id}{document.ext}"
    path.write_bytes(data)
    return path


async def _persist_pages(db: AsyncSession, document: Document, pages: list[ParsedPage]) -> None:
    """Page text is encrypted at rest — it is as privileged as the PDF (DR-5)."""
    existing = await db.execute(select(DocumentPage).where(DocumentPage.document_id == document.id))
    for row in existing.scalars():
        if row.text_key:
            await asyncio.to_thread(blob.delete, row.text_key)
        await db.delete(row)
    await db.flush()

    doc_offset = 0
    for page in pages:
        key = blob.object_key("pages", document.id, f"p{page.page_no}")
        await asyncio.to_thread(blob.write_text, key, page.text)
        db.add(
            DocumentPage(
                document_id=document.id,
                page_no=page.page_no,
                char_count=len(page.text),
                doc_char_start=doc_offset,
                ocr_confidence=page.ocr_confidence,
                text_key=key,
                parse_engine=page.engine,
            )
        )
        doc_offset += len(page.text) + 1
    await db.flush()


async def _persist_spans(db: AsyncSession, document: Document, chunks: list[Any]) -> int:
    """One span per child chunk. Offsets are page-local to `page_from`, which is
    the unit the viewer can highlight (BACKEND-TODO §8.2)."""
    existing = await db.execute(select(DocumentSpan).where(DocumentSpan.document_id == document.id))
    for row in existing.scalars():
        await db.delete(row)
    await db.flush()

    count = 0
    for chunk in chunks:
        if chunk.is_parent:
            continue
        db.add(
            DocumentSpan(
                id=prefixed_id("s"),
                document_id=document.id,
                page_no=chunk.page_from,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                section=chunk.section_path,
            )
        )
        count += 1
    await db.flush()
    return count


async def _persist_chunks(db: AsyncSession, document: Document, chunks: list[Any]) -> None:
    existing = await db.execute(select(ChunkMeta).where(ChunkMeta.document_id == document.id))
    for row in existing.scalars():
        await db.delete(row)
    await db.flush()

    parent_ids: dict[str, str] = {}
    for chunk in chunks:
        if not chunk.is_parent:
            continue
        row = ChunkMeta(
            document_id=document.id,
            page_from=chunk.page_from,
            page_to=chunk.page_to,
            char_start=chunk.char_start,
            char_end=chunk.char_end,
            section_path=chunk.section_path,
            clause_no=chunk.clause_no,
            token_count=chunk.token_count,
            index_version=INDEXER.index_version,
        )
        db.add(row)
        await db.flush()
        if chunk.parent_key:
            parent_ids[chunk.parent_key] = row.id

    for chunk in chunks:
        if chunk.is_parent:
            continue
        db.add(
            ChunkMeta(
                document_id=document.id,
                parent_chunk_id=parent_ids.get(chunk.parent_key or ""),
                page_from=chunk.page_from,
                page_to=chunk.page_to,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                section_path=chunk.section_path,
                clause_no=chunk.clause_no,
                token_count=chunk.token_count,
                index_version=INDEXER.index_version,
                vector_point_id=None,  # M4 fills this in
            )
        )
    await db.flush()
