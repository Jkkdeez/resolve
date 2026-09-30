# Resolve

Resolve is a Tectonic Hackathon proof of concept for the SD Worx challenge: it turns fragmented organisational information into a trusted, contextual answer. Rather than merely retrieve text, it evaluates structured claims against authority, jurisdiction, validity period, ownership, permission scope and known conflicts.

## Working vertical slice

Ask: **“Can a Belgian employee work remotely from Spain for eight working days?”**

The service retrieves five competing claims, then:

- uses the current, People Operations Belgium–owned 2026 policy;
- uses a Teams update only as corroboration;
- rejects the expired 2024 handbook;
- rejects the Netherlands policy for a jurisdiction mismatch; and
- downranks an ownerless, unverified shared file.

The UI presents evidence dimensions—not an unexplained probability—and records which evidence was accepted, rejected, or downranked.

**Scenario B — safe escalation.** Ask how overtime should be calculated for a Belgian customer. Two current, authoritative claims conflict, so Resolve refuses to invent an answer and routes the question to Anna De Smet, Belgian Payroll Compliance.

**Scenario C — reusable expert knowledge.** In Anna's expert workspace, confirm the signed customer agreement. The conflict changes to resolved and the next identical question returns that accountable, human-verified decision with its rationale.

The companion **Knowledge lifecycle** panel is backed by `GET /v1/knowledge/overview`: it shows the actor-scoped path from ingested sources to contextual claims, conflicts, expert resolutions and recent question events. It is intentionally a governed data pipeline view, so Payroll never sees HR-only knowledge and vice versa.

## Architecture

```text
Next.js + TypeScript + Tailwind     FastAPI deterministic trust engine
                 │                              │
                 └──────────── REST ────────────┘
                                                │
                    PostgreSQL + pgvector ◄────┘
                    (durable repository when DATABASE_URL is set)
                                                │
                    Vertex AI / Gemini ◄──────── embeddings, extraction and comparison hooks
```

The MVP deliberately keeps the final decisions deterministic. Gemini/Vertex is reserved for claim extraction, semantic retrieval and contradiction suggestion; it must not overrule dates, jurisdictions, permissions or source authority.

`apps/api/app/ai.py` is the bounded Vertex/Gemini adapter and `apps/api/.env.example` documents the required Google Cloud configuration. With Application Default Credentials it can call Gemini for claim proposals and `text-embedding-004` for embeddings; model output remains untrusted until Resolve validates it.

`apps/api/app/models.py` and `apps/api/app/repository.py` persist **Sources, Claims, Conflicts, Experts, Questions and Resolutions**, including pgvector embedding columns. The application uses PostgreSQL automatically when `DATABASE_URL` is set, and retains an in-memory adapter for instant, credential-free demos.

## Governed ingestion pipeline

`POST /v1/sources/ingest` is the connector-neutral data pipe. It accepts a bounded source payload, requires a `knowledge_admin` scope, records ownership/jurisdiction/effective dates/visibility, extracts deterministic policy claims, and opens a conflict only when two current official claims disagree. Future Teams, Drive and SD Worx connectors map into this contract; they do not bypass the trust engine.

## Security design

- All question routes require an authenticated actor (`x-resolve-user` / `x-resolve-roles` in the development adapter). Cloud Run deployment replaces this with verified OIDC identity.
- Retrieval filters sources by the actor’s scope *before* claims are ranked. A user cannot infer a source they cannot access through answer content or evidence cards.
- There is no unauthorised direct-source endpoint; future source endpoints must make the same actor-scoped check.
- Request input is bounded and validated. Secrets live in environment variables and are excluded from git.

## Run locally

Prerequisites: Node 20+, Python 3.11+, and optionally Docker for PostgreSQL.

```bash
python3 -m venv .venv
.venv/bin/pip install -r apps/api/requirements-dev.txt
.venv/bin/uvicorn app.main:app --app-dir apps/api --reload --port 8000

pnpm install
pnpm dev:web
```

Open `http://localhost:3000`. The frontend talks to the API through its development rewrite. For the complete durable stack (web, API, PostgreSQL + pgvector), run `docker compose up --build`. The API automatically switches to PostgreSQL and the frontend routes requests to the containerised API. See [DEPLOYMENT.md](DEPLOYMENT.md) for local lifecycle commands and the Cloud Run sequence.

## Test

```bash
PYTHONPATH=apps/api python3 -m unittest discover -s apps/api/tests -v
```

The tests cover Scenarios A–C, permission-filtered retrieval, and the governed source ingestion/conflict-detection path.

## Deployment

The repository ships non-root API/web containers, Cloud Build definitions, a configurable API origin and a full local Compose stack. Cloud Run needs your Google Cloud project, database secret and production identity configuration; the exact deployment sequence is in [DEPLOYMENT.md](DEPLOYMENT.md).
