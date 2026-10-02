#!/usr/bin/env python3
"""Generates legallens-technical-flow.excalidraw — LegalLens v1 technical flow.

Regenerate:  uv run python docs/architecture/legallens_flow_gen.py
Layout is coordinate-driven; edit the NODES / EDGES tables at the bottom.
"""
import json, random, os

E = []
_seed = random.Random(7)

def _n():  return _seed.randint(1, 2**31 - 1)

def _base(**kw):
    d = dict(id=kw.pop("id"), type=kw.pop("type"), x=kw.pop("x"), y=kw.pop("y"),
             width=kw.pop("width"), height=kw.pop("height"), angle=0,
             strokeColor="#1e1e1e", backgroundColor="transparent", fillStyle="solid",
             strokeWidth=2, strokeStyle="solid", roughness=0, opacity=100,
             groupIds=kw.pop("groupIds", []), frameId=None, index=None,
             roundness=None, seed=_n(), version=1, versionNonce=_n(),
             isDeleted=False, boundElements=None, updated=1, link=None, locked=False)
    d.update(kw)
    return d

# ---------------------------------------------------------------- primitives
def rect(id, x, y, w, h, stroke="#1e1e1e", bg="transparent", sw=2, ss="solid",
         round=True, group=None, locked=False, fill="solid"):
    e = _base(id=id, type="rectangle", x=x, y=y, width=w, height=h,
              strokeColor=stroke, backgroundColor=bg, strokeWidth=sw,
              strokeStyle=ss, fillStyle=fill,
              roundness={"type": 3} if round else None,
              groupIds=[group] if group else [], locked=locked)
    E.append(e); return e

def ellipse(id, x, y, w, h, stroke="#1e1e1e", bg="transparent", group=None):
    e = _base(id=id, type="ellipse", x=x, y=y, width=w, height=h,
              strokeColor=stroke, backgroundColor=bg, strokeWidth=2,
              groupIds=[group] if group else [])
    E.append(e); return e

def diamond(id, x, y, w, h, stroke="#1e1e1e", bg="transparent", group=None):
    e = _base(id=id, type="diamond", x=x, y=y, width=w, height=h,
              strokeColor=stroke, backgroundColor=bg, strokeWidth=2,
              groupIds=[group] if group else [])
    E.append(e); return e

_CW = {1: 0.54, 2: 0.52, 3: 0.60}   # avg char-width / fontSize, per family

def text(id, x, y, s, size=16, color="#1e1e1e", fam=2, align="left",
         group=None, bold=False):
    lines = s.split("\n")
    w = max(len(l) for l in lines) * size * _CW[fam] + 2
    lh = 1.25
    h = len(lines) * size * lh
    if align == "center":  x -= w / 2
    elif align == "right": x -= w
    e = _base(id=id, type="text", x=x, y=y, width=w, height=h,
              strokeColor=color, groupIds=[group] if group else [],
              text=s, originalText=s, fontSize=size,
              fontFamily=(1 if bold else fam), textAlign=align,
              verticalAlign="top", containerId=None, lineHeight=lh,
              autoResize=True)
    E.append(e); return e

def arrow(id, pts, stroke="#1e1e1e", sw=2, ss="solid", head="arrow",
          start_head=None, group=None):
    ox, oy = pts[0]
    rel = [[px - ox, py - oy] for px, py in pts]
    xs = [p[0] for p in rel]; ys = [p[1] for p in rel]
    e = _base(id=id, type="arrow", x=ox, y=oy,
              width=max(xs) - min(xs), height=max(ys) - min(ys),
              strokeColor=stroke, strokeWidth=sw, strokeStyle=ss,
              roundness={"type": 2}, groupIds=[group] if group else [],
              points=rel, lastCommittedPoint=None, startBinding=None,
              endBinding=None, startArrowhead=start_head, endArrowhead=head,
              elbowed=False)
    E.append(e); return e

# ---------------------------------------------------------------- composites
def band(id, x, y, w, h, label, stroke, bg, sub=""):
    """A locked background swim-lane with its title at top-left."""
    rect(id, x, y, w, h, stroke=stroke, bg=bg, sw=1.5, ss="dashed",
         locked=True, fill="solid")
    text(id + "_t", x + 26, y + 16, label, size=26, color=stroke, bold=True)
    if sub:
        text(id + "_s", x + 26, y + 50, sub, size=15, color=stroke)

def card(id, x, y, w, h, title, body, stroke, bg, tsize=18, bsize=13.5,
         bfam=2, badge=None, bstroke=None):
    """Titled box. `body` lines are left-aligned under a centred title."""
    g = "g_" + id
    rect(id, x, y, w, h, stroke=stroke, bg=bg, sw=2.5, group=g)
    text(id + "_h", x + w / 2, y + 14, title, size=tsize, color=stroke,
         align="center", bold=True, group=g)
    if body:
        text(id + "_b", x + 16, y + 20 + tsize * 1.45, body, size=bsize,
             fam=bfam, color="#343a40", group=g)
    if badge:
        bs = bstroke or stroke
        bw = len(badge) * 11 * 0.52 + 16
        rect(id + "_bg", x + w - bw - 10, y + h - 28, bw, 20, stroke=bs,
             bg="#ffffff", sw=1.5, group=g)
        text(id + "_bt", x + w - bw / 2 - 10, y + h - 25, badge, size=11,
             color=bs, align="center", group=g)
    return g

def elabel(id, x, y, s, color="#495057", size=13, align="center"):
    """Small edge label on an opaque chip so it never collides with a line."""
    w = len(max(s.split("\n"), key=len)) * size * 0.52 + 14
    h = len(s.split("\n")) * size * 1.25 + 8
    gx = x - w / 2 if align == "center" else x
    rect(id + "_c", gx, y - 4, w, h, stroke="transparent",
         bg="#ffffff", sw=1, round=False)
    text(id, x, y, s, size=size, color=color, align=align)

def tag(id, x, y, letter, note, stroke, bg):
    """Off-page connector: keeps long cross-diagram hops out of the picture."""
    g = "t_" + id
    ellipse(id, x - 21, y - 21, 42, 42, stroke=stroke, bg=bg, group=g)
    text(id + "_l", x, y - 12, letter, size=19, color=stroke, align="center",
         bold=True, group=g)
    text(id + "_n", x + 28, y - 9, note, size=12.5, color=stroke, group=g)

def write(path):
    for i, e in enumerate(E):
        e["index"] = "a" + str(i).zfill(4)
    doc = {"type": "excalidraw", "version": 2,
           "source": "https://excalidraw.com",
           "elements": E,
           "appState": {"gridSize": 20, "gridStep": 5, "gridModeEnabled": False,
                        "viewBackgroundColor": "#ffffff"},
           "files": {}}
    with open(path, "w") as f:
        json.dump(doc, f, indent=1)
    print(f"wrote {path}  ({len(E)} elements)")

# ============================================================== palette
FE  = ("#1971c2", "#e7f5ff")   # frontend        blue
API = ("#e8590c", "#fff4e6")   # api             orange
ORC = ("#9c36b5", "#f8f0fc")   # orchestration   violet
RAG = ("#2f9e44", "#ebfbee")   # ai / rag        green
GAT = ("#c92a2a", "#fff5f5")   # gates           red
DAT = ("#0c8599", "#e3fafc")   # data stores     teal
ING = ("#5f3dc4", "#f3f0ff")   # ingestion       indigo
EXT = ("#495057", "#f1f3f5")   # external        slate

BL = "#1e1e1e"
# ============================================================== geometry
L, R = 300, 4900                    # lane inner left / right
W    = R - L                        # 4600
C5   = [680, 1640, 2600, 3560, 4520]        # 5-column centres
X5   = [c - 380 for c in C5]                # 5-column x (w=760)
C3   = [1000, 2600, 4200]                   # 3-column centres
X3   = [c - 700 for c in C3]                # 3-column x (w=1400)
W5, W3 = 760, 1400

def row6(w=700, gap=80):
    return [L + i * (w + gap) for i in range(6)]
X6 = row6()                                  # 6-across row
def row4(w=1060, gap=120):
    return [L + i * (w + gap) for i in range(4)]
X4 = row4()

# ============================================================== title
text("title", L, 10, "LegalLens — Technical Architecture: End-to-End Request & Ingestion Flow",
     size=40, color=BL, bold=True)
text("title2", L, 68,
     "v1 · single-workspace · React+Vite+TS  ·  FastAPI  ·  LangChain orchestration  ·  hybrid RAG  ·  SQLite + Qdrant     "
     "|  companion to docs/LegalLens-BRD-PRD-FRD.md", size=16, color="#868e96")

# ============================================================== bands
band("b_fe",  L - 40, 140,  W + 80, 500,  "1 · CLIENT / FRONTEND", FE[0],  "#f8fcff",
     "React + Vite + TypeScript · SPA · all transport over HTTPS")
band("b_api", L - 40, 690,  W + 80, 690,  "2 · API LAYER", API[0], "#fffbf5",
     "FastAPI · Pydantic · OpenAPI 3.1 · SSE")
band("b_orc", L - 40, 1430, W + 80, 640,  "3 · ORCHESTRATION", ORC[0], "#fdfaff",
     "LangChain (LCEL) · one router, three workflows · the only caller of the AI layer")
band("b_rag", L - 40, 2120, W + 80, 1990, "4 · AI / RAG LAYER", RAG[0], "#f9fefa",
     "Not naive RAG — query rewrite → hybrid → rerank → parent expansion → grounded")
band("b_tail", L - 40, 4160, W + 80, 580, "5 · VERIFICATION & RESPONSE TAIL", GAT[0], "#fffafa",
     "Nothing reaches the user without passing the citation gate — FR-21, FR-22, TS-2")
band("b_dat", L - 40, 4790, W + 80, 540,  "6 · PERSISTENCE", DAT[0], "#f5fdfe",
     "SQLite = conversations, messages, citations, transactions, audit · Qdrant = vectors · encrypted blob + parsed-text stores")
band("b_ing", L - 40, 5380, W + 80, 800,  "7 · INGESTION PIPELINE  (asynchronous · off the request path)", ING[0], "#fbfaff",
     "Where the hostile-PDF risk is confronted — BRD §15: layout-aware parse, OCR, and a layout QA gate before anything is indexed")
band("b_ext", L - 40, 6230, W + 80, 540,  "8 · EXTERNAL MODELS & CROSS-CUTTING", EXT[0], "#f9fafb",
     "Model providers under zero-retention terms (NFR-10) · tracing, cost, versioning, CI eval gate")

# ============================================================== LANE 1 — frontend
fe = [
 ("fe_side", "SIDEBAR",
  "• Conversation list (title, last-msg time)\n• “+ New chat”  →  NCC endpoint\n"
  "• Rename / delete / pin a thread\n• Workspace doc count + index health\n• Infinite scroll, cursor-paged", "US-10"),
 ("fe_prompt", "PROMPT BAR",
  "• Multiline input + Cmd+Enter send\n• Mode chips:  Auto | Ask | Summary | Draft\n"
  "• Scope picker: this doc / subset / workspace\n• Draft param drawer (QP, audience,\n   position, tone)\n• Attach-file shortcut", "FR-8, FR-19"),
 ("fe_chat", "CHAT PANE",
  "• SSE token stream, incremental render\n• Inline citation chips  [1] [2] [3]\n"
  "• Refusal card — a success state, not an error\n• Persistent “UNREVIEWED AI DRAFT” banner\n• thumbs up / down + reason on every turn", "FR-10, FR-14, FR-23"),
 ("fe_lib", "DOCUMENT LIBRARY",
  "• Multi-file drag-drop + picker\n• Per-file status: queued → parsing →\n   indexing → ready | failed\n"
  "• Detected type + manual override\n• Low-OCR-confidence page warnings\n• Delete (document / workspace)", "FR-1, FR-3, FR-5"),
 ("fe_cite", "CITATION & EXCERPT VIEWER",
  "• Retrieved excerpts beside the answer\n• Click chip → open doc, scroll to page,\n   highlight the char span\n"
  "• Page image + text-layer overlay\n• Keyboard-navigable, SR-announced", "FR-12, FR-13, NFR-13"),
]
for i, (id, t, b, badge) in enumerate(fe):
    card(id, X5[i], 250, W5, 280, t, b, FE[0], FE[1], tsize=17, bsize=12.5, badge=badge)

# ============================================================== LANE 2 — api
card("api_gw", L, 800, W, 92,
     "FastAPI APPLICATION  ·  ASGI / Uvicorn",
     "middleware chain:   session auth (cookie)  →  request-id + trace span  →  rate limit  →  Pydantic request validation  →  route  →  response envelope  →  audit write",
     API[0], "#ffe8cc", tsize=19, bsize=13.5)

api = [
 ("api_conv", "CONVERSATIONS API",
  "POST   /api/conversations        ← NCC\nGET    /api/conversations?cursor=\n"
  "GET    /api/conversations/{id}\nGET    /api/conversations/{id}/messages\nPATCH  /api/conversations/{id}   (title)\nDELETE /api/conversations/{id}", "NCC"),
 ("api_turn", "CHAT TURN API   (SSE)",
  "POST   /api/conversations/{id}/messages\n  body: {text, mode:auto|ask|summary\n         |draft, scope, draft_params}\n"
  "  ← text/event-stream:\n     token · citation · excerpt ·\n     refusal · usage · done", "FR-10"),
 ("api_mode", "MODE ENDPOINTS   (explicit)",
  "POST   /api/ask        (SSE)\nPOST   /api/summarize  (SSE)\nPOST   /api/draft      (SSE)\n"
  "\nused when the user picks a mode —\nskips the intent router, same\nworkflow underneath", "BRD §7"),
 ("api_doc", "DOCUMENTS API",
  "POST   /api/documents          multipart\nGET    /api/documents\nGET    /api/documents/{id}\n"
  "GET    /api/documents/{id}/status\nGET    /api/documents/{id}/pages/{n}\nPATCH  /api/documents/{id}  (type)\nDELETE /api/documents/{id}", "FR-1, FR-26"),
 ("api_misc", "SPANS · FEEDBACK · TRACE",
  "GET    /api/spans/{span_id}\nPOST   /api/feedback\nGET    /api/traces/{trace_id}\n"
  "GET    /api/usage              $ ledger\nPOST   /api/auth/login\nGET    /api/auth/me", "FR-25, NFR-11"),
]
for i, (id, t, b, badge) in enumerate(api):
    card(id, X5[i], 960, W5, 300, t, b, API[0], API[1],
         tsize=16, bsize=12, bfam=3, badge=badge)

# ============================================================== LANE 3 — orchestration
card("orc_hdr", L, 1510, W, 86,
     "ORCHESTRATOR SERVICE  —  LangChain / LCEL",
     "the backend holds no retrieval or prompt logic (NFR-14) · exposed to FastAPI as exactly three callables:   answer(req) | summarize(req) | draft(req)   → each returns a response model with citations attached",
     ORC[0], "#f3d9fa", tsize=19, bsize=13.5)

card("orc_ctx", 300, 1660, 1100, 310, "TURN CONTEXT BUILDER",
     "• load thread from SQLite: last N=8 turns\n• rolling summary buffer for older turns\n"
     "• resolve referenced doc IDs + prior\n   citations (“that clause you quoted”)\n• attach user_id, workspace, trace_id",
     ORC[0], ORC[1], tsize=17, bsize=13, badge="SQLite read")

card("orc_rt", 1750, 1660, 1500, 310, "INTENT ROUTER   ·   LLM CLASSIFIER",
     "small fast model + structured output (Pydantic enum), few-shot, conversation-aware\n"
     "   intent = one of { ask · summary · draft · out_of_scope }   +   confidence   +   extracted slots\n"
     "   ask → question, scope        summary → doc_id, template override\n"
     "   draft → draft_type, params   out_of_scope → refusal reason\n"
     "fallbacks:  explicit mode chip overrides the router  ·  confidence < 0.6 → ask the user to disambiguate",
     ORC[0], "#eebefa", tsize=18, bsize=13, badge="LLM call")

card("orc_scope", 3400, 1660, 680, 310, "SCOPE RESOLVER",
     "• this doc / subset /\n   whole workspace (FR-9)\n• drops any doc whose\n   status is not ready (FR-7)\n"
     "• builds the Qdrant\n   payload filter\n• records scope on the\n   response",
     ORC[0], ORC[1], tsize=16, bsize=12.5, badge="FR-7, FR-9")

card("orc_guard", 4180, 1660, 720, 310, "POLICY GUARD",
     "• rate / quota check\n• draft-param validation\n• refuses non-attorney\n   advice framing (TS-5)\n"
     "• no tool call may be\n   driven by document\n   text (TS-4)\n• logs decision to audit",
     GAT[0], GAT[1], tsize=16, bsize=12.5, badge="TS-4, TS-5")

# ============================================================== LANE 4 — workflow headers
for i, (t, sub, intent) in enumerate([
    ("ASK  WORKFLOW", "question → cited answer", "intent = ask"),
    ("SUMMARY  WORKFLOW", "document → structured template", "intent = summary"),
    ("DRAFT  WORKFLOW", "params + sources → memo / case brief", "intent = draft")]):
    card("wf_h%d" % i, X3[i], 2230, W3, 86, t, "   " + sub + "          ( " + intent + " )",
         RAG[0], "#b2f2bb", tsize=19, bsize=13.5)

STEP_H, STEP_GAP = 236, 60
def step(col, k, title, body, stroke=RAG[0], bg=RAG[1], badge=None, bstroke=None):
    y = 2380 + k * (STEP_H + STEP_GAP)
    card("s%d_%d" % (col, k), X3[col] + 60, y, W3 - 120, STEP_H, title, body,
         stroke, bg, tsize=16, bsize=12.5, badge=badge, bstroke=bstroke)
    return y

# ---------- ASK ----------
step(0, 0, "(1) QUERY REWRITER  (LLM)",
     "resolves the turn against conversation history —\nthe reason this is not naive RAG:\n"
     "• pronoun / ellipsis resolution → standalone query\n   “and what about termination?” → “What are the\n   termination rights under the Acme MSA?”\n"
     "• HyDE-style expansion + 3 query variants\n• legal-synonym widening (assignment / transfer,\n   change of control / merger / successor)",
     badge="LLM call")
step(0, 1, "(2) HYBRID RETRIEVAL  (Qdrant)",
     "one query, two vector spaces, server-side fusion:\n"
     "• DENSE   bge-large-en-v1.5, 1024-d, cosine\n• SPARSE  BM25 / SPLADE — exact clause numbers,\n   party names, dollar figures, statute cites\n"
     "• Reciprocal Rank Fusion over both  →  top-k 40\n• payload filter: doc_ids + status=ready + section\n• run all 3 query variants, union + dedupe",
     badge="Q →")
step(0, 2, "(3) CROSS-ENCODER RERANK",
     "bge-reranker-v2-m3 — scores (query, chunk) pairs\njointly instead of comparing two embeddings\n"
     "• 40 candidates  →  top 8\n• score floor 0.25; everything below is dropped\n• if nothing clears the floor → structured refusal,\n   not a low-quality answer  (FR-14)",
     badge="FR-14")
step(0, 3, "(4) PARENT-DOCUMENT EXPANSION",
     "retrieve on small chunks, generate on large ones:\n"
     "• child chunk → its parent section window\n• a numbered clause is expanded whole, never\n   truncated mid-obligation\n"
     "• +/-1 sibling chunk for run-on provisions\n• dedupe overlaps, then fit a token budget",
     badge="precision")
step(0, 4, "(5) CONTEXT ASSEMBLER",
     "untrusted input is fenced, never concatenated:\n"
     "   <document id=... page=... span=...>  ...text...  </document>\n"
     "• system instructions structurally separated from\n   retrieved content  (TS-4)\n"
     "• every block carries its span_id so the model can\n   only cite what it was actually given",
     stroke=GAT[0], bg=GAT[1], badge="TS-4")
step(0, 5, "(6) ANSWER GENERATION  (LLM, streamed)",
     "• cite-as-you-write: every claim ends with\n   [doc_id : page : span_id]\n"
     "• instructed to answer “not in your documents”\n   when the context does not support an answer\n"
     "• tokens streamed straight through to SSE\n• model + prompt version stamped  (NFR-12)",
     badge="LLM call")

# ---------- SUMMARY ----------
step(1, 0, "(1) TYPE RESOLUTION",
     "• classification from the ingestion pipeline\n   (contract | opinion | pleading | other)\n"
     "• user override from the library wins  (FR-5)\n• low classifier confidence → ask before\n   summarising with the wrong template",
     badge="FR-5")
step(1, 1, "(2) TEMPLATE SELECTOR",
     "BRD §9 — three genuinely different schemas:\n"
     "CONTRACT  parties · term · obligations · payment ·\n   termination · liability · assignment/CoC · law\n"
     "OPINION   posture · facts · issues · holding ·\n   reasoning · disposition · separate opinions\n"
     "PLEADING  court · cause · relief · allegations ·\n   theories · dates",
     badge="FR-15")
step(1, 2, "(3) FIELD-WISE RETRIEVAL",
     "one targeted hybrid query per template field,\nnot one query for the whole document:\n"
     "• field → query template (“limitation of liability,\n   cap on damages, consequential damages”)\n"
     "• section-aware filter from the clause tree\n• same hybrid + rerank stack as Ask",
     badge="Q →")
step(1, 3, "(4) MAP  —  per-section extraction",
     "• each retrieved section extracted independently\n   into the field schema, with span_ids\n"
     "• parallel fan-out, bounded concurrency\n• a field with no supporting span is returned\n   empty — never filled by inference  (FR-16)",
     badge="FR-16")
step(1, 4, "(5) REDUCE  —  hierarchical compose",
     "how a 300-page agreement is summarised without\nsilently truncating it  (FR-17):\n"
     "• section summaries → group summaries → document\n• COVERAGE LEDGER: pages seen / skipped / failed,\n   returned with the summary\n"
     "• conflicting extractions surfaced, not averaged",
     badge="FR-17")
step(1, 5, "(6) STRUCTURED SUMMARY OUTPUT",
     "• JSON schema per field + its citation spans\n• absent fields rendered “not addressed in\n   this document”\n"
     "• off-market / unusual terms flagged\n• field-level precision is what makes this\n   measurable at all",
     badge="LLM call")

# ---------- DRAFT ----------
step(2, 0, "(1) PARAMETER VALIDATOR",
     "• draft_type = one of { legal memo, case brief }\n• question presented · audience · position to\n   argue · tone · selected source documents\n"
     "• refuses on an empty source set — a draft with\n   no sources cannot be grounded  (FR-19)",
     badge="FR-19")
step(2, 1, "(2) OUTLINE PLANNER  (LLM)",
     "structure first, prose second:\n"
     "MEMO  Question Presented → Short Answer →\n   Statement of Facts → Discussion → Conclusion\n"
     "BRIEF  Posture → Facts → Issue → Holding →\n   Reasoning → Disposition\n"
     "• emits a per-section retrieval intent",
     badge="FR-18")
step(2, 2, "(3) PER-SECTION RETRIEVAL",
     "• one hybrid + rerank pass per outline section,\n   scoped to the selected sources only\n"
     "• Statement of Facts pulls facts; Discussion\n   pulls holdings and provisions\n"
     "• builds the ALLOWLIST: the exact span set this\n   draft is permitted to cite",
     badge="Q →")
step(2, 3, "(4) SECTION COMPOSER  (LLM, loop)",
     "• sections composed in order, each conditioned on\n   those already written for continuity\n"
     "• every factual assertion carries a span cite\n   (FR-20); argument marked as argument\n"
     "• holds the attorney’s stated position without\n   inventing support for it",
     badge="FR-20")
step(2, 4, "(5) CITATION ALLOWLIST ENFORCER",
     "the rule that keeps this out of Mata v. Avianca:\n"
     "• emitted cites  within  allowlist from step (3)\n• any case cite, statute cite or docket number\n   not present in the sources is STRIPPED — including\n   ones the model “knows” to be real  (FR-22)\n"
     "• Bluebook formatting derived from source text only",
     stroke=GAT[0], bg="#ffc9c9", badge="FR-22")
step(2, 5, "(6) DRAFT ASSEMBLER",
     "• assembles sections into conventional structure\n• stamps UNREVIEWED AI DRAFT into the body and\n   into every export  (FR-23, FR-24)\n"
     "• attaches the full source manifest\n• Markdown + clipboard export",
     badge="FR-23")

# ============================================================== LANE 5 — tail
tail = [
 ("t_gate", "(1) CITATION\nVERIFICATION GATE",
  "for every emitted cite:\n• resolve doc_id → page →\n   char span\n• span must exist AND have\n   been retrieved this turn\n"
  "• fuzzy-match quoted text\n   against the span\nunresolvable → STRIP, or\nREFUSE the whole output",
  GAT[0], "#ffc9c9", "FR-21 · release gate"),
 ("t_ground", "(2) GROUNDEDNESS\nCHECK",
  "claim-level NLI / LLM judge:\n• split output into claims\n• each claim entailed by its\n   cited span?\n"
  "• unsupported claim → drop\n   or downgrade to a hedge\n• score logged per turn\ntarget >= 95%",
  GAT[0], GAT[1], "BRD §5"),
 ("t_filter", "(3) OUTPUT FILTER",
  "documents are untrusted:\n• strips instruction-like text\n   that leaked from a PDF\n"
  "• blocks system-prompt echo\n• blocks any tool/URL the\n   model picked up from\n   document content\n• PII-safe logging",
  GAT[0], GAT[1], "TS-4"),
 ("t_asm", "(4) RESPONSE\nASSEMBLER",
  "one envelope for all three\nworkflows:\n{ answer_md, citations[],\n  excerpts[], scope_used,\n"
  "  intent, refusal?, coverage?,\n  trace_id, model_version,\n  prompt_version, index_version,\n  usage{tok,$}, disclaimer }",
  ORC[0], ORC[1], "NFR-12"),
 ("t_sse", "(5) SSE STREAMER",
  "event types pushed to the\nchat pane:\n  token      incremental text\n  citation   as it resolves\n"
  "  excerpt    retrieved span\n  refusal    first-class state\n  usage      cost + latency\n  done | error\nan interrupted stream is\nmarked incomplete (NFR-7)",
  FE[0], FE[1], "FR-10, NFR-7"),
 ("t_persist", "(6) PERSIST  +  AUDIT",
  "written atomically per turn:\n• message row (user + asst)\n• citation rows → span refs\n"
  "• retrieval trace: queries,\n   candidate ids, scores\n• usage / cost transaction\n• audit row (DR-4)\n• feedback joins later",
  DAT[0], DAT[1], "DR-4, FR-25"),
]
for i, (id, t, b, sc, bgc, badge) in enumerate(tail):
    card(id, X6[i], 4340, 700, 290, t, b, sc, bgc,
         tsize=15, bsize=12, badge=badge, bstroke=sc)

# ============================================================== LANE 6 — persistence
card("db_sql", X4[3], 4910, 1060, 330, "SQLite   —   “conversation DB”",
     "file-backed, zero-ops for v1; Postgres swap at M6 with no schema change\n\n"
     "users · conversations · messages\nmessage_citations (span refs)\ndocuments · document_pages\n"
     "chunk_meta (chunk_id <-> qdrant point)\nfeedback · audit_log\nusage_transactions ($ + tokens)\n"
     "ingestion_jobs · eval_runs\nprompt_versions · index_versions",
     DAT[0], "#99e9f2", tsize=17, bsize=12, badge="DR-3, DR-4")

card("db_qdr", X4[2], 4910, 1060, 330, "Qdrant   —   vector index",
     "collection  legal_chunks\n\nvectors:  dense 1024-d (bge-large)\n          sparse BM25 / SPLADE\n"
     "payload:  doc_id · page · char_start/end\n          section_path · clause_no\n          doc_type · ocr_conf · status\n          parent_chunk_id\n"
     "named-vector hybrid query + RRF,\nserver-side; payload filter does the\ndocument scoping for FR-8",
     DAT[0], "#99e9f2", tsize=17, bsize=12, badge="hybrid")

card("db_blob", X4[0], 4910, 1060, 330, "ENCRYPTED BLOB STORE",
     "• original uploaded file (AES-256 at rest)\n• rendered page images for the citation\n   viewer\n"
     "• SHA-256 content hash → upload dedupe\n• signed, short-lived read URLs only\n• no document content ever leaves for\n   telemetry, analytics or error tracking\n"
     "   (DR-5)\n• TLS in transit throughout (NFR-9)",
     DAT[0], DAT[1], tsize=17, bsize=12, badge="NFR-9, DR-5")

card("db_text", X4[1], 4910, 1060, 330, "PARSED-TEXT + SPAN STORE",
     "the thing that makes a citation clickable:\n\n• full extracted text per page\n"
     "• char-offset map  text <-> page <-> bbox\n• reading order + column assignment\n• section / clause tree per document\n"
     "• per-page OCR confidence\n• parse engine + version (reproducibility)",
     DAT[0], DAT[1], tsize=17, bsize=12, badge="FR-4, FR-13")

# ============================================================== LANE 7 — ingestion
ing = [
 ("i1", "(1) UPLOAD &\nVALIDATE",
  "• type = one of PDF, DOCX, TXT\n• reject > 50 MB or\n   > 500 pages, naming\n   the limit and the\n   actual value (FR-2)\n"
  "• malware scan\n• SHA-256 dedupe\n• write encrypted blob\n• row → documents",
  "FR-1, FR-2"),
 ("i2", "(2) JOB QUEUE",
  "Celery / RQ + Redis\n\n• one job per file —\n   a single failure must\n   not fail the batch\n"
  "• status transitions:\n   queued → parsing →\n   indexing → ready\n   | failed (FR-3)\n• retry w/ backoff\n• progress polled by\n   /documents/{id}/status",
  "FR-3"),
 ("i3", "(3) PARSE:\nLAYOUT + OCR",
  "• format router\n• TEXT-LAYER PROBE:\n   chars/page heuristic →\n   machine-readable vs\n   scanned\n"
  "• LAYOUT PARSER (Docling\n   / unstructured hi_res):\n   reading order, 2-column\n   detection, tables,\n   headers/footers,\n   footnotes, exhibit\n   stamps over body text\n"
  "• OCR (Tesseract /\n   PaddleOCR) on scanned\n   pages, per-page conf",
  "DR-1"),
 ("i4", "(4) LAYOUT QA GATE",
  "the BRD §15 risk, caught\nhere instead of at M4 —\na clause pulled from a\nmis-ordered two-column\npage looks correct, which\nis why it is worse than\nno extraction:\n"
  "• reading-order score\n• column sanity check\n• table integrity check\n• OCR conf < threshold\n   → page flagged, shown\n   in the UI\n• hard fail → quarantine,\n   never indexed",
  "BRD §15"),
 ("i5", "(5) CLASSIFY ·\nSEGMENT · CHUNK",
  "• doc type classifier:\n   contract | opinion |\n   pleading | other\n"
  "• section / clause tree\n   (numbered clauses for\n   contracts, opinion parts)\n"
  "• SECTION-AWARE CHUNKER\n   child  ~512 tok, 64 overlap\n   parent = whole section\n   a numbered clause is\n   never split\n• span offsets preserved",
  "FR-4, FR-5"),
 ("i6", "(6) EMBED & INDEX",
  "• dense embeddings\n   (batched) + sparse\n   BM25 / SPLADE vectors\n"
  "• upsert points → Qdrant\n   with full payload\n• chunk_meta rows →\n   SQLite\n"
  "• index_version stamped\n• status = ready  →\n   document becomes\n   retrievable (FR-7)",
  "FR-7"),
]
for i, (id, t, b, badge) in enumerate(ing):
    card(id, X6[i], 5510, 700, 350, t, b, ING[0], ING[1],
         tsize=15, bsize=11.5, badge=badge, bstroke=ING[0])

X3b = [L + i * (1460 + 110) for i in range(3)]
card("i_del", X3b[0], 5910, 1460, 210, "HARD-DELETE WORKER",
     "delete must be real, and is verified by test rather than asserted (TS-6):  blob → parsed text → span map → page images\n"
     "→ chunk_meta rows → Qdrant points (filtered delete)   ·   effective immediately for retrieval, tombstone kept in audit only",
     GAT[0], GAT[1], tsize=16, bsize=12, badge="FR-26, TS-6", bstroke=GAT[0])
card("i_reidx", X3b[1], 5910, 1460, 210, "RE-INDEX / MIGRATION WORKER",
     "embedding-model or chunking-strategy change => rebuild into a new index_version, shadow-read, then cut over\n"
     "· enables the M6 rollback story · old index retained one version back",
     ING[0], ING[1], tsize=16, bsize=12, badge="M6", bstroke=ING[0])
card("i_qa", X3b[2], 5910, 1460, 210, "PARSE-QUALITY METRICS",
     "parse quality is a first-class metric, not a hope:  per-doc reading-order score · OCR confidence distribution ·\n"
     "table-extraction rate · quarantine rate · measured against a deliberately adversarial document set at M1",
     ING[0], ING[1], tsize=16, bsize=12, badge="BRD §15", bstroke=ING[0])

# ============================================================== LANE 8 — external
card("x_llm", X4[0], 6350, 1060, 330, "LLM PROVIDER   L",
     "zero-retention terms, no training on\nsubmitted content — a stated, verifiable\nproperty of the deployment (NFR-10)\n\n"
     "router / rewriter   fast model\ngeneration · compose   frontier model\ngroundedness judge  separate model\n\n"
     "called ONLY from the orchestration and\nAI layers, never from a route handler",
     EXT[0], "#dee2e6", tsize=17, bsize=12, badge="NFR-10")
card("x_emb", X4[1], 6350, 1060, 330, "EMBEDDING + RERANKER",
     "dense     bge-large-en-v1.5 (1024-d)\nsparse    BM25 / SPLADE\nrerank    bge-reranker-v2-m3\n\n"
     "run locally where confidentiality favours\nit — embeddings of client text need not\nleave the deployment at all\n\n"
     "model id + version pinned per index_version",
     EXT[0], EXT[1], tsize=17, bsize=12, badge="deferred→decided")
card("x_obs", X4[2], 6350, 1060, 330, "OBSERVABILITY",
     "OpenTelemetry + LangSmith traces\n\nevery request traced:\n  retrieval → assembly → generation\n"
     "  → verification, with latency AND cost\n  attributed per stage (NFR-11)\n\n"
     "prompt · model · index version recorded on\nevery generation, making any answer\nreproducible (NFR-12)",
     EXT[0], EXT[1], tsize=17, bsize=12, badge="NFR-11/12")
card("x_eval", X4[3], 6350, 1060, 330, "EVAL HARNESS  ·  CI GATE",
     "labelled set from public-domain documents\nonly — never client files (DR-5)\n\n"
     "retrieval recall@k   (no LLM in the loop)\ncitation precision   100% or the build fails\n"
     "groundedness         >= 95%\ncorrect / false refusal\ndraft acceptance\n\n"
     "runs in CI on every change (NFR-15)",
     GAT[0], "#ffe3e3", tsize=17, bsize=12, badge="NFR-15", bstroke=GAT[0])

# ============================================================== convergence bar
card("t_bar", L, 4250, W, 50,
     "all three workflows converge here  —  no output reaches the user without passing (1) and (2)",
     "", GAT[0], "#ffc9c9", tsize=15)

# ============================================================== arrows
FLOW, SSEC, ASYNC = "#343a40", FE[0], ING[0]
_a = [0]
def A(pts, c=FLOW, ss="solid", sw=2.2, head="arrow"):
    _a[0] += 1
    arrow("ar%03d" % _a[0], pts, stroke=c, sw=sw, ss=ss, head=head)
def LBL(x, y, s, c="#495057", size=13):
    _a[0] += 1
    elabel("al%03d" % _a[0], x, y, s, color=c, size=size)

# ---- 1→2  frontend <-> API gateway -----------------------------------------
req = ["POST /conversations\nGET  /conversations", "POST .../messages\n{text, mode, scope}",
       "POST /feedback", "POST /documents\nmultipart", "GET /spans/{id}"]
for i in range(5):
    A([(C5[i] - 70, 530), (C5[i] - 70, 800)])
    LBL(C5[i] - 70, 588, req[i])
for i, lab in [(0, "thread list\n+ message history"), (2, "SSE event stream"), (3, "per-file status\npoll")]:
    A([(C5[i] + 70, 800), (C5[i] + 70, 530)], c=SSEC)
    LBL(C5[i] + 70, 700, lab, c=SSEC)
for i in range(5):
    A([(C5[i], 892), (C5[i], 960)], sw=2)
LBL(2600, 912, "route", size=12)

# ---- 2→3  API → orchestration --------------------------------------------
A([(C5[1], 1260), (C5[1], 1400), (2500, 1400), (2500, 1510)], sw=2.6)
LBL(1980, 1372, "mode = auto  →  intent router", c=ORC[0])
A([(C5[2], 1260), (C5[2], 1330), (2900, 1330), (2900, 1510)], ss="dashed")
LBL(3060, 1300, "explicit mode  →  router skipped", c=ORC[0])

# ---- inside lane 3 --------------------------------------------------------
for x in (850, 3740, 4540):
    A([(x, 1596), (x, 1660)], sw=2)
A([(1400, 1815), (1750, 1815)], sw=2.6)
LBL(1575, 1778, "history +\nresolved refs")
A([(3250, 1815), (3400, 1815)], sw=2.6)
LBL(3325, 1778, "intent\n+ slots")
A([(4080, 1815), (4180, 1815)], sw=2.6)
LBL(4130, 1778, "filter")

# ---- 3→4  intent fan-out --------------------------------------------------
A([(2300, 1970), (2300, 2020), (1000, 2020), (1000, 2230)], c=RAG[0], sw=2.8)
LBL(1640, 2010, "intent = ask", c=RAG[0], size=14)
A([(2500, 1970), (2500, 2060), (2600, 2060), (2600, 2230)], c=RAG[0], sw=2.8)
LBL(2600, 2110, "intent = summary", c=RAG[0], size=14)
A([(2700, 1970), (2700, 2020), (4200, 2020), (4200, 2230)], c=RAG[0], sw=2.8)
LBL(3470, 2010, "intent = draft", c=RAG[0], size=14)
A([(2400, 1970), (2400, 2138)], c=GAT[0], ss="dashed", sw=2.2)
LBL(2400, 2150, "out_of_scope → refusal, skips retrieval", c=GAT[0], size=12.5)

# ---- inside lane 4: step chains ------------------------------------------
for col in range(3):
    A([(C3[col], 2316), (C3[col], 2380)], c=RAG[0], sw=2)
    for k in range(5):
        y = 2380 + k * 296
        A([(C3[col], y + 236), (C3[col], y + 296)], c=RAG[0], sw=2.4)
LBL(C3[0], 2634, "standalone query\n+ 3 variants", c=RAG[0], size=12)
LBL(C3[0], 2930, "40 candidates", c=RAG[0], size=12)
LBL(C3[0], 3226, "top 8", c=RAG[0], size=12)
LBL(C3[0], 3522, "expanded spans", c=RAG[0], size=12)
LBL(C3[0], 3818, "fenced context", c=RAG[0], size=12)
LBL(C3[1], 2930, "field schema", c=RAG[0], size=12)
LBL(C3[1], 3522, "per-field\nextractions", c=RAG[0], size=12)
LBL(C3[2], 2930, "outline +\nretrieval intents", c=RAG[0], size=12)
LBL(C3[2], 3522, "draft sections", c=RAG[0], size=12)
LBL(C3[2], 3818, "allowlisted\ncites only", c=GAT[0], size=12)

# ---- 4→5  into the tail ---------------------------------------------------
for col in range(3):
    A([(C3[col], 4096), (C3[col], 4250)], c=GAT[0], sw=2.8)
A([(650, 4300), (650, 4340)], c=GAT[0], sw=2.6)

# ---- inside lane 5 --------------------------------------------------------
for i in range(5):
    A([(X6[i] + 700, 4485), (X6[i + 1], 4485)], c=GAT[0] if i < 3 else FLOW, sw=2.4)
A([(X6[5] + 350, 4630), (X6[5] + 350, 4910)], c=DAT[0], ss="dashed", sw=2.4)
LBL(X6[5] + 350, 4712, "write-behind: message · citations · trace · usage · audit", c=DAT[0])

# ---- lane 7 chain + lane 7 → lane 6 --------------------------------------
for i in range(5):
    A([(X6[i] + 700, 5685), (X6[i + 1], 5685)], c=ING[0], sw=2.4)
LBL(X6[3] + 740, 5640, "pass", c=ING[0], size=12)

# ---- off-page connectors --------------------------------------------------
tag("tp1", C5[0], 1330, "P", "threads · messages · audit", DAT[0], DAT[1])
tag("td1", C5[3], 1330, "D", "enqueue ingestion job", ING[0], ING[1])
tag("ts1", C5[4], 1330, "T", "resolve span → page + bbox", DAT[0], DAT[1])
tag("te1", 2760, 586, "E", "from tail 5", SSEC, FE[1])
tag("te2", X6[4] + 660, 4690, "E", "", SSEC, FE[1])

for _i, (_x, _l) in enumerate([(830, "B"), (2010, "T"), (3190, "Q"), (4370, "P")]):
    tag("tst%d" % _i, _x, 5270, _l, "", DAT[0], DAT[1])
for _i, (_x, _l) in enumerate([(650, "B"), (2210, "T"), (4400, "Q"), (4700, "P")]):
    tag("tsb%d" % _i, _x, 5478, _l, "", DAT[0], DAT[1])
tag("td2", 350, 5478, "D", "", ING[0], ING[1])
tag("tl2", 350, 6324, "L", "", EXT[0], EXT[1])

# ============================================================== legend
LX, LY, LW = 5300, 140, 1000
LGBOX = rect("lg", LX, LY, LW, 100, stroke="#868e96", bg="#ffffff", sw=2)
text("lg_h", LX + 28, LY + 24, "HOW TO READ THIS DIAGRAM", size=22, color=BL, bold=True)
text("lg_s", LX + 28, LY + 58,
     "Top to bottom is one request.  Lane 7 runs asynchronously,\noff the request path.", size=13.5, color="#868e96")

y = LY + 118
text("lg_l", LX + 28, y, "LAYERS", size=15, color=BL, bold=True); y += 34
for i, (nm, (sc, bg)) in enumerate([
    ("1  Client / frontend", FE), ("2  API layer", API), ("3  Orchestration", ORC),
    ("4  AI / RAG layer", RAG), ("5  Verification gates", GAT), ("6  Persistence", DAT),
    ("7  Ingestion (async)", ING), ("8  External / cross-cutting", EXT)]):
    rect("lg_sw%d" % i, LX + 30, y, 34, 22, stroke=sc, bg=bg, sw=2)
    text("lg_st%d" % i, LX + 78, y + 2, nm, size=14, color="#343a40")
    y += 32

y += 18
text("lg_a", LX + 28, y, "LINES", size=15, color=BL, bold=True); y += 34
for i, (c, ss, nm) in enumerate([
    (FLOW, "solid", "synchronous call / data flow"),
    (SSEC, "solid", "response streamed back to the client"),
    (RAG[0], "solid", "retrieval + generation path"),
    (GAT[0], "solid", "must pass a gate to continue"),
    (DAT[0], "dashed", "write-behind / read from a store"),
    (ING[0], "dashed", "asynchronous job")]):
    arrow("lg_ar%d" % i, [(LX + 32, y + 11), (LX + 96, y + 11)], stroke=c, sw=2.4, ss=ss)
    text("lg_at%d" % i, LX + 112, y + 2, nm, size=14, color="#343a40")
    y += 32

y += 18
text("lg_c", LX + 28, y, "OFF-PAGE CONNECTORS", size=15, color=BL, bold=True); y += 10
text("lg_cs", LX + 28, y + 16,
     "A letter names a store or one end of a hop, and appears at\nevery place that touches it — so no line has to cross the\ndiagram to show the link.",
     size=13, color="#868e96"); y += 80
for i, (ltr, nm, (sc, bg)) in enumerate([
    ("P", "SQLite — written by the API, by the tail, and by\n      ingestion; read to rebuild a thread", DAT),
    ("Q", "Qdrant — written at ingestion 6, queried by every\n      step badged  Q →", DAT),
    ("B", "Encrypted blob store — written at ingestion 1", DAT),
    ("T", "Parsed-text + span store — written at ingestion 3,\n      read on a citation click", DAT),
    ("D", "Documents API → ingestion queue", ING),
    ("E", "SSE events → chat pane (lane 1)", FE),
    ("L", "Any node badged  LLM call  reaches the provider", EXT)]):
    ellipse("lg_ce%d" % i, LX + 30, y, 34, 34, stroke=sc, bg=bg)
    text("lg_cl%d" % i, LX + 47, y + 7, ltr, size=16, color=sc, align="center", bold=True)
    text("lg_cn%d" % i, LX + 78, y + 7, nm, size=13.5, color="#343a40")
    y += 44 + 18 * nm.count("\n")

y += 20
text("lg_b", LX + 28, y, "BADGES", size=15, color=BL, bold=True)
text("lg_bs", LX + 28, y + 28,
     "The small chip at the bottom-right of a box is the requirement\n"
     "it implements, traceable to docs/LegalLens-BRD-PRD-FRD.md —\n"
     "FR = functional, NFR = non-functional, DR = data, TS = trust\n& safety, BR = business objective.",
     size=13.5, color="#343a40")

y += 132
rect("lg_n", LX + 24, y, LW - 48, 150, stroke=GAT[0], bg=GAT[1], sw=2)
text("lg_nh", LX + 42, y + 14, "THE LOAD-BEARING CLAIM", size=14, color=GAT[0], bold=True)
text("lg_nb", LX + 42, y + 44,
     "Lane 5 (1) is a release gate, not a quality check. An output\n"
     "carrying a citation that does not resolve to a span retrieved\n"
     "on this turn is never shown — it is stripped or the whole\n"
     "output is refused. Everything upstream exists to make that\n"
     "gate cheap to pass.", size=13, color="#343a40")

LGBOX["height"] = (y + 150 + 28) - LY

write(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "legallens-technical-flow.excalidraw"))
