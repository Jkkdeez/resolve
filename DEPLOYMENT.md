# Deployment

Resolve has two intentional runtime modes:

- **Demo mode:** no credentials or database needed. The API uses its seeded in-memory dataset.
- **Durable mode:** PostgreSQL with pgvector is selected automatically when `DATABASE_URL` exists.

## Local full stack

Install Docker Desktop, open it until its engine is running, then run:

```bash
docker compose up --build
```

Open `http://localhost:3000`; the API is available at `http://localhost:8000/health`.
PostgreSQL is exposed on port `5433` to avoid clashing with a locally installed database; containers use the internal `database:5432` address.

`docker compose down` stops the stack while preserving the local database. `docker compose down -v` also deletes the local demo data.

## Cloud Run

The images and build definitions are ready for Cloud Run, but a real deployment has one deliberate prerequisite: replace the development `x-resolve-*` headers with verified identity. A browser can forge those headers, so it would be wrong to expose the API and call that secure.

1. Choose a Google Cloud project, region and an Artifact Registry repository. Enable Cloud Run, Cloud Build, Artifact Registry, Secret Manager and Vertex AI APIs.
2. Create PostgreSQL with pgvector available (Cloud SQL or AlloyDB). Store its SQLAlchemy connection string as a Secret Manager secret named `resolve-database-url`. The account used by Cloud Run needs the least-privileged database role.
3. Build both images, substituting your project, region and the API URL:

```bash
gcloud builds submit --config infra/cloudbuild-api.yaml --substitutions _IMAGE=REGION-docker.pkg.dev/PROJECT/resolve/resolve-api:latest
gcloud builds submit --config infra/cloudbuild-web.yaml --substitutions _IMAGE=REGION-docker.pkg.dev/PROJECT/resolve/resolve-web:latest,_API_URL=https://RESOLVE_API_URL
```

4. Before deploying request-serving services, connect an identity-aware gateway or server-side session layer. It must verify the user, map the verified identity to Resolve scopes, and invoke the private API with a service identity. Do not rely on Cloud Run service-to-service IAM alone: Next.js rewrites do not automatically mint a user or service token.

For the hackathon, use the local Compose deployment for the live demo. The codebase is prepared for the Cloud Run platform, but we will not make a fake production-security claim before this identity boundary exists.

## Vertex AI

Set `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` and `VERTEX_GEMINI_MODEL` on the API service only after workload identity is configured. The deterministic trust engine remains the final authority: Gemini can propose extracted claims, embeddings and comparisons but cannot override ownership, jurisdiction, dates, permissions or an unresolved conflict.
