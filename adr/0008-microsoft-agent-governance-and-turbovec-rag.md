# ADR 0008: Adoption of Microsoft Agent Governance Principles and In-Process Turbovec RAG

* Status: accepted
* Deciders: AI Systems Architect, Repository Maintainer
* Date: 2026-10-23

## Context and Problem Statement
The SPARK PA daemon ingests untrusted text, audio notes, and document OCR from semi-public university Telegram groups. Malicious or adversarial students can attempt prompt injection, social engineering, or privilege escalation to cause unauthorized mutations in downstream systems (Google Calendar, Tasks, Sheets, and ERP). Furthermore, semantic search across student course materials, past announcements, and lab viva preparation was previously either stateless or dependent on external vector services, introducing latency and cloud token waste.

We need an architectural standard that enforces rigorous agentic governance, anti-prompt injection guardrails, zero-disclosure PII scrubbing, tiered human-in-the-loop (HITL) authorization, and low-latency semantic retrieval while adhering strictly to Ponytail Ultra minimalism (YAGNI, standard library first, zero heavy external framework baggage).

## Decision Drivers
* Enforce deterministic data vs instruction separation at trust boundaries.
* Eliminate unauthorized mutations via 3-tiered risk classification and cryptographic state validation.
* Maintain immutable, append-only forensic audit telemetry in SQLite.
* Deliver sub-millisecond semantic search across academic notes and viva materials without external vector database daemons.
* Comply with the Universal Engineering Pipeline Standard v2.2.0 and Ponytail minimalism.

## Considered Options
* **Option 1 (Primary / Accepted): Native In-Process Implementation using Python Standard Library, SQLite, and Turbovec.**
  Extract core patterns from the Microsoft Agent Governance Toolkit natively using `re`, `hashlib`, `hmac`, `dataclasses`, and `sqlite3`. Utilize Google's TurboQuant algorithm via `turbovec.TurboQuantIndex(dim=3072, bit_width=4)` in `.venv` with persistent local disk synchronization (`data/intel_index.tv`).
* **Option 2: Microsoft Agent Governance Toolkit Python Package & Semantic Kernel.**
  Install the official Microsoft toolkit and Semantic Kernel packages from PyPI with Azure AI telemetry.
* **Option 3: External Vector Microservice (ChromaDB / Qdrant) with Celery Tasks.**
  Spin up a standalone vector database container and background task queue for RAG queries and quarantine processing.

## Decision Outcome
Accepted Option: **Option 1 (Native In-Process Implementation using Python Standard Library, SQLite, and Turbovec)**.

### Rationale & Comparison
* **Option 1:**
  - *Pros:* Zero external cloud or enterprise framework dependencies; pure stdlib and SQLite WAL persistence; sub-millisecond in-process 4-bit vector search; deterministic regex guardrails that prevent prompt injection before LLM invocation; cryptographic HMAC-SHA256 authorization tokens with 24h TTL; 100% compliant with Ponytail Ultra doctrine.
  - *Reversal Cost:* Low. Clean module boundaries under `src/governance/` and `src/knowledge/retriever.py`.
* **Option 2:**
  - *Choose when:* Enterprise Azure cloud deployment with managed IAM and Semantic Kernel pipelines is mandated.
  - *Excluded because:* Violates §0 invariants and Ponytail minimalism; introduces hundreds of transitive cloud dependencies and incompatible Python runtime constraints.
* **Option 3:**
  - *Choose when:* Multitenant cluster scaling with billions of vectors across distributed nodes is required.
  - *Excluded because:* Invariant 7 strictly prohibits Celery, Redis, or Postgres services in the PA daemon. Turbovec handles local embeddings with 15x memory compression directly in-process.

## Positive Consequences
* All incoming messages are sealed in a frozen `UntrustedInput` envelope with explicit trust tiering (`UNTRUSTED_COMMUNITY` vs `TRUSTED_OWNER`).
* Known prompt injection vectors are quarantined deterministically, alerting the owner via Telegram.
* Forensic audit trail (`governance_audit` table) records deterministic SHA-256 event IDs, raw fingerprints, policy verdicts, and rollback diffs for `/undo`.
* Academic queries (`/ask`) respond in microseconds using locally cached 4-bit quantized embeddings.
* Owner gains interactive quarantine management (`/quarantine`, `/quarantine_inspect`) and attendance bunk margin calculations (`/bunk`).

## Negative Consequences
* High-dimensional embeddings require ~5MB of disk cache for `data/intel_index.tv`.
* Extremely obscure benign messages containing injection keywords require manual inspection via the quarantine console.
