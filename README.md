# Insurance agent on Google Cloud

Reference project for the blog series "Agentic AI on Google Cloud" (Parts 1 to 5).
It is a **scaffold assembled from the series**: read it, run it in a sandbox project, and
check every GCP, ADK and Terraform detail against current documentation before relying on it.

## Layout

```
src/api/          FastAPI service (chat endpoint, JWT auth)            -> Cloud Run service agent-api
src/agent/        ADK agent, tools, evidence callback
src/verify/       claim extraction, checks, citations, response policy
src/rag/          BigQuery vector search with version/date filters
src/ingestion/    parse, chunk, embed, load; Pub/Sub endpoint and batch job
tests/            unit, security, fake claims API
evals/            golden set, runner, thresholds
graph/            Spanner Graph schema (Part 6); src/graph, src/graph_sync (named queries, guards, sync)
infra/bootstrap/  one-time setup per project (state bucket, Workload Identity Federation)
infra/terraform/  modules/platform + envs/{dev,prod}
.github/workflows CI, deploy-app, deploy-infra, drift
```

## Quick start (local)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit -q                      # no cloud access needed
cp .env.example .env                      # then export the variables
uvicorn tests.fake_claims:app --port 9000 &
export AGENT_ALLOW_DEV_TOKENS=true       # LOCAL ONLY: bearer token = customer id
uvicorn src.api.main:app --port 8080
curl -s localhost:8080/api/v1/chat -H "Authorization: Bearer cust-7" \
  -H "Content-Type: application/json" -d '{"message":"Why was CLM-1042 rejected?"}'
```

## Deploy (summary)

1. For each GCP project run `infra/bootstrap/bootstrap.sh` (state bucket, Workload Identity Federation, deployer service accounts).
2. In GitHub create environments `dev`, `prod`, `prod-promote` and set the variables listed in `.github/workflows/README.md`.
3. Push to `main`: `deploy-infra` applies Terraform, `deploy-app` builds, canaries, evaluates and promotes.
4. Add the real claims token as a new Secret Manager version and set the model names in `envs/*/terraform.tfvars`.

Graph (Part 6) is OFF by default (AGENT_ENABLE_GRAPH=false, Terraform enable_graph=false).

Not included: Cloud SQL for shared sessions (set `AGENT_SESSIONS_DB_URL` when you add it), Cloud Scheduler for nightly reindex, the React front end.
