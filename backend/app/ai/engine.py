"""The one place the concrete AI engine is chosen.

NFR-14 says the backend reaches the AI layer only through `answer()`,
`summarize()` and `draft()`. Routes therefore import `get_engine()` from here
and receive something typed as `AiEngine` — they never name an implementation.

**This is the M4 swap point.** When the LangChain orchestration lands, it is one
return statement in this file. No route, schema, service or test changes, which
is the property the three-function interface exists to buy (BRD §7).
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.ports import AiEngine


@lru_cache
def get_engine() -> AiEngine:
    """The process-wide AI layer.

    Cached because an engine is stateless configuration, not per-request state;
    at M4 it will also hold warmed model clients, which must not be rebuilt per
    turn.
    """
    from app.ai.fixture_engine import FixtureEngine

    return FixtureEngine()


def reset_engine() -> None:
    """Drop the cached engine. For tests that swap in a double."""
    get_engine.cache_clear()
