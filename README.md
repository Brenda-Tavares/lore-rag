# Lore

**Secure RAG for SRE knowledge.** A retrieval-augmented generation system that ingests
operational documents, strips sensitive data before storage, and answers questions with
cited sources.

[English](README.md) · [Português](README.pt-BR.md) · [简体中文](README.zh-CN.md)

Author: Brenda Tavares · Status: local MVP, not deployed · QA: manual (§9) · Updated: 2026-10-17

> Portfolio project. All keys live in a git-ignored `.env`; no secret is committed in this
> repository.

---

## 1. The Problem

Operational knowledge — runbooks, incident procedures, troubleshooting guides — lives in
scattered files and in people's heads. When an on-call engineer needs an answer during an
incident, search time is measured in minutes of downtime.

Generic tooling fails this workload for three reasons:

- **Keyword search fails on fuzzy recall.** The engineer remembers the symptom, not the
  exact command or section title.
- **Plain LLM answers are unauditable.** A model asked from memory can confabulate commands
  that do not exist in the institution's own runbooks, and nothing exposes that.
- **Operational documents contain secrets.** Credentials, tokens and hostnames appear in
  real runbooks. Uploading them to an external index, or pasting them into a chat UI, leaks
  them.

Lore addresses the three at once: semantic retrieval over the institution's own documents,
answers grounded in retrieved context and returned with citations, and sanitization of
sensitive data **before** anything is stored.

---

## 2. Design Rationale

Four constraints shaped the architecture:

- **Auditability over fluency.** An answer without a source is a liability in operations.
  Every response returns the exact chunks it was grounded on, and the UI renders them as
  citations. When retrieval finds nothing, the system states so instead of improvising.
- **Sanitization before persistence, not after.** Redaction runs inside the ingestion
  pipeline, before chunking and embedding. A secret that never enters the vector store
  cannot be retrieved, echoed or leaked by any later component.
- **Isolation by construction, not by convention.** Multi-tenancy is enforced as a
  mandatory filter on every vector query, not as an optional parameter a developer might
  forget. The current tenant is a fixed development identifier; authentication is roadmap
  (§10, §14).
- **Zero-infrastructure development, documented production path.** Qdrant runs in embedded
  (local path) mode so the MVP needs no extra service. The migration path to a Qdrant
  server and managed Postgres is documented (§13) rather than silently assumed.

---

## 3. The Solution

A two-pipeline system with a trilingual interface:

**Ingestion.** Upload → MIME allowlist validation → secret/PII redaction → sliding-window
chunking with overlap → embedding (OpenRouter, with on-disk cache, batching and exponential
backoff) → PostgreSQL (document and chunk metadata) + Qdrant (vectors with tenant payload).

**Retrieval.** Question → same embedding model → tenant-filtered vector search → top-5
chunks → prompt assembly (grounding instruction + context + question) → Groq LLM → answer
in Markdown plus cited sources.

**Interface.** A React SPA in PT-BR / EN / ZH-CN exposes upload and chat, renders Markdown
and citations, and never sees an API key.

---

## 4. Tech Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Frontend | React 18 + TypeScript, Vite, Tailwind CSS 3 (+ typography plugin), axios, react-markdown, lucide-react | Single-page tool UI; TypeScript for contract safety; Tailwind for a consistent design system without a component library |
| Backend | FastAPI (Python 3.11), Pydantic Settings v2 | Async API with typed validation; settings resolved from an explicit env file path |
| Relational | PostgreSQL, SQLAlchemy 2 (psycopg2) | Document and chunk metadata with relational integrity |
| Vector store | Qdrant, embedded local-path mode | Zero-infra development; payload filters enable mandatory tenant isolation; server mode documented for production |
| Embeddings | OpenRouter (`liquid/lfm-2.5-embedding-350m:free`) with disk cache, batching, backoff | Free tier with bounded spend; cache removes repeat calls; batching reduces request count |
| LLM | Groq (`openai/gpt-oss-120b`) | Low-latency inference for the chat path |
| i18n | Inline dictionaries (26 keys × 3 locales), React Context, localStorage | No library dependency; same zero-dependency approach used across the author's portfolio |

---

## 5. Architecture

```
INGESTION
browser ──multipart──▶ FastAPI ──▶ MIME allowlist ──▶ redaction ──▶ chunking
                                │
                                ▼
                    embedding (OpenRouter: cache / batch / backoff)
                                │
                   ┌────────────┴────────────┐
                   ▼                         ▼
            PostgreSQL                 Qdrant (embedded)
       documents, chunks           vectors + tenant payload

RETRIEVAL
browser ──query──▶ FastAPI ──▶ embed query ──▶ Qdrant search (tenant filter, top-5)
                                │
                                ▼
                   prompt = grounding instruction + chunks + query
                                │
                                ▼
                          Groq LLM ──▶ answer (Markdown) + sources
```

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/documents/upload` | Multipart ingestion with validation and redaction |
| `POST /api/v1/ai/chat` | Grounded answer with cited sources |
| `GET /health` | Liveness probe |
| `GET /docs` | OpenAPI / Swagger UI |

---

## 6. Security Model

| Control | Implementation |
| --- | --- |
| Tenant isolation | Every vector query carries a mandatory `tenant_id` filter; cross-tenant retrieval is not expressible through the service layer |
| Secret redaction | Credential, token and PII patterns are stripped during ingestion, before chunking and embedding |
| Upload validation | Server-side MIME allowlist (`.md`, `.txt`, `.pdf`); type is verified server-side, never trusted from the client |
| CORS | Explicit origin allowlist (development origins only); no wildcard |
| Secrets handling | All keys in a git-ignored `.env`; the env file is resolved by absolute path so the app cannot silently boot with an empty environment |
| Grounded answers | The system instruction forbids answering outside retrieved context; sources accompany every answer |
| External API bounds | Embedding cache, batching and exponential backoff; `MAX_CHUNKS_PER_QUERY` caps context size and spend |
| Auditability | Citations expose exactly which chunks grounded each answer |

---

## 7. Retrieval: What It Is (and Is Not)

- **It is real RAG.** Embeddings, vector search, context injection and citation — not a
  static prompt block presented as retrieval.
- **Retrieval is semantic, not lexical.** The query is embedded with the same model used at
  ingestion; ranking is vector similarity, filtered by tenant.
- **Overlap produces near-duplicates.** Sliding-window chunking means several chunks of one
  document can rank in the top-5. The UI deduplicates citations by `(filename, snippet)`;
  backend-level deduplication is roadmap.
- **It is not fine-tuning and not a knowledge graph.** The model has no memory of the
  documents beyond the context injected per request.
- **Answer language follows document language.** i18n covers the interface only (§8).

---

## 8. Internationalization

Three locales — PT-BR, EN, ZH-CN — with 26 keys each and no i18n library.

- First visit auto-detects via `navigator.language`.
- An in-app switcher overrides the choice and persists it in `localStorage`.
- Fallback chain: active locale → English → raw key (a visible key is a detectable defect).
- `document.documentElement.lang` is updated on change for accessibility and SEO.

Scope note: i18n translates the **UI**. LLM answers depend on the language of the ingested
documents.

---

## 9. Quality Assurance

### 9.1 Current state: manual

QA is performed **manually**. There is no automated suite yet; the roadmap for one is in
§9.3. The checklist below is executed on every change:

| Check | How it is verified |
| --- | --- |
| Upload happy path | `.md` upload returns a document id; ingestion logs complete |
| Invalid MIME rejected | Non-allowlisted type returns a validation error |
| Redaction | A document containing a fake token is ingested; the token is absent from stored chunks and citations |
| Grounded answer | Chat returns an answer consistent with the runbook, plus sources |
| Citation dedup | A single-document corpus yields one citation block, not five |
| i18n parity | Switcher renders all UI strings in PT, EN and ZH without reload |
| CORS | A request from a non-allowlisted origin is blocked by the browser |
| Rate-limit recovery | A 429 during ingestion recovers via backoff without data loss |
| Settings loading | App boots with `.env` at repository root regardless of process CWD |
| Clean shutdown | Stopping with Ctrl+C leaves no port or Qdrant lock held |

### 9.2 Incident log (development-time defects and process failures)

Defects fixed silently teach nothing. The incidents below are recorded with root cause and
guardrail. Items 1–7 are product or configuration defects; item 8 is a tooling/process
incident, classified separately because it never reached the product.

| # | Symptom | Root cause | Resolution and guardrail |
| --- | --- | --- | --- |
| 1 | Settings loaded empty (`ValidationError`, `input_value={}`) | `env_file = ".env"` in pydantic-settings resolves against the process CWD; the file moved to the repository root while the server runs from `src/` | Env file resolved by absolute path derived from module location; boot-from-root check added to manual QA |
| 2 | Server "starts" but never serves; boot hangs | A stale Python process held port 8000 and the embedded Qdrant file lock after a terminal was closed without Ctrl+C | Processes killed; operational rule adopted: always stop with Ctrl+C; embedded Qdrant documented as single-process |
| 3 | Embedding calls failed with HTTP 429 during ingestion | Free-tier provider rate limits | Exponential backoff with retry, on-disk embedding cache, batched embedding; context capped by `MAX_CHUNKS_PER_QUERY` |
| 4 | Editor and Vite reported unknown compiler options (`erasableSyntaxOnly`, `noUncheckedSideEffectImports`, `tsBuildInfoFile` without `incremental`) | The Vite template emitted flags newer than the local TypeScript toolchain | tsconfig set pinned to a conservative, toolchain-compatible configuration |
| 5 | `npx tailwindcss init -p` failed ("could not determine executable"); Markdown rendered unstyled | Binary resolution failure; `@tailwindcss/typography` absent so `prose` classes were inert | Config files authored by hand; typography plugin added once unstyled Markdown was observed |
| 6 | Frontend requests blocked by CORS | Allowlist predated the Vite dev origin (5173) | Allowlist updated with explicit dev origins; wildcard deliberately not used |
| 7 | The same document cited up to five times per answer | Sliding-window overlap yields near-identical chunks that all rank in top-5 | UI-level citation dedup by `(filename, snippet)`; backend dedup on roadmap |
| 8 | Process incident: source files corrupted with PowerShell here-string delimiters; one module created in the wrong directory, breaking import resolution | Here-strings interpolate backticks and `${}`; delimiters landed inside file content; manual placement error | Rule adopted: source files are authored only in the editor, never via shell redirection; post-write verification (first/last line check). Classified as tooling/process failure, not a product defect |

### 9.3 Automated QA roadmap

- `pytest` suite for redaction, chunking, tenant filtering and MIME validation.
- Vitest + Testing Library for frontend components.
- GitHub Actions CI running the suite on push.
- i18n parity check asserting all locales share the same key set.

---

## 10. Honest Limits

- **Not deployed.** Local MVP by decision; deployment strategy is documented, not executed
  (§13).
- **No authentication yet.** The tenant is a fixed development identifier. Isolation is
  enforced in the service layer, but there is no login; JWT is the first roadmap item. This
  instance must not be exposed to untrusted networks.
- **Embedded Qdrant is single-process.** Unsuitable for concurrent workers or horizontal
  scale; server mode is the production path.
- **Manual QA only.** No automated suite exists yet (§9.3).
- **Free-tier models** were chosen for cost bounds, not benchmark leadership.
- **Citation dedup happens in the UI.** The backend may still return redundant chunks.
- **PDF ingestion is accepted but not yet covered by manual QA.** Markdown and plain text
  are the verified paths.

---

## 11. Project Structure

```
lore-rag/
├── src/                      FastAPI backend
│   ├── app/
│   │   ├── api/v1/           Routers: documents, ai/chat
│   │   ├── core/             Settings (pydantic-settings), security constants
│   │   ├── db/               SQLAlchemy base and session
│   │   ├── models/           Relational models
│   │   ├── services/         Ingestion, redaction, chunking, embedding,
│   │   │                     vector store, RAG orchestration
│   │   └── main.py           App factory, CORS, lifespan
│   └── run.py                Development entrypoint
├── front-end/                React SPA (Vite)
│   ├── src/
│   │   ├── components/       Chat, FileUpload, LanguageSwitcher
│   │   ├── i18n/             I18nContext + locales (pt-BR, en, zh-CN)
│   │   ├── services/api.ts   Axios client
│   │   └── types/            Shared TypeScript types
│   └── ...
├── .env                      Git-ignored; never committed
└── README.md / README.pt-BR.md / README.zh-CN.md
```

---

## Screenshots

### Main interface

<p align="center">
  <img src="docs/screenshots/interface.png" alt="Lore main interface with upload and chat" width="800" />
</p>

<p align="center">
  <em>Document upload and RAG chat with cited sources.</em>
</p>

---

### Document upload

<p align="center">
  <img src="docs/screenshots/upload-success.png" alt="Document upload with success message" width="800" />
</p>

<p align="center">
  <em>Complete pipeline: MIME validation, sanitization, chunking and vectorization.</em>
</p>

---

### RAG chat with citations

<p align="center">
  <img src="docs/screenshots/chat-response.png" alt="Chat response with cited sources" width="800" />
</p>

<p align="center">
  <em>Grounded answer on retrieved context, with cited and deduplicated chunks.</em>
</p>

---

### Internationalization

<p align="center">
  <img src="docs/screenshots/language-switcher.png" alt="Language switcher PT/EN/ZH" width="800" />
</p>

<p align="center">
  <em>Language switcher with automatic detection and localStorage persistence.</em>
</p>

---

## 12. Getting Started

### Prerequisites

- Python 3.11+, Node 18+, PostgreSQL running locally
- API keys: OpenRouter (embeddings), Groq (chat)

### Backend

```bash
cd src
python -m venv ../venv
../venv/Scripts/Activate.ps1        # Windows; use bin/activate on Unix
pip install -r requirements.txt
python run.py                       # http://127.0.0.1:8000  (Swagger at /docs)
```

### Frontend

```bash
cd front-end
npm install
npm run dev                         # http://localhost:5173
```

Both processes must run simultaneously, each in its own terminal. Stop them with Ctrl+C;
closing a terminal while a process runs can leave the port or the Qdrant lock held (§9.2,
incident 2).

### Environment variables (`.env` at repository root, never committed)

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string |
| `OPENROUTER_API_KEY` | Embedding provider |
| `GROQ_API_KEY` | Chat LLM provider |
| `EMBEDDING_MODEL` / `DEFAULT_LLM_MODEL` | Model identifiers |
| `QDRANT_PATH` | Embedded vector store directory |
| `MAX_CHUNKS_PER_QUERY` | Retrieval cap (context size and spend) |
| `RATE_LIMIT_PER_MINUTE` | Application rate-limit setting |
| `SECRET_KEY` | Application secret |
| `APP_NAME` / `DEBUG` | Metadata and debug flag |

---

## 13. Deployment Status and Strategy

Not deployed, by decision. Three strategies were evaluated for a future production run:

| Strategy | Shape | Trade-off |
| --- | --- | --- |
| VPS + Docker Compose | Containers for app, PostgreSQL and Qdrant server; data in volumes | Lowest cost, full control, demonstrates containerization; you own backups |
| Fully managed | PaaS for the app, managed Postgres, Qdrant Cloud | Zero ops; higher cost, less demonstrable engineering |
| Hybrid | PaaS app + managed Postgres + containerized Qdrant | Middle ground; stateless-PaaS volumes are a trap for vector data |

Required changes for any production run: Qdrant client in dual mode (`QDRANT_URL` +
`QDRANT_API_KEY` when set, embedded path otherwise); `DATABASE_URL` pointed at a managed
instance; JWT authentication replacing the development tenant; reverse proxy with HTTPS;
per-user rate limiting; backup and monitoring policy.

---

## 14. Roadmap

- JWT authentication (replace the development tenant identifier)
- Automated test suite and CI (§9.3)
- Backend-level citation deduplication
- Docker Compose for local development (PostgreSQL + Qdrant server)
- Manual QA coverage for PDF ingestion
- Execution of one deployment strategy (§13)

---

## 15. License and Author

MIT. See `LICENSE`.

**Brenda Tavares** — Backend Developer
B.A. in Humanities, Federal University of Bahia (UFBA)
Backend Development, Pitágoras Unopar Anhanguera University
GitHub: https://github.com/Brenda-Tavares
LinkedIn: https://www.linkedin.com/in/brenda-campos-tavares/
Contact: tavaresbrenda@proton.me

Embeddings served by OpenRouter; inference served by Groq; vector store by Qdrant
(open source). All provider keys are caller-supplied and never committed.