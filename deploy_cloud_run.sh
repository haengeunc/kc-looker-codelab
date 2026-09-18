#!/usr/bin/env bash
# Deploy the Vertex AI Looker Analyst Agent (Knowledge Catalog MCP + BigQuery MCP Toolbox) to Google Cloud Run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-kc-analyst-agent}"

if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "(unset)" ]]; then
  echo "Error: GOOGLE_CLOUD_PROJECT is not set and gcloud default project is not configured."
  echo "Run: export GOOGLE_CLOUD_PROJECT=YOUR-GCP-PROJECT"
  exit 1
fi

echo "================================================================"
echo " Deploying KC Analyst Agent to Cloud Run"
echo " Project:      $PROJECT_ID"
echo " Region:       $REGION"
echo " Service Name: $SERVICE_NAME"
echo "================================================================"

# 1. Get Project Number to grant IAM roles to default Cloud Run Service Account
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Granting required Vertex AI, Dataplex Knowledge Catalog, Looker, and BigQuery IAM roles to $SERVICE_ACCOUNT..."
for ROLE in \
  "roles/aiplatform.user" \
  "roles/dataplex.viewer" \
  "roles/dataplex.catalogViewer" \
  "roles/looker.schemaViewer" \
  "roles/bigquery.jobUser" \
  "roles/bigquery.dataViewer"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="$ROLE" \
    --condition=None \
    --quiet >/dev/null
done

# 2. Resolve adk CLI executable
ADK_BIN="adk"
if [[ -x "${SCRIPT_DIR}/.venv/bin/adk" ]]; then
  ADK_BIN="${SCRIPT_DIR}/.venv/bin/adk"
fi

# 3. Deploy via ADK CLI (includes ADK Web UI via --with_ui and A2A endpoint via --a2a)
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
  "${SCRIPT_DIR}/kc_analyst_agent" \
  -- --allow-unauthenticated
