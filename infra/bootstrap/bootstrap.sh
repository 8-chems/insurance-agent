#!/usr/bin/env bash
# One-time setup per GCP project (run once for dev, once for prod).
# Usage: PROJECT=my-dev REGION=europe-west1 GITHUB_REPO=my-org/insurance-agent ./bootstrap.sh
set -euo pipefail
: "${PROJECT:?}" "${REGION:?}" "${GITHUB_REPO:?}"
NUM=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')

gcloud services enable iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com \
  cloudresourcemanager.googleapis.com serviceusage.googleapis.com storage.googleapis.com --project "$PROJECT"

# 1. Terraform state bucket (versioned)
gcloud storage buckets create "gs://$PROJECT-tfstate" --project "$PROJECT" --location "$REGION" \
  --uniform-bucket-level-access || true
gcloud storage buckets update "gs://$PROJECT-tfstate" --versioning

# 2. Workload Identity Federation: GitHub Actions proves who it is with a short-lived OIDC token
gcloud iam workload-identity-pools create github --project "$PROJECT" --location global \
  --display-name "GitHub Actions" || true
gcloud iam workload-identity-pools providers create-oidc github-provider --project "$PROJECT" \
  --location global --workload-identity-pool github \
  --issuer-uri "https://token.actions.githubusercontent.com" \
  --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition "assertion.repository=='$GITHUB_REPO'" || true

# 3. Two deployer identities: Terraform (powerful) and app deploys (narrow)
gcloud iam service-accounts create tf-sa --project "$PROJECT" --display-name "Terraform (CI)" || true
gcloud iam service-accounts create deploy-sa --project "$PROJECT" --display-name "App deploys (CI)" || true
TF="tf-sa@$PROJECT.iam.gserviceaccount.com"; DEP="deploy-sa@$PROJECT.iam.gserviceaccount.com"
PRINCIPAL="principalSet://iam.googleapis.com/projects/$NUM/locations/global/workloadIdentityPools/github/attribute.repository/$GITHUB_REPO"
for SA in "$TF" "$DEP"; do
  gcloud iam service-accounts add-iam-policy-binding "$SA" --project "$PROJECT" \
    --role roles/iam.workloadIdentityUser --member "$PRINCIPAL"
done

# 4. Roles. tf-sa creates infrastructure; deploy-sa only ships images and moves traffic.
for ROLE in roles/run.admin roles/iam.serviceAccountAdmin roles/resourcemanager.projectIamAdmin \
  roles/pubsub.admin roles/bigquery.admin roles/storage.admin roles/secretmanager.admin \
  roles/artifactregistry.admin roles/datastore.owner roles/serviceusage.serviceUsageAdmin \
  roles/logging.configWriter roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding "$PROJECT" --member "serviceAccount:$TF" --role "$ROLE" --condition=None >/dev/null
done
for ROLE in roles/run.developer roles/artifactregistry.writer; do
  gcloud projects add-iam-policy-binding "$PROJECT" --member "serviceAccount:$DEP" --role "$ROLE" --condition=None >/dev/null
done

echo "Set these GitHub environment variables:"
echo "  PROJECT_ID=$PROJECT  REGION=$REGION  TFSTATE_BUCKET=$PROJECT-tfstate"
echo "  WIF_PROVIDER=projects/$NUM/locations/global/workloadIdentityPools/github/providers/github-provider"
echo "  TF_SA=$TF  DEPLOY_SA=$DEP"
echo "After the first terraform apply, also grant deploy-sa roles/iam.serviceAccountUser on api-sa and ingest-sa."
