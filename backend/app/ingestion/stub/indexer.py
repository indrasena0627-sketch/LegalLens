"""STUB. Embedding and vector upsert are M4.

This stamps an `index_version` and returns no point IDs, so `chunk_meta` rows
exist with `vector_point_id = NULL`. At M4 the real indexer embeds with
bge-large-en-v1.5, upserts into Qdrant, and returns the point IDs — one
implementation swap, no schema change.

`delete_document` matters more than it looks: FR-26 requires vector points to go
with everything else, and the hard-delete service already calls it. When Qdrant
lands, that call becomes a filtered delete and nothing above it changes.
"""

from __future__ import annotations

import logging

from app.ingestion.ports import Chunk

log = logging.getLogger("legallens.ingest.index")


class StubIndexer:
    name = "indexer/stub-m3"
    index_version = "stub-m3-v1"

    def index(self, document_id: str, chunks: list[Chunk]) -> list[str | None]:
        log.info(
            "indexed %d chunks for %s into %s (no vectors — M3 stub)",
            len(chunks),
            document_id,
            self.index_version,
        )
        return [None] * len(chunks)

    def delete_document(self, document_id: str) -> int:
        """No vector store, so nothing to delete — reported as 0 rather than
        silently succeeding, so the delete log says what actually happened."""
        return 0
