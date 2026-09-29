#!/usr/bin/env bash
# Deploy Pattern 4: Looker-Free Dataplex-Governed Analyst Agent to Google Cloud Run with ADK Web UI.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-opm-looker-core-demo-instance}"
TARGET_PROJECT_ID="${TARGET_PROJECT_ID:-haengeun-f478f}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-kc-pure-governance-agent}"

echo "================================================================"
echo " Deploying Pattern 4 Agent to Cloud Run (ADK Web UI)"
echo " Host Project:    $PROJECT_ID"
echo " Target Project:  $TARGET_PROJECT_ID (BigQuery + Dataplex)"
echo " Region:          $REGION"
echo " Service Name:    $SERVICE_NAME"
echo "================================================================"

# 1. Resolve Cloud Run default Compute Engine Service Account
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Ensuring Cloud Run SA ($SERVICE_ACCOUNT) has permissions on host and target projects..."
# Host project roles
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

# Target project roles
for ROLE in \
  "roles/bigquery.dataViewer" \
  "roles/bigquery.jobUser" \
  "roles/bigquery.user" \
  "roles/serviceusage.serviceUsageConsumer" \
  "roles/dataplex.metadataReader" \
  "roles/dataplex.viewer"; do
  gcloud projects add-iam-policy-binding "$TARGET_PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="$ROLE" \
    --condition=None \
    --quiet >/dev/null || true
done

# 2. Ensure requirements.txt is in the agent directory
cp -f "${SCRIPT_DIR}/requirements.txt" "${SCRIPT_DIR}/kc_pure_agent/requirements.txt"

# 3. Resolve adk CLI executable
ADK_BIN="adk"
if [[ -x "${SCRIPT_DIR}/../../.venv/bin/adk" ]]; then
  ADK_BIN="${SCRIPT_DIR}/../../.venv/bin/adk"
elif [[ -x "${SCRIPT_DIR}/.venv/bin/adk" ]]; then
  ADK_BIN="${SCRIPT_DIR}/.venv/bin/adk"
fi

# 4. Deploy via ADK CLI to Cloud Run with public Web UI
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
  --env TARGET_PROJECT_ID="$TARGET_PROJECT_ID" \
  "${SCRIPT_DIR}/kc_pure_agent" \
  -- --allow-unauthenticated
