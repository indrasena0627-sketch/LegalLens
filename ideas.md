# Legal Lens — Idea Notes

**Status:** collected thoughts, pre-BRD
**Date:** 2026-09-29
**Next artifact:** BRD (functional + non-functional specs) → then technical architecture

**How to read this file**

- **[DECIDED]** — settled, carry into the BRD as-is.
- **[SUGGESTION]** — Claude's proposal, needs my yes/no.
- **[OPEN]** — deliberately unanswered, to be resolved at BRD or architecture time.
- **[DEFERRED]** — technical nuance I do not want to discuss yet. Not a gap.

---

## 1. What Legal Lens is

Legal Lens is an AI application for practising attorneys. A lawyer uploads their own legal documents — contracts, judicial opinions, pleadings, discovery — and then does three things with them: **asks questions**, **gets structured summaries**, and **generates first-draft work product** such as a legal memo or case brief. Every answer points back to the exact place in the document it came from.

**One line:** *Legal Lens turns a lawyer's own document set into something they can question, summarise and draft from — with a citation behind every sentence.*

It is not a general legal chatbot. It is a grounded reading and drafting assistant over documents the attorney already has.

---

## 2. The problem, and why this shape of product

Attorney time disproportionately goes to three low-leverage activities:

1. **Locating something.** "Where does this 200-page master services agreement address assignment on change of control?" This is a search problem that keyword search handles badly, because the clause may never use the word "assignment".
2. **First-pass reading.** Getting the shape of an unfamiliar contract or opinion before deciding whether it matters.
3. **The blank page.** The first draft of a memo or case brief, which is mostly structural and derivable from documents already in hand.

A general-purpose chatbot fails at all three for one reason: **it will confidently make things up, and in law a fabrication is a sanctionable event, not an inconvenience.** That single fact drives the whole architecture — retrieval-grounded, citation-first, willing to say "not in your documents."

---

## 3. Who it is for

**[DECIDED] v1 persona:** a single US attorney — solo practitioner or small-firm lawyer — working their own document set in one personal workspace. No roles, no shared matters, no firm hierarchy.

**Secondary read:** a paralegal doing first-pass document review and producing a summary for the attorney.

**[DECIDED] Jurisdiction: United States.** This is not cosmetic — it fixes citation style (Bluebook), memo and case-brief conventions, the ethics frame (ABA Model Rules), and the privacy regime.

**[DECIDED] Not in v1:** firm multi-tenancy, partner/associate/paralegal roles, per-matter access control, client-facing portal. Phase-2 material.

---

## 4. The three features

### 4.1 Ask

**Intent:** "Answer my question using the documents I gave you."

**[DECIDED] Retrieval scope: uploaded documents only.** No curated corpus of statutes or case law in v1. Every answer is grounded in what the attorney uploaded. This avoids a large data-licensing and freshness problem and keeps the trust story simple: *if it is not in your documents, Legal Lens does not know it.*

| | |
|---|---|
| **Input** | Natural-language question + a document scope (one document, or the whole workspace) |
| **Output** | Answer with inline citations, each resolving to document + page/clause, plus the retrieved excerpts shown alongside |
| **Acceptance** | Every factual claim carries a citation that resolves to real retrieved text; when the documents do not contain the answer, the system says so instead of answering |

**"Not found" is a feature, not a failure.** A refusal that is correct is a successful response and should be measured as one. This needs to be visible in the UI as a legitimate outcome — not an error state.

### 4.2 Summary

**[SUGGESTION] "Summarise this document" is not one feature — it is three.** A contract summary and a case-opinion summary have almost nothing structurally in common, and a single generic prompt produces something useful for neither. I propose **structured summary templates driven by detected document type**:

**Contract / agreement**
- Parties and roles
- Effective date, term, renewal
- Core obligations per party
- Payment / consideration
- Termination rights and notice periods
- Limitation of liability and indemnity
- Assignment and change of control
- Governing law and dispute resolution
- Anything unusual or off-market, flagged

**Judicial opinion / case**
- Procedural posture
- Facts
- Issue(s) presented
- Holding
- Reasoning
- Disposition
- Notable concurrences / dissents

**Pleading / filing**
- Court, parties, cause of action
- Relief sought
- Key factual allegations
- Legal theories asserted
- Deadlines and dates appearing in the document

| | |
|---|---|
| **Input** | A document + optionally an override of the detected type |
| **Output** | Structured summary against the template, each field citing its source location; fields genuinely absent are marked "not addressed in this document" rather than filled by inference |
| **Acceptance** | No field is populated from model knowledge; a reviewer can verify every field against the cited span in under a minute |

The template approach also gives something evaluable: field-level precision, rather than a vague judgment about whether a paragraph of prose was "good".

### 4.3 Draft

**Intent:** "Give me a first draft I can edit, not a finished document I have to trust."

**[DECIDED] v1 draft types:** legal memo, case brief. **[OPEN]** whether to add demand letter, clause redline language, or deposition outline in v1.

| | |
|---|---|
| **Input** | Draft type + attorney-supplied parameters (question presented, audience, position to argue, tone) + selected source documents |
| **Output** | Structured draft (e.g. memo: Question Presented → Short Answer → Statement of Facts → Discussion → Conclusion), each factual assertion cited to a source document, visibly marked as an AI draft requiring attorney review |
| **Acceptance** | Zero citations that do not exist in the supplied documents; the draft's structure matches the convention for its type; the attorney can edit rather than rewrite |

**Two hard constraints on Draft:**

1. **It must never invent a citation.** Draft may assemble and restate facts drawn from retrieved documents; it may not produce a case cite, statute cite or docket number that does not appear in those documents. I want an explicit verification pass that strips or refuses any citation absent from the source set.
2. **It must never masquerade as final work product.** Persistent visual marking in the UI, and in any exported file, that this is an unreviewed AI draft and the attorney remains responsible for it.

---

## 5. Explicitly not in v1

Writing these down so they do not creep in:

- **Compare / redline** two versions of a contract. Genuinely useful, genuinely a separate feature. Later.
- **General legal research** over statutes, regulations and case law. This is the curated-corpus problem I decided against for v1.
- E-filing, docketing, calendaring, court-deadline computation.
- Billing, time capture, matter management.
- Client-facing access of any kind.
- **Anything resembling legal advice to a non-lawyer.** Legal Lens is a tool for licensed attorneys. This is both an ethics line (unauthorised practice) and a product-positioning line.

---

## 6. How I want to build it — three phases

**[DECIDED] Phase order: frontend → backend → AI layer.**

**Phase 1 — Frontend.** Take input from the lawyer. Document upload (drag-drop, multi-file), a document library view, a prompt/search bar, mode selection across Ask / Summary / Draft, streaming answer display with inline citations that click through to the source span, and feedback capture (thumbs up/down + reason) on every response.

**Phase 2 — Backend.** Python + FastAPI. Upload handling and storage, document parsing and text extraction, session/conversation state, the three endpoints (`/ask`, `/summarize`, `/draft`), streaming responses, error states the user can act on.

**Phase 3 — AI layer.** RAG. Ingestion → chunking → embedding → index → retrieve → assemble context → generate with citations → verify citations.

> **[SUGGESTION] One patch to this order.** Building the frontend first means Phase 1 has no backend to talk to. Rather than change the phase order, **write the API contract first** — define the OpenAPI schema for the three endpoints on day one, then stub FastAPI to return canned, realistic responses (including a canned "not found" and a canned error). Phase 1 develops against the stub and is never blocked; Phase 3 slots in behind an interface that already exists and has a consumer. Cost: about a day. Benefit: no integration cliff at the end, and the frontend's citation-rendering and streaming work gets exercised before any AI exists.

> **[SUGGESTION] Also consider a thin vertical slice first:** upload one PDF → ask one question → get one cited answer, crossing all three layers, before broadening any single layer. It de-risks the integration and produces a demoable thing early. The phased plan then becomes "widen each layer" rather than "hope the layers meet."

---

## 7. Stack

**[DECIDED]**

| Layer | Choice | Note |
|---|---|---|
| Frontend | **React + Vite + TypeScript** | I had no preference between Angular and React; React chosen for the streaming-UI and citation-rendering ecosystem |
| Backend | **Python + FastAPI** | |
| Packaging / dependencies | **uv** | Both package management and dependency resolution |
| Schemas | **Pydantic** | Request/response models, shared with the OpenAPI contract |
| Streaming | **SSE** | Token-by-token answers; matters more for perceived latency than actual latency |

**[SUGGESTION] Keep the AI layer behind a narrow service interface** — three functions, `answer()`, `summarize()`, `draft()`, each taking a request model and returning a response model with citations attached. The backend calls only these. The consequence: when this becomes a multi-agent system later, the swap happens entirely behind that interface and touches neither the frontend nor the API contract. This is the single highest-value structural decision available at this stage, and it costs nothing to make now.

**[DEFERRED — do not resolve here]** Vector database, embedding model, chunking strategy, retrieval topology (naive / hybrid / re-ranked / parent-document), reranker choice, LLM selection, prompt structure. All of this belongs in the technical architecture document, after the BRD.

---

## 8. Trust, safety and ethics — the non-negotiable section

This is the part that separates a legal AI product from a demo. It belongs in the BRD as requirements, not as aspirations.

### 8.1 Grounding and fabrication

Fabricated citations in legal filings have produced real judicial sanctions — *Mata v. Avianca, Inc.* (S.D.N.Y. 2023) is the canonical example, where counsel submitted a brief containing non-existent cases generated by an LLM and faced Rule 11 sanctions. Since then, courts have issued standing orders on AI-assisted filings.

Requirements that follow:

- Every factual claim in every output traceable to a retrieved span.
- A **citation verification pass** that checks each emitted citation against the source document set and refuses or strips any citation it cannot resolve.
- "Not answerable from your documents" available as a first-class output from all three features.
- Retrieved excerpts always viewable next to the answer, so verification takes seconds.

### 8.2 Confidentiality and privilege

Client documents are confidential (ABA Model Rule 1.6) and often privileged. The duty of technological competence (Model Rule 1.1, comment 8) means the attorney is responsible for understanding where their client's data goes.

Requirements that follow:

- **Zero-retention terms with whatever LLM provider is used**, and no training on client data. This needs to be a stated, verifiable property, not an assumption.
- Encryption at rest for uploaded documents; TLS in transit.
- **Delete-on-demand**, document-level and workspace-level, that actually removes the document, its extracted text, and its embeddings from the index.
- **Audit log of every retrieval and every generation** — which document, which spans, which prompt, which model version, what output. This serves the ethics obligation and simultaneously gives answer reproducibility.

### 8.3 Prompt injection through documents

An uploaded document is **untrusted input**. Opposing counsel's filing, a PDF from a third party, or a scanned exhibit can contain text crafted to hijack the model's instructions. Retrieved document text must be treated as *data to reason about*, never as *instructions to follow*.

Requirements that follow: clear separation of system instructions from retrieved content in the assembled context; no tool invocation driven by document content; output filtering for instruction-like content leaking into answers.

### 8.4 Scope and disclaimers

- Legal Lens produces attorney work product aids, not legal advice.
- The attorney is responsible for all output. Every draft carries that statement.
- No use by non-lawyers as a substitute for counsel.

---

## 9. Non-functional themes to firm up in the BRD

Naming them now so the BRD has a checklist; the actual numbers need to be decided there.

- **Latency budget** — split into time-to-first-token (perceived) and time-to-complete-answer. Summarising a 200-page contract is a different budget from answering a question.
- **Document limits** — max pages, max file size, max documents per workspace, supported formats.
- **Throughput** — concurrent uploads, concurrent queries, ingestion time per page.
- **Cost per query** and cost per document ingested, with a stated target.
- **Availability** and graceful degradation — what the app does when the LLM provider is down or rate-limited.
- **Observability** — tracing every request through retrieval → context assembly → generation, with cost attribution.
- **Data retention** — how long documents live, what deletion guarantees exist.
- **Accessibility** — keyboard navigation, screen-reader support for the citation UI.

---

## 10. Success metrics (first cut)

Quality, not just latency. These are the inputs to the evaluation dashboard later.

| Metric | Why it matters |
|---|---|
| **Groundedness / faithfulness rate** | % of claims supported by cited spans. The headline number. |
| **Citation precision** | % of emitted citations that resolve to real source text. Target: 100%, treated as a gate. |
| **Retrieval recall@k** | Measured on a labelled query set, independently of the LLM — far cheaper to fix in retrieval than in generation. |
| **Correct-refusal rate** | Does it say "not in your documents" when that is true? |
| **False-refusal rate** | Does it refuse when the answer *was* retrievable? The failure mode that kills usefulness. |
| **Draft acceptance rate** | % of drafts the attorney keeps with only minor edits. The real product metric. |
| **p95 latency** (first token, full answer) | |
| **Cost per query** | |

---

## 11. Risks and open questions

### Top technical risk: the documents themselves

**Real legal PDFs are hostile.** Scanned faxes of signed agreements, exhibit stamps over body text, two-column opinions, dense footnotes carrying substantive content, tables of payment schedules, tracked-changes artifacts, handwritten margin notes. OCR quality and layout-aware parsing will be the single largest hidden cost in this build — larger than the RAG pipeline itself. A clause extracted from a mis-ordered two-column page is worse than no extraction, because it looks correct.

This needs to be a named risk in the BRD with a mitigation, not a Phase-3 surprise.

### Other risks

- **No labelled evaluation set exists yet.** Without one, every retrieval improvement is a guess. Building it is real work and needs to be scheduled, not assumed.
- **Long documents vs. context limits** — a 300-page agreement will not fit in context; summary quality depends on how well the pipeline composes partial summaries.
- **State-level variation** in memo and filing conventions within the US.
- **Trust is asymmetric** — one confidently wrong cited answer costs more credibility than fifty correct ones earn.

### [OPEN] — answer these at BRD time

1. **Document volume and size** — typical documents per matter, typical page count? Drives ingestion architecture and cost model.
2. **Default Ask scope** — does a question search the whole workspace, or one selected document? Whole-workspace is more useful and much harder to keep precise.
3. **Firm-specific templates** — does Draft need to match a house style / firm template, or are standard conventions enough for v1?
4. **Retention policy** — are documents persisted indefinitely in the workspace, or is a session ephemeral? Directly affects the confidentiality posture and the storage design.
5. **Evaluation data** — can a labelled question/answer set be produced from real documents, or does it need to be synthesised?
6. **Hosted LLM API vs. self-hosted** — given the confidentiality requirements, is a hosted API acceptable with zero-retention terms, or does the posture require local inference? This one has large cost and quality consequences and should be decided before the architecture doc.
7. **Export formats** — does a draft need to come out as .docx to be useful, or is copy-to-clipboard enough for v1?

---

## 12. Later, not now

- **Multi-agent upgrade.** The natural decomposition: a *researcher* agent that retrieves, a *drafter* that composes, a *citation checker* that verifies every cite against sources, and a *reviewer* that critiques the draft against the attorney's stated position. This is where Legal Lens becomes more than RAG — but only after the RAG version is measured and working.
- Compare & redline across contract versions.
- Matters, multi-user, role-based access.
- Integrations: document management systems, email, calendar.
- A curated legal research corpus, if the licensing story can be solved.

---

## 13. Capstone mapping (Batch B7)

Legal Lens doubles as the spine for **Capstone I — Production RAG System (Days 24–32)**, with the multi-agent upgrade as **Capstone II (Days 52–57)**. The phases above line up with the existing curriculum almost exactly:

| Class | Curriculum deliverable | Legal Lens artifact |
|---|---|---|
| 24 | One-page product spec with measurable success criteria | **The BRD** — sections 3, 4, 5, 10 of this file |
| 25 | Architecture diagram + threat model | Technical architecture doc + section 8.3 (injection via documents) |
| 26 | Re-runnable ingestion pipeline over the real corpus | Phase 3 ingestion — where the PDF-parsing risk (§11) gets confronted |
| 27 | Working query → grounded answer path with citations | **Ask**, end to end |
| 28 | Deployed local app with streaming and inline citations | Phase 1 + Phase 2 integrated; SSE streaming, citation click-through |
| 29 | Green CI with an eval gate that can fail the build | Citation precision as a hard gate |
| 30 | Staging deployment with demonstrated rollback | Prompt and index versioning |
| 31 | Live evaluation dashboard over real traffic | Section 10 metrics |
| 32 | Governance note + cost model | Section 8.2 audit log, retention, cost per query |
| 52–57 | Production multi-agent system | Section 12 — researcher / drafter / citation-checker / reviewer |

Existing teaching assets that prefigure the AI layer: `Classes/Langchain/class 4 rag.ipynb`, `class 5 agents.ipynb`, and the working Chroma index in `Classes/Langchain/chroma_techmart/`.

---

## 14. Next artifact — BRD table of contents

1. Document control, purpose, intended audience
2. Business context and problem statement
3. Scope — in scope / out of scope / non-goals
4. Personas and user journeys
5. User stories with acceptance criteria, per feature (Ask, Summary, Draft)
6. Functional requirements (numbered, testable, traceable to user stories)
7. Non-functional requirements — performance, security, privacy, availability, observability, accessibility
8. Data requirements — document types, volumes, retention, deletion, PII handling
9. Trust & safety requirements — grounding, citation verification, refusal behaviour, injection resistance, disclaimers
10. Assumptions and dependencies
11. Success metrics and acceptance thresholds
12. Risks and mitigations
13. Phased delivery milestones
14. Open questions and decision log

Then: **technical architecture document** — where the deferred items from §7 get decided.
