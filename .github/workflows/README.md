# GitHub setup

Create three **environments** in the repository settings: `dev`, `prod` (required reviewers) and
`prod-promote` (required reviewers). For `dev` and `prod` set these **environment variables**
(the values are printed at the end of `infra/bootstrap/bootstrap.sh`):

| Variable | Meaning |
|---|---|
| PROJECT_ID | GCP project of that environment |
| REGION | e.g. europe-west1 |
| TFSTATE_BUCKET | `<project>-tfstate` |
| WIF_PROVIDER | Workload Identity provider resource name |
| TF_SA / DEPLOY_SA | service accounts created by the bootstrap script |

Environment **secret** `EVAL_TOKENS` (dev and prod): JSON of test-customer tokens for the eval gate,
for example `{"cust-7": "...", "cust-8": "..."}`. Protect `main` and require the `ci` checks; add CODEOWNERS for `infra/`.
