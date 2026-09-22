#!/usr/bin/env bash
# Deploy Baseline BigQuery Analyst Agent to Vertex AI Agent Engine (Reasoning Engine)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-opm-looker-core-demo-instance}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
DISPLAY_NAME="${DISPLAY_NAME:-bigquery-baseline-analyst-agent}"

echo "================================================================"
echo " Deploying Baseline BigQuery Agent to Vertex AI Agent Engine"
echo " Project:      $PROJECT_ID"
echo " Region:       $REGION"
echo " Display Name: $DISPLAY_NAME"
echo "================================================================"

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
RE_SA="service-${PROJECT_NUMBER}@gcp-sa-aiplatform.iam.gserviceaccount.com"

echo "Granting BigQuery IAM roles to Vertex AI Agent Engine SA ($RE_SA)..."
for ROLE in \
  "roles/aiplatform.user" \
  "roles/bigquery.jobUser" \
  "roles/bigquery.dataViewer"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${RE_SA}" \
    --role="$ROLE" \
    --condition=None \
    --quiet >/dev/null || true
done

ADK_BIN="adk"
if [[ -x "${SCRIPT_DIR}/../../.venv/bin/adk" ]]; then
  ADK_BIN="${SCRIPT_DIR}/../../.venv/bin/adk"
elif [[ -x "${SCRIPT_DIR}/.venv/bin/adk" ]]; then
  ADK_BIN="${SCRIPT_DIR}/.venv/bin/adk"
fi

EXTRA_ARGS=()
if [[ -n "${AGENT_ENGINE_ID:-}" ]]; then
  EXTRA_ARGS+=("--agent_engine_id=${AGENT_ENGINE_ID}")
fi

"$ADK_BIN" deploy agent_engine \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --display_name="$DISPLAY_NAME" \
  --description="Baseline BigQuery Analyst Agent (LLM + BigQuery MCP only)" \
  "${EXTRA_ARGS[@]}" \
  "${SCRIPT_DIR}/baseline_bq_only_agent"
