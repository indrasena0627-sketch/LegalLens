# Legal Lens — Glossary

Companion to `LegalLens-BRD-PRD-FRD.docx`.

**RAG (retrieval-augmented generation)** — answering from text fetched from a document set at query time, rather than from the model's training weights. The reason Legal Lens can cite: the text it answers from is text it actually retrieved.

**Chunking** — splitting a document into passages small enough to retrieve precisely but large enough to stay meaningful. Where a chunk boundary falls decides whether a clause survives intact.

**Embedding** — a numeric representation of a passage that lets similar passages be found by meaning rather than by keyword. This is what lets a question about "assignment on change of control" match a clause that never uses the word *assignment*.

**Groundedness (faithfulness)** — the share of claims in an output actually supported by the source text cited for them. Measures whether the model stuck to its evidence.

**Citation precision** — the share of emitted citations that resolve to real source text. Distinct from groundedness: a citation can point at a real passage that does not support the claim. Legal Lens treats 100% as a release gate.

**Recall@k** — whether the correct passage appears among the top *k* retrieved results. Measured without the LLM, because a retrieval failure cannot be fixed by better generation.

**Correct vs. false refusal** — a correct refusal declines when the documents genuinely lack the answer, and counts as a success. A false refusal declines when the answer *was* retrievable, and is the failure mode that makes a grounded system useless.

**TTFT (time to first token)** — the delay before the first word of an answer appears. Governs perceived speed far more than total completion time does, which is why streaming matters.

**SSE (server-sent events)** — one-way HTTP streaming from server to browser, used here to deliver answers token-by-token.

**Prompt injection** — text inside an untrusted input crafted to be read as instructions rather than as content. An uploaded PDF from opposing counsel is untrusted input.

**Bluebook** — the standard US legal citation style; it fixes how cites are formatted in memos and briefs.

**Work product** — material an attorney prepares for a matter. Legal Lens produces aids to work product, never the finished thing, which is why every draft carries a review marking.
