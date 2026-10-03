# Legal Lens

Grounded reading and drafting over an attorney's own documents. Every output traces to a retrieved
span, or the system declines — a refusal is a first-class success state, not an error.

Ask a question across a document set and get an answer where every sentence carries a citation you
can click through to the exact clause on the exact page. Summarise a 312-page agreement against a
schema that reports an absent term as absent rather than inferring it. Draft a memo or a case brief
from sources you chose. Nothing is answered from the model's own knowledge of the law.

## Run it

```bash
cd backend && make install && make seed && make dev   # http://127.0.0.1:8000
cd frontend && npm install && npm run dev             # http://localhost:5173
```

`make seed` prints the dev credentials — `dana@example.com` / `counsel-demo-2026` — and seeds a
workspace that is deliberately not all healthy: a 312-page MSA, two opinions, a pleading, a scanned
amendment with low-OCR-confidence pages, one document mid-indexing and one hard parse failure.

Or both at once:

```bash
docker compose up --build        # then open localhost:5173
```

Once signed in, try **"What happens on a change of control?"** against the whole workspace, then
click citation `[1]`. It lands on page 84 of the MSA with the assignment clause highlighted, because
the highlight is computed from the character offsets the retrieval actually returned.

Then ask something the corpus does not cover — "what does the MSA say about force majeure?" — and
watch it decline, naming what it searched for and why that fell short.

## Layout

```
backend/     FastAPI · Pydantic v2 · SQLAlchemy 2.0 async + SQLite · Alembic · uv
frontend/    React 19 · TypeScript · Vite · Tailwind v4 · zustand · Radix
docs/        BRD/PRD/FRD, glossary, technical architecture
```

Each has its own README: [backend](backend/README.md) for the API, the data model and what M4
replaces; [frontend](frontend/README.md) for the API seam, the design system and how it reaches the
backend.

The build plans are kept as working documents rather than history:
[BACKEND-TODO.md](BACKEND-TODO.md), [FRONTEND-TODO.md](FRONTEND-TODO.md) and
[INTEGRATION-TODO.md](INTEGRATION-TODO.md).

## Where it stands

The frontend and backend are integrated and run end to end — real session auth, real uploads with
real text extraction, real persistence, real SSE streaming, real hard deletion. The **AI layer is a
port with one implementation**: a server-side fixture engine behind
`backend/app/ai/ports.py`. Retrieval, embeddings, the citation gate and the groundedness check are
M4, and they land behind that boundary without a route, a schema or a frontend file changing.

What that means in practice: the plumbing, the contract and every failure path are real and
verifiable today. The answers are scripted.

```bash
cd backend && make check      # ruff · mypy --strict · openapi freshness · 156 tests
cd frontend && npm run build  # tsc --noEmit + production build
```
