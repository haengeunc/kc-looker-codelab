#!/usr/bin/env bash
# Deploy the Governed Looker & Knowledge Catalog Analyst Agent to Vertex AI Agent Engine (Reasoning Engine)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
DISPLAY_NAME="${DISPLAY_NAME:-Looker Governed Semantic Analyst Agent}"

if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "(unset)" ]]; then
  echo "Error: GOOGLE_CLOUD_PROJECT is not set and gcloud default project is not configured."
  echo "Run: export GOOGLE_CLOUD_PROJECT=YOUR-GCP-PROJECT"
  exit 1
fi

echo "================================================================"
echo " Deploying Governed Looker Agent to Vertex AI Agent Engine"
echo " Project:      $PROJECT_ID"
echo " Region:       $REGION"
echo " Display Name: $DISPLAY_NAME"
echo "================================================================"

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
RE_SA="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

echo "Granting Dataplex and Storage IAM roles to Vertex AI Agent Engine SA ($RE_SA)..."
for ROLE in \
  "roles/aiplatform.user" \
  "roles/dataplex.viewer" \
  "roles/dataplex.catalogViewer" \
  "roles/storage.objectViewer"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${RE_SA}" \
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

"$ADK_BIN" deploy agent_engine \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --display_name="$DISPLAY_NAME" \
  --description="Governed Data Analyst Agent that uses Looker as a deterministic semantic layer (Text-to-Intent) and Knowledge Catalog for PII & policy governance." \
  "${SCRIPT_DIR}/looker_governed_agent"
