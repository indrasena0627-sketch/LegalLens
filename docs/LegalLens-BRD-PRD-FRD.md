# Legal Lens — Business, Product & Functional Requirements

**v1.0 draft** · 2026-09-30 · predecessor `ideas.md` · successor *Technical Architecture & Threat Model* · terms defined in `LegalLens-Glossary.docx`

Three labelled layers. **Part A** — why this should exist and how we know it worked. **Part B** — what the user experiences. **Part C** — what must be built and verified, as numbered testable requirements, tracing back through Part B stories to Part A objectives. Implementation choices are deliberately absent; §16 lists them as explicit deferrals, not omissions.

# Part A — Business

## 1. Problem

Attorney time goes disproportionately to three low-leverage activities: **locating something** ("where does this 200-page agreement address assignment on change of control?" — which keyword search handles badly, because the clause may never use the word *assignment*), **first-pass reading** to learn the shape of an unfamiliar contract or opinion, and **the blank page**, a first draft that is mostly structural and derivable from documents already in hand.

A general-purpose chatbot fails at all three for one reason: it will confidently fabricate, and in law a fabrication is a sanctionable event rather than an inconvenience. In *Mata v. Avianca, Inc.* (S.D.N.Y. 2023) counsel filed a brief containing non-existent cases produced by an LLM and faced Rule 11 sanctions; courts have since issued standing orders on AI-assisted filings. That fact drives the product's shape — retrieval-grounded, citation-first, willing to say *not in your documents*. **Legal Lens turns an attorney's own document set into something they can question, summarise and draft from, with a citation behind every sentence:** not a general legal chatbot, but a grounded reading and drafting assistant over documents the attorney already holds.

## 2. Business objectives

| | Objective | Measured by |
|---|---|---|
| **BR-1** | Cut time to locate a provision or holding in a long document | Time-to-answer vs. manual baseline, fixed task set |
| **BR-2** | Cut time to first-pass comprehension of a document | Time to a reviewed structured summary |
| **BR-3** | Cut time to a usable first draft of a memo or case brief | Draft acceptance rate (§5) |
| **BR-4** | Make every output verifiable in seconds, so trust is earned | Citation precision, groundedness (§5) |
| **BR-5** | Keep the product defensible under the attorney's ethical duties | Zero unresolvable citations shipped; audit-log completeness |

**BR-4 and BR-5 are gates, not goals.** Missing BR-1 to BR-3 is disappointing. Missing BR-4 or BR-5 is unshippable: one confidently wrong cited answer costs more credibility than fifty correct ones earn.

## 3. Scope

| In scope (v1) | Out of scope (v1) |
|---|---|
| Three features: Ask, Summary, Draft | Compare / redline across contract versions |
| Attorney-uploaded documents as the sole corpus | General research over statutes, regulations, case law |
| One personal workspace, one user | Multi-tenancy, roles, per-matter access control |
| US conventions (Bluebook, ABA Model Rules) | Non-US jurisdictions; state-specific filing conventions |
| Draft types: legal memo, case brief | Demand letters, clause redlines, deposition outlines |
| Markdown and clipboard export | `.docx`, e-filing, docketing, calendaring, billing |
| | Matter management; client-facing access of any kind |

**Two exclusions are decisions, not shortfalls.** Legal Lens produces work-product aids, never legal advice, and is not for non-lawyers to use as a substitute for counsel — an ethics line (unauthorised practice) and a positioning line at once. And retrieval over uploaded documents *only* sidesteps a large data-licensing and freshness problem while making the trust claim falsifiable in one sentence: *if it is not in your documents, Legal Lens does not know it.*

## 4. Users

**Primary — Dana, solo or small-firm US attorney.** Works her own documents in one workspace; technically competent, not technical. Will abandon the tool permanently the first time it cites something that does not exist, and needs verification to cost seconds, not minutes — otherwise the time saved is cancelled by the time spent checking. **Secondary — Marcus, paralegal**, doing first-pass review and producing summaries for an attorney: heavy on Summary, light on Draft, same workspace and same permissions, since v1 has no role model.

## 5. Success metrics

| Metric | Target | | Metric | Target |
|---|---|---|---|---|
| **Citation precision** | **100% — build gate** | | **False-refusal rate** | ≤ 10% |
| **Groundedness** | ≥ 95% | | **Draft acceptance rate** | ≥ 60% |
| **Retrieval recall@k** | ≥ 85% | | **p95 latency** | NFR-1 |
| **Correct-refusal rate** | ≥ 90% | | **Cost per query** | NFR-8 |

Citation precision — the share of emitted citations resolving to real source text — is a release gate, not a target. Recall@k is measured without the LLM, because retrieval failures cannot be fixed by better generation; and the refusal pair matters both ways, since a correct refusal is a success while a false one is the failure mode that kills usefulness.

# Part B — Product

## 6. Product principles

**Grounded or silent** — every claim traces to retrieved text, or the system declines. **Refusal is a first-class success** — "not answerable from your documents" renders as a legitimate outcome, never an error state, and counts as a success when correct. **Verification in seconds** — retrieved excerpts sit beside the answer, and a citation click highlights its source span. **A draft is visibly a draft** — persistent marking, in the UI and in every export, that this is unreviewed AI output for which the attorney remains responsible.

## 7. System context

```
┌──────────────────────────────────────────────────────────────┐
│ FRONTEND React+Vite+TS · upload · library · prompt bar       │
│ Ask│Summary│Draft · streamed answer · citations · excerpts   │
└───────────────┬──────────── HTTPS · OpenAPI · SSE ───────────┘
┌───────────────▼──────────────────────────────────────────────┐
│ BACKEND FastAPI · /documents /ask /summarize /draft /feedback │
│ auth · Pydantic · session state · audit log                  │
└────┬──────────────────────────┬──────────────────────────────┘
     │ encrypted store          │ answer() summarize() draft()
┌────▼───────────────┐ ┌────────▼─────────────────────────────┐
│ files · text+spans │◄►│ AI LAYER (RAG) parse→chunk→embed→   │
│ chunks · vectors   │ │ index→retrieve→assemble→generate→    │
│ metadata · audit   │ │ VERIFY CITATIONS ─► LLM (0-retention)│
└────────────────────┘ └──────────────────────────────────────┘
```

The AI layer is reachable only through `answer()`, `summarize()` and `draft()`, each taking a request model and returning a response model with citations attached. The backend calls nothing else. **Consequence:** when this later becomes a multi-agent system, the change happens behind that interface and touches neither the frontend nor the API contract.

## 8. User stories

Acceptance criteria live in §11, where each requirement traces back here. As Dana (or Marcus) I want to… **US-1** upload several documents at once without per-file ceremony · **US-2** see what is in my workspace and whether it is ready to query · **US-3** ask a question in natural language and get a cited answer I can verify at a glance · **US-4** know when the answer is simply not in my documents · **US-5** control whether a question searches one document or everything · **US-6** get a structured summary matching the kind of document it is *(Marcus)* · **US-7** get a first draft I can edit rather than one I must trust · **US-8** supply the position a draft argues from · **US-9** delete a document and know it is actually gone · **US-10** tell the system when an answer was wrong.

## 9. Why Summary is three features, not one

A contract summary and a case-opinion summary share almost no structure, and one generic prompt serves neither — so Summary is template-driven off the detected document type. **Contract:** parties and roles · effective date, term, renewal · obligations per party · payment · termination rights and notice periods · limitation of liability and indemnity · assignment and change of control · governing law and dispute resolution · anything off-market, flagged. **Judicial opinion:** procedural posture · facts · issues presented · holding · reasoning · disposition · notable concurrences and dissents. **Pleading:** court, parties, cause of action · relief sought · key factual allegations · legal theories asserted · dates and deadlines appearing in the document. The template is also what makes Summary measurable: field-level precision, instead of a vague judgment about whether a paragraph of prose was good.

## 10. Delivery milestones

Phase order is frontend → backend → AI layer. **M0 is what makes that order safe:** the frontend's citation and streaming work gets exercised before any AI exists, and the AI layer later slots in behind an interface that already has a consumer.

**M0 API contract first** — OpenAPI schema for the five endpoints; FastAPI stub returning realistic canned responses, including a canned refusal and a canned error. · **M1 Thin vertical slice** — one PDF → one question → one cited answer across all three layers, de-risking integration before any layer widens. · **M2 Frontend** — upload, library, prompt bar, modes, streaming, citation click-through, feedback, against the stub. · **M3 Backend** — real upload, storage, parsing, session state, five endpoints, SSE, actionable errors. · **M4 AI layer** — full RAG path with citation verification; all three features live. · **M5 Eval gate in CI** — labelled set in place; citation precision below 100% fails the build. · **M6 Staging** — deployed with demonstrated rollback; prompt and index versions pinned and recorded.

# Part C — Functional & Non-Functional Requirements

## 11. Functional requirements

Trailing code is the story served.

*Documents and library* — **FR-1** Accept PDF, DOCX, TXT via multi-file drag-drop and file picker. `US-1` · **FR-2** Reject files over 50 MB or 500 pages, naming the limit and the actual value. `US-1` · **FR-3** Report per-file status (queued, parsing, indexing, ready, failed); one failure must not fail the batch. `US-1` · **FR-4** Extract text with page and position metadata sufficient to resolve a citation to a page and, for contracts, a clause. `US-3` · **FR-5** Classify each document as contract, opinion, pleading or other; show it and allow override. `US-6` · **FR-6** List the library with name, type, pages, status, upload date, filterable and sortable. `US-2` · **FR-7** Exclude a document from all retrieval until its status is `ready`. `US-2`

*Ask* — **FR-8** Accept a question scoped to one document, a subset, or the whole workspace. `US-5` · **FR-9** Default scope to workspace-wide, narrowing to the open document when one is selected, and state the scope used on the response. `US-5` · **FR-10** Stream answers token-by-token over SSE. `US-3` · **FR-11** Attach to every answer a citation list, each entry resolving to document ID, page and character span. `US-3` · **FR-12** Display retrieved excerpts alongside the answer with no further user action. `US-3` · **FR-13** On citation click, open the source document and scroll to and highlight the cited span. `US-3` · **FR-14** Return a structured refusal — distinct in type from an error — when retrieval yields no sufficient support, naming the scope searched. `US-4`

*Summary and Draft* — **FR-15** Generate summaries against the template for the document's type (§9). `US-6` · **FR-16** Cite every populated field to a source span; mark unsupported fields "not addressed in this document"; never populate a field by inference. `US-6` · **FR-17** Summarise documents exceeding the context window by composition, without silent truncation, stating what was covered. `US-6` · **FR-18** Support legal memo (Question Presented → Short Answer → Statement of Facts → Discussion → Conclusion) and case brief, each in its conventional structure. `US-7` · **FR-19** Accept draft parameters: question presented, audience, position to argue, tone, source selection. `US-8` · **FR-20** Cite every factual assertion in a draft to a source document. `US-7` · **FR-21** Run a citation verification pass over every output; strip the citation, or refuse the output, when a citation cannot be resolved to the supplied sources. `US-7, BR-5` · **FR-22** Never emit a case cite, statute cite or docket number absent from the sources — including ones the model "knows". `US-7, BR-5` · **FR-23** Mark drafts as unreviewed AI output in the UI and in every export. `US-7` · **FR-24** Export any output as Markdown and to clipboard, carrying that marking. `US-7`

*Platform* — **FR-25** Capture thumbs up/down plus optional reason on every response, linked to its request and retrieval trace. `US-10` · **FR-26** Hard-delete at document and workspace level — file, extracted text, chunks, embeddings — effective immediately for retrieval. `US-9, BR-5` · **FR-27** Authenticate one user by email and password with server-side sessions; no roles in v1. `BR-5` · **FR-28** Surface actionable error states for LLM unavailability, rate limiting, parse failure and timeout, each naming a next action. `BR-4`

## 12. Non-functional requirements

**Performance** — **NFR-1** p95 time-to-first-token ≤ 2 s; p95 complete answer ≤ 15 s. · **NFR-2** Ingestion ≤ 30 s per 50 pages of machine-readable PDF. · **NFR-3** Summary of a 200-page document ≤ 3 min. **Scale** — **NFR-4** 50 documents per workspace; 500 pages and 50 MB per file. · **NFR-5** 10 concurrent users and 3 concurrent ingestions without breaching NFR-1. **Availability** — **NFR-6** When the LLM provider is down or rate-limited, retrieval and excerpt display keep working and generation fails with a stated reason and a retry. · **NFR-7** No partial output is presented as complete; an interrupted stream is marked incomplete. **Cost** — **NFR-8** ≤ $0.05 per Ask and ≤ $0.50 per document ingested, attributed per request and visible in observability.

**Security and privacy** — **NFR-9** TLS in transit; encryption at rest for files, extracted text and embeddings. · **NFR-10** The LLM provider operates under zero-retention terms with no training on submitted content — a stated, verifiable property of the deployment, recorded in the governance note. **Observability** — **NFR-11** Every request traced retrieval → context assembly → generation, with latency and cost per stage. · **NFR-12** Prompt, model and index versions recorded on every generation, making any answer reproducible. **Accessibility** — **NFR-13** Keyboard navigation throughout; citations and excerpt panes operable and announced by screen readers; WCAG 2.1 AA contrast. **Maintainability and test** — **NFR-14** The AI layer is reachable only via `answer()`, `summarize()`, `draft()`; the backend holds no retrieval or prompt logic. · **NFR-15** Evaluation runs in CI against a labelled set; citation precision below 100% fails the build.

## 13. Data requirements

**DR-1** Formats: PDF (machine-readable and scanned), DOCX, TXT. Scanned PDFs are OCR'd; OCR confidence is recorded and low-confidence pages flagged in the UI. · **DR-2** Documents persist until explicitly deleted; no automatic expiry in v1. · **DR-3** Stored per document: file, extracted text with position metadata, chunks, embeddings, classification, ingestion log. · **DR-4** Audit log of every retrieval and generation: document IDs, retrieved spans, prompt, model version, output, timestamp, user. · **DR-5** All uploads are assumed to carry client confidences and privileged material; no document content reaches third-party telemetry, error trackers or analytics, and the evaluation set is built only from public-domain sources — published opinions, publicly filed agreements — never client documents.

## 14. Trust and safety requirements

These follow from the attorney's own obligations — confidentiality (ABA Model Rule 1.6), technological competence (Rule 1.1 cmt. 8), candour to the tribunal — and are requirements, not aspirations.


**TS-1** Every factual claim in every output is traceable to a retrieved span, and retrieved excerpts are always viewable beside the output, so verification costs seconds. · **TS-2** Citation verification (FR-21) gates every output; shipping an unresolvable citation is a release-blocking defect. · **TS-3** "Not answerable from your documents" is a first-class output of all three features. · **TS-4** Uploaded documents are **untrusted input**: system instructions are structurally separated from retrieved content in the assembled context, no tool invocation may be driven by document content, and output is filtered for instruction-like content leaking from documents. · **TS-5** Every output states that it is an attorney work-product aid, not legal advice, and that the attorney is responsible for it. · **TS-6** Deletion is real — FR-26 is verified by test, not asserted — and the data-handling posture (NFR-10) is documented in terms an attorney can rely on under Rule 1.1 cmt. 8.

## 15. Risks and mitigations

**Real legal PDFs are hostile** — scanned faxes, exhibit stamps over body text, two-column opinions, substantive footnotes, payment tables, tracked-changes artifacts. A clause pulled from a mis-ordered two-column page is *worse* than no extraction, because it looks correct. This is the highest risk in the build and probably its largest hidden cost, larger than the RAG pipeline itself. *Mitigated by* layout-aware parsing evaluated against a deliberately adversarial document set at M1 rather than M4, per-page OCR confidence surfaced (DR-1), and parse quality treated as a first-class metric.

**No labelled evaluation set exists yet**, so every retrieval change is a guess — *mitigated* by ~50 labelled Q/A pairs over public-domain documents, scheduled across M1–M5 rather than assumed (DR-5). **Long documents exceed context limits** and summary quality degrades silently — *mitigated* by FR-17. **Trust is asymmetric**: one wrong cited answer outweighs fifty right ones — *mitigated* by BR-4/BR-5 as gates and citation precision in CI (NFR-15). **Workspace-wide Ask loses precision as the corpus grows** — *mitigated* by stating scope on every answer (FR-9) and measuring recall@k independently of the LLM. **Prompt injection via uploaded documents** — *mitigated* by TS-4, with the full threat model in the architecture document.

## 16. Decisions, deferrals and open questions

**Decided here** — each an assumption made to keep requirements testable, each overturnable: Ask defaults to workspace scope · 50 documents, 500 pages, 50 MB per file · PDF, DOCX, TXT only · documents persist until explicit delete · Markdown and clipboard export, `.docx` deferred · single-user auth, no roles · drafts limited to memo and case brief · hosted LLM API under zero-retention terms rather than local inference · public-domain evaluation set · API contract before implementation (M0) · vertical slice before widening any layer (M1) · type-driven summary templates · AI layer behind a three-function interface.

**Deferred to the architecture document**, named so they read as decisions pending rather than gaps: vector database · embedding model · chunking strategy · retrieval topology (naive, hybrid, re-ranked, parent-document) · reranker · model selection · prompt structure and versioning · OCR engine · deployment topology and rollback mechanics.

**Still open.** (1) Does the evaluation set need adversarial-layout coverage separately from Q/A correctness, and who builds it? (2) Is `.docx` export required before the product is genuinely useful? (3) How is a *correct* refusal distinguished from a *false* one in CI without a human in the loop on every run? (4) Are OCR-low-confidence pages excluded from retrieval, or retrieved with a warning? (5) What is the retention posture for the audit log itself, given it quotes client content (DR-4)?
