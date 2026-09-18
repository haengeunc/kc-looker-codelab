#!/usr/bin/env bash
# Deploy the Baseline BigQuery Analyst Agent (LLM + BigQuery MCP only) to Google Cloud Run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-opm-looker-core-demo-instance}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-bq-baseline-agent}"

echo "================================================================"
echo " Deploying Baseline BigQuery Agent to Cloud Run"
echo " Project:      $PROJECT_ID"
echo " Region:       $REGION"
echo " Service Name: $SERVICE_NAME"
echo "================================================================"

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Granting required Vertex AI and BigQuery IAM roles to $SERVICE_ACCOUNT..."
for ROLE in \
  "roles/aiplatform.user" \
  "roles/bigquery.jobUser" \
  "roles/bigquery.dataViewer"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="$ROLE" \
    --condition=None \
    --quiet >/dev/null || true
done

ADK_BIN="adk"
if [[ -x "${SCRIPT_DIR}/../demo-kc-bq/.venv/bin/adk" ]]; then
  ADK_BIN="${SCRIPT_DIR}/../demo-kc-bq/.venv/bin/adk"
elif [[ -x "${SCRIPT_DIR}/.venv/bin/adk" ]]; then
  ADK_BIN="${SCRIPT_DIR}/.venv/bin/adk"
fi

echo "Deploying via adk deploy cloud_run (with Web UI and A2A protocol enabled)..."
"$ADK_BIN" deploy cloud_run \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --service_name="$SERVICE_NAME" \
  --with_ui \
  --a2a \
  --env GOOGLE_GENAI_USE_VERTEXAI=1 \
  --env GOOGLE_CLOUD_PROJECT="$PROJECT_ID" \
  --env GOOGLE_CLOUD_LOCATION="$REGION" \
  "${SCRIPT_DIR}/baseline_analyst_agent" \
  -- --allow-unauthenticated
