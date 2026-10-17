# Security Model — Lore

This document describes the security posture of the Lore MVP. It is intended for
reviewers and security-minded engineers, not as a replacement for a live penetration test.
The system is a local development prototype and is not deployed; several controls are
enforced by construction in the codebase, others are documented gaps on the roadmap.

Companion documents:
- [README.md](README.md) — project overview, architecture, getting started
- [LICENSE](LICENSE) — license terms

---

## 1. Threat Model

Lore handles **operational documents that may contain secrets** (credentials, tokens,
hostnames, PII) and answers questions about them using an external LLM. The threat
surface has four actors:

| Actor | Trust level | Threat |
| --- | --- | --- |
| Local developer (you) | Trusted | Misconfiguration, accidental commit of secrets, unsafe termination leaving port/lock held |
| Upstream AI provider (OpenRouter, Groq) | Semi-trusted | Rate limiting, model availability, potential leakage of prompt content to provider logs |
| Malicious uploaded document | Untrusted | Injection of instructions into chunks (prompt injection via retrieval), secret exfiltration |
| Cross-tenant reader (future, multi-user) | Untrusted | Retrieval of chunks ingested by another tenant |

The MVP runs single-tenant on localhost, so actors (3) and (4) are partially theoretical
today; controls for them exist because the architecture was designed to scale to them.

---

## 2. Controls in Place

### 2.1 Secret and PII redaction (ingestion-time)

**Where:** `src/app/services/redaction.py` (or equivalent module in the ingestion
pipeline).

**What it does:** Patterns matching credentials, API keys, tokens, connection strings
and common PII formats are stripped from document text **before chunking and embedding**.

**Why before chunking:** A secret that never enters the vector store cannot be retrieved
by any query, echoed by the LLM, or leaked via a citation snippet. Post-storage
redaction would leave the secret present in at least one chunk, retrievable by a
sufficiently similar query.

**Honest limit:** Pattern-based redaction is not a guarantee. Unusual secret formats,
base64-encoded credentials, or secrets embedded in images (PDF) may pass through. The
footer of the UI and the README both state explicitly: *"Do not input real credentials
into documents."*

### 2.2 Tenant isolation (query-time)

**Where:** Vector store query layer.

**What it does:** Every vector search carries a mandatory `tenant_id` filter applied at
the Qdrant query level. The retrieval service does not expose a path that omits this
filter; cross-tenant retrieval is inexpressible through the service API.

**Current state:** The tenant identifier is a fixed development constant read from
configuration. There is **no authentication** in the MVP, so all requests today share
the same tenant. The control is structural — swapping the constant for a claim extracted
from a JWT (roadmap) preserves the same filter, without any change to the retrieval
service.

**Honest limit:** Until authentication lands, the tenant filter protects against
programmatic mistakes, not against a malicious caller. This instance must not be
exposed to untrusted networks.

### 2.3 Upload validation

**Where:** `POST /api/v1/documents/upload` handler.

**What it does:** Server-side MIME allowlist (`.md`, `.txt`, `.pdf`). The declared
`Content-Type` from the client is not trusted; the actual file content is inspected.

**Honest limit:** PDF ingestion is accepted by the allowlist but its redaction coverage
is not verified by manual QA (§9.1 of the README). Markdown and plain text are the
verified paths.

### 2.4 CORS allowlist

**Where:** `src/app/main.py`, `CORSMiddleware` configuration.

**What it does:** Explicit origin allowlist with the development origins
(`http://localhost:5173`, `http://127.0.0.1:5173`, etc.). No wildcard.

**Why explicit:** A wildcard `*` would let any page on the public web issue requests to
your local API while the server runs. The allowlist closes that surface for free.

### 2.5 Secrets handling

**Where:** `src/app/core/config.py`, pydantic-settings.

**What it does:** All keys (`OPENROUTER_API_KEY`, `GROQ_API_KEY`, `DATABASE_URL`,
`SECRET_KEY`) are read from a `.env` file resolved by **absolute path** derived from
the module location. The `.env` is git-ignored.

**Why absolute path:** pydantic-settings' default `env_file = ".env"` resolves against
the process CWD. The app can silently boot with an empty environment if run from the
wrong directory, which is worse than failing loudly. The incident log (§9.2 of the
README, item 1) records the bug this guardrail was added to prevent.

**What it does NOT do:** Secrets are never logged, never echoed in error responses,
never included in exception tracebacks returned to the client.

### 2.6 Grounded answers with citations

**Where:** `src/app/services/rag.py` (system prompt and post-processing).

**What it does:** The LLM is instructed, via the system prompt, to answer **only** from
the retrieved context and to refuse when the context is insufficient. Every response
returns the chunks that grounded it. The system prompt also instructs the model to
respond in the same language as the user's question, regardless of the language of
the retrieved documents — so a PT/EN/ZH UI produces answers in the matching language
even when the corpus is in a single language.

**Why this matters for security:** An unauditable answer is an injection vector — a
model answering from memory can be steered into disclosing system-prompt content or
fabricating commands. A cited answer lets a human verify, in seconds, whether the
answer is grounded or hallucinated.

**Honest limit (language):** The language-matching instruction works reliably for
high-resource languages (Portuguese, English, Simplified Chinese). For low-resource
languages or very short queries (1–2 words with no language signal), the model may
fall back to the dominant language of the retrieved context. This is a prompt-level
control, not a language detection system.

### 2.7 External API bounds

**Where:** Embedding service.

**What it does:**
- On-disk embedding cache (identical text never re-embedded).
- Batching (multiple chunks per provider call).
- Exponential backoff on HTTP 429.
- `MAX_CHUNKS_PER_QUERY` cap on context size.
- `RATE_LIMIT_PER_MINUTE` application-level cap.

**Why:** Unbounded context growth is both a spend risk (paid embeddings) and an
injection surface (more chunks = more opportunity for a poisoned chunk to rank). The
cap is a control, not a tuning knob.

### 2.8 Frontend hygiene

**Where:** `front-end/src/services/api.ts`, `front-end/index.html`.

**What it does:**
- Axios client points at a fixed `baseURL`; no user-controlled URL construction.
- The frontend bundle contains **no API keys** — the browser never sees
  `OPENROUTER_API_KEY` or `GROQ_API_KEY`.
- Markdown rendering via `react-markdown` (no raw `dangerouslySetInnerHTML` with
  server content).

### 2.9 Deployment Security Considerations (roadmap)

When this MVP moves from localhost to production, these controls become mandatory:

| Control | Current state | Production requirement |
| --- | --- | --- |
| Authentication | Development tenant constant | JWT auth, tenant extracted from token |
| HTTPS | Absent (localhost) | TLS termination via reverse proxy (Caddy/nginx) |
| Per-user rate limit | Absent | Required before multi-user deployment |
| Vector store | Embedded Qdrant (single-process) | Qdrant server with API key and TLS |
| Backup policy | None | Automated database + Qdrant snapshots |
| Monitoring | None | Alerting on failed redaction, anomalous query patterns |
| Dependency scanning | Manual | Automated `npm audit` + `pip-audit` in CI |

The architecture is designed to accept these controls without structural changes:
the tenant filter (§2.2) swaps a constant for a JWT claim, the embedding service
(§2.7) already has rate limiting infrastructure, and the CORS allowlist (§2.4)
expands from localhost to production origins.

---

## 3. OWASP LLM Top 10 Mapping

| LLM Risk | Lore's posture | Notes |
| --- | --- | --- |
| **LLM01 — Prompt Injection** | Mitigated by redaction + grounded system prompt. Direct system-prompt injection from the client is not a surface: the system prompt is assembled server-side and never read from the request. | Indirect injection (via a malicious ingested document) is reduced by redaction but not eliminated. |
| **LLM02 — Sensitive Information Disclosure** | Mitigated by ingestion-time redaction; secrets never reach the vector store. | Pattern coverage is bounded; see §2.1 honest limit. |
| **LLM03 — Supply Chain Vulnerabilities** | Dependencies pinned; `package-lock.json` and `requirements.txt` committed. | No automated dependency scanning in CI yet (roadmap). |
| **LLM04 — Data and Model Poisoning** | Mitigated by upload validation + redaction; retrieval filtered by tenant. | No adversarial training or retrieval-time anomaly detection. |
| **LLM05 — Improper Output Handling** | Markdown rendered via `react-markdown`, not raw HTML. No `dangerouslySetInnerHTML` with server content. | Citations expose the grounding chunks, letting the user verify the output. |
| **LLM06 — Excessive Agency** | No tool calls, no function execution, no file writes from the LLM. The LLM produces text only. | The system has no agency to abuse. |
| **LLM07 — System Prompt Leakage** | System prompt is fixed, short, and contains no secrets. The model is instructed not to reproduce it. | No dedicated anti-echo filter (OWASP LLM07 specific) yet. Roadmap: server-side scan of LLM output for verbatim echoes of the system prompt before returning to client, similar to Claritas implementation. |
| **LLM08 — Vector and Embedding Weaknesses** | Mandatory tenant filter on every vector query; no unfiltered search endpoint exists. | Embedded Qdrant is single-process — no concurrency bug class for now. |
| **LLM09 — Misinformation** | Mitigated by grounding + citations; model told to refuse when context is insufficient. | Not a benchmark; the model can still be wrong within the retrieved context. |
| **LLM10 — Unbounded Consumption** | `MAX_CHUNKS_PER_QUERY`, embedding cache + batching, application rate limit, exponential backoff. | No per-user rate limit yet (no users yet). |

---

## 4. Known Gaps and Roadmap

| Gap | Current state | Roadmap |
| --- | --- | --- |
| Authentication | Development tenant constant; no login | JWT auth, tenant extracted from token |
| PDF redaction | Accepted by upload allowlist, not covered by manual QA | Extend redaction patterns or drop PDF from allowlist |
| Anti-echo filter | Absent | Add OWASP LLM07 scan on LLM output before release |
| Dependency scanning | Manual | Automated `npm audit` + `pip-audit` in CI |
| Automated tests | None | pytest suite for redaction, chunking, tenant filter, MIME; Vitest for frontend |
| Vector store in production | Embedded (single-process) | Qdrant server with API key |
| Reverse proxy / HTTPS | Absent (localhost) | Caddy or nginx with TLS termination |
| Per-user rate limit | Absent | Required once authentication lands |
| Backup policy | None | Database + Qdrant snapshot schedule once deployed |

---

## 5. Reporting a Vulnerability

This is a portfolio project maintained by a single developer. If you find a security
issue, please contact the author directly at **tavaresbrenda@proton.me** rather than
opening a public issue, so a fix can land before disclosure.

Public disclosure window: 30 days from acknowledgement, or earlier if a fix is released.

---

## 6. Incident Response

This is a portfolio project maintained by a single developer. If a security incident
occurs in a deployed instance (future roadmap):

1. **Immediate response:** Disable the affected endpoint, rotate all API keys
   (`OPENROUTER_API_KEY`, `GROQ_API_KEY`), and notify users via the repository's
   security advisories.

2. **Investigation:** Review logs (once logging is added), identify the root cause,
   and document the incident in a public advisory.

3. **Fix and disclosure:** Release a patch within 7 days of confirmation, then
   publish the advisory with root cause, impact and mitigation.

4. **Post-incident:** Update this document and the threat model to reflect the
   new attack surface.

The 30-day disclosure window (§5) applies to externally reported vulnerabilities.
Internally discovered incidents follow the same timeline but start from discovery,
not acknowledgement.