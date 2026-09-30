# Resolve

Resolve is a Tectonic Hackathon proof of concept for the SD Worx challenge: it turns fragmented organisational information into a trusted, contextual answer. Rather than merely retrieve text, it evaluates structured claims against authority, jurisdiction, validity period, ownership, permission scope and known conflicts.

## Working vertical slice — Scenario A

Ask: **“Can a Belgian employee work remotely from Spain for eight working days?”**

The service retrieves five competing claims, then:

- uses the current, People Operations Belgium–owned 2026 policy;
- uses a Teams update only as corroboration;
- rejects the expired 2024 handbook;
- rejects the Netherlands policy for a jurisdiction mismatch; and
- downranks an ownerless, unverified shared file.

The UI presents evidence dimensions—not an unexplained probability—and records which evidence was accepted, rejected, or downranked.

## Architecture

```text
Next.js + TypeScript + Tailwind     FastAPI deterministic trust engine
                 │                              │
                 └──────────── REST ────────────┘
                                                │
                    PostgreSQL + pgvector ◄────┘
                    (production adapter/model contract)
                                                │
                    Vertex AI / Gemini ◄──────── embeddings, extraction and comparison hooks
```

The MVP deliberately keeps the final decisions deterministic. Gemini/Vertex is reserved for claim extraction, semantic retrieval and contradiction suggestion; it must not overrule dates, jurisdictions, permissions or source authority.

`apps/api/app/ai.py` is the bounded Vertex/Gemini adapter seam and `apps/api/.env.example` documents the required Google Cloud configuration. It intentionally does not make model calls until a hackathon GCP project and credentials are supplied.

`apps/api/app/models.py` has the persistence contract for **Sources, Claims, Conflicts, Experts, Questions and Resolutions**, including pgvector embedding columns. The demo repository is in-memory to keep this first slice reproducible without a database or cloud credential.

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

Open `http://localhost:3000`. The frontend talks to the API through its development rewrite. For PostgreSQL + pgvector, run `docker compose up -d database`.

## Test

```bash
PYTHONPATH=apps/api python3 -m unittest discover -s apps/api/tests -v
```

The tests cover Scenario A, Scenario B’s safe expert escalation hook, and permission-filtered retrieval.

## Next slices

- **Scenario B:** expose the existing current-conflict escalation and assignment flow for Anna, Belgian Payroll Compliance.
- **Scenario C:** write an expert decision to `resolutions`, attach it to the conflict, and prioritize it as human-verified reusable knowledge.
- Add the PostgreSQL repository/migrations, Vertex embeddings and authenticated Cloud Run deployment only after those visible flows work.
