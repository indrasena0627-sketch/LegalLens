"""STUB. Real OCR (Tesseract / PaddleOCR) is M4.

What this stub does honestly: it reports that OCR *would* be required, produces
per-page confidences, and lets the pipeline exercise the DR-1 path — flagged
pages, a mean confidence, and the below-floor failure that quarantines a
document rather than indexing text nobody should rely on.

What it does not do: invent text. A page with no text layer gets an empty page
and a low confidence, so the document ends up `failed` with a real reason rather
than `ready` with fabricated content. Returning plausible-looking text here
would be the single most dishonest thing this backend could do.
"""

from __future__ import annotations

import hashlib

from app.config import get_settings
from app.ingestion.ports import ParsedPage, ParseResult


class StubOcr:
    name = "ocr/stub-m3"

    def run(self, path: str, pages: list[int], *, total_pages: int) -> ParseResult:
        settings = get_settings()
        # Deterministic per file, so the same upload always reports the same
        # confidences and a test can assert on them.
        seed = int(hashlib.sha256(path.encode()).hexdigest()[:8], 16)

        out: list[ParsedPage] = []
        for page_no in pages:
            # Spread across the floor so both the flagged-page path (DR-1) and
            # the quarantine path get exercised by real uploads.
            confidence = 0.26 + ((seed + page_no * 37) % 61) / 100
            out.append(
                ParsedPage(
                    page_no=page_no,
                    text="",
                    ocr_confidence=round(min(confidence, 0.97), 2),
                    engine=self.name,
                )
            )

        mean = sum(p.ocr_confidence or 0 for p in out) / max(1, len(out))
        warnings = [
            f"OCR is stubbed in M3: {len(pages)} page(s) have no text layer and no "
            f"real OCR engine is wired up (mean simulated confidence {mean:.2f}, "
            f"floor {settings.ocr_confidence_floor:.2f})."
        ]
        return ParseResult(pages=out, scanned=True, engine=self.name, warnings=warnings)
