#!/usr/bin/env bash
# Deploy Pattern 4: Looker-Free Dataplex-Governed Analyst Agent to Vertex AI Agent Engine
# Deploys to opm-looker-core-demo-instance while querying haengeun-f478f for unified management & publishing.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-opm-looker-core-demo-instance}"
TARGET_PROJECT_ID="${TARGET_PROJECT_ID:-haengeun-f478f}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
DISPLAY_NAME="${DISPLAY_NAME:-looker-free-dataplex-governed-agent}"

echo "================================================================"
echo " Deploying Pattern 4 Agent to Vertex AI Agent Engine"
echo " Host Project:    $PROJECT_ID"
echo " Target Project:  $TARGET_PROJECT_ID (BigQuery + Dataplex)"
echo " Region:          $REGION"
echo " Display Name:    $DISPLAY_NAME"
echo "================================================================"

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
RE_SA="service-${PROJECT_NUMBER}@gcp-sa-aiplatform.iam.gserviceaccount.com"
RE_RUNTIME_SA="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

echo "Ensuring Vertex AI Agent Engine SAs permissions in host and target projects..."
# Host project roles
for SA in "$RE_SA" "$RE_RUNTIME_SA"; do
  for ROLE in "roles/aiplatform.user" "roles/bigquery.jobUser" "roles/bigquery.dataViewer"; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:${SA}" \
      --role="$ROLE" \
      --condition=None \
      --quiet >/dev/null || true
  done
done

# Target project roles
for SA in "$RE_SA" "$RE_RUNTIME_SA"; do
  for ROLE in "roles/bigquery.dataViewer" "roles/bigquery.jobUser" "roles/bigquery.user" "roles/serviceusage.serviceUsageConsumer" "roles/dataplex.metadataReader" "roles/dataplex.viewer"; do
    gcloud projects add-iam-policy-binding "$TARGET_PROJECT_ID" \
      --member="serviceAccount:${SA}" \
      --role="$ROLE" \
      --condition=None \
      --quiet >/dev/null || true
  done
done

# Ensure requirements.txt exists in agent directory
cp -f "${SCRIPT_DIR}/requirements.txt" "${SCRIPT_DIR}/kc_pure_agent/requirements.txt"

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
  --description="Pattern 4: Looker-Free Dataplex-Governed Analyst Agent (Pure Knowledge Catalog metadata + BigQuery)" \
  "${EXTRA_ARGS[@]}" \
  "${SCRIPT_DIR}/kc_pure_agent"
