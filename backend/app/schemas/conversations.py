"""Conversations and turns. Mirrors `Conversation`, `UserTurn`, `AssistantTurn`
in types.ts. The discriminator the frontend switches on is `role`.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from app.schemas.base import CamelModel, StrictCamelModel
from app.schemas.common import ApiError as ApiErrorModel
from app.schemas.common import (
    Citation,
    Coverage,
    Excerpt,
    FeedbackReason,
    FeedbackVerdict,
    Intent,
    Mode,
    OutputKind,
    Refusal,
    Scope,
    ScopeUsed,
    Stage,
    TurnStatus,
    Usage,
    Versions,
)
from app.schemas.envelope import DraftParams, DraftPayload, SummaryPayload


class Feedback(CamelModel):
    verdict: FeedbackVerdict
    reasons: list[FeedbackReason] = Field(default_factory=list)
    note: str | None = None


class UserTurn(CamelModel):
    id: str
    role: Literal["user"] = "user"
    text: str
    mode: Mode
    scope: Scope
    draft_params: DraftParams | None = None
    created_at: str


class AssistantTurn(CamelModel):
    id: str
    role: Literal["assistant"] = "assistant"
    status: TurnStatus
    kind: OutputKind
    # The mode the user picked, kept so `auto → ask` stays visible.
    requested_mode: Mode
    intent: Intent | None = None
    text: str = ""
    citations: list[Citation] = Field(default_factory=list)
    excerpts: list[Excerpt] = Field(default_factory=list)
    scope_used: ScopeUsed | None = None
    stages: list[Stage] = Field(default_factory=list)
    summary: SummaryPayload | None = None
    draft: DraftPayload | None = None
    refusal: Refusal | None = None
    error: ApiErrorModel | None = None
    coverage: Coverage | None = None
    usage: Usage | None = None
    versions: Versions | None = None
    trace_id: str | None = None
    disclaimer: str | None = None
    feedback: Feedback | None = None
    created_at: str


Turn = Annotated[UserTurn | AssistantTurn, Field(discriminator="role")]


class ConversationSummary(CamelModel):
    id: str
    title: str
    last_message_at: str
    pinned: bool
    dominant_kind: OutputKind
    turn_count: int


class Conversation(ConversationSummary):
    turns: list[Turn] = Field(default_factory=list)


class ConversationCreate(StrictCamelModel):
    title: str = "New chat"


class ConversationPatch(StrictCamelModel):
    """⊕ `pinned` is not in the architecture's endpoint list but client.ts
    calls `setPinned`, so it lands here rather than as a second route."""

    title: str | None = None
    pinned: bool | None = None


class ConversationPage(CamelModel):
    items: list[ConversationSummary] = Field(default_factory=list)
    next_cursor: str | None = None


class TurnPage(CamelModel):
    items: list[Turn] = Field(default_factory=list)
    next_cursor: str | None = None


class SendMessageRequest(StrictCamelModel):
    """Body of POST /api/conversations/{id}/messages. `conversation_id` is in
    the path; types.ts carries it in the object too, so it is accepted and
    ignored rather than rejected by `extra='forbid'`."""

    conversation_id: str | None = None
    text: str = Field(min_length=1, max_length=8000)
    mode: Mode = "auto"
    scope: Scope = Field(default_factory=Scope)
    draft_params: DraftParams | None = None


class ModeRequest(SendMessageRequest):
    """Body of the explicit-mode endpoints. `conversation_id` optional: when
    absent the endpoint creates a conversation, so /api/ask works standalone."""
