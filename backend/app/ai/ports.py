"""NFR-14: the AI layer is reachable only via `answer()`, `summarize()` and
`draft()`. The backend holds no retrieval or prompt logic.

BRD §7 states the consequence: when this later becomes a multi-agent system, the
change happens behind this interface and touches neither the frontend nor the
API contract. The interface is therefore the deliverable, and the M3 fixture
engine is just its first implementation.

Each method is an async iterator of `StreamEvent`, because streaming is in the
contract (FR-10) and a method returning a finished envelope would make
token-by-token delivery impossible to add later without changing every caller.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.schemas.common import Mode, ScopeUsed
from app.schemas.envelope import DraftParams
from app.schemas.events import StreamEvent


@dataclass
class ScopedDocument:
    """A document the engine is permitted to retrieve from, with everything it
    needs so the engine never touches the database."""

    id: str
    name: str
    type: str
    pages: int
    status: str


@dataclass
class AiRequest:
    """What the orchestration layer will build at M4, and what the route builds
    today. Deliberately free of ORM objects and of `Request`: the engine must be
    callable from a test with a literal."""

    text: str
    mode: Mode
    scope_used: ScopeUsed
    documents: list[ScopedDocument]
    conversation_id: str
    trace_id: str
    user_id: str
    #: Prior turns, oldest first, for the query rewriter at M4.
    history: list[tuple[str, str]] = field(default_factory=list)
    draft_params: DraftParams | None = None
    #: Dev-only override from `X-LegalLens-Scenario`; None in production.
    scenario: str | None = None

    def document(self, document_id: str) -> ScopedDocument | None:
        return next((d for d in self.documents if d.id == document_id), None)

    @property
    def ready_documents(self) -> list[ScopedDocument]:
        """FR-7: only `ready` documents enter retrieval."""
        return [d for d in self.documents if d.status == "ready"]


class AiUnavailable(RuntimeError):
    """The provider is down or rate-limited. NFR-6: retrieval and excerpts keep
    working, so the route turns this into an error event carrying
    `excerptsAvailable: true` rather than failing the request outright."""

    def __init__(self, message: str, *, retry_after_sec: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_sec = retry_after_sec


@runtime_checkable
class AiEngine(Protocol):
    """The whole AI layer, as three callables.

    M3  `FixtureEngine` — fixture lookup plus realistic timings.
    M4  `LangChainEngine` — router, query rewrite, hybrid retrieval, rerank,
        parent expansion, grounded generation, citation gate.
    """

    name: str
    prompt_version: str
    model_version: str
    index_version: str

    def answer(self, request: AiRequest) -> AsyncIterator[StreamEvent]: ...

    def summarize(self, request: AiRequest) -> AsyncIterator[StreamEvent]: ...

    def draft(self, request: AiRequest) -> AsyncIterator[StreamEvent]: ...

    def route_intent(self, request: AiRequest) -> str:
        """Returns one of ask | summary | draft | out_of_scope.

        An explicit mode chip overrides the router — the architecture says so,
        and frontend nuance #4 requires the decision to be visible either way.
        """
        ...
