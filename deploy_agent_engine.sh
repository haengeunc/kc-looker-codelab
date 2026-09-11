#!/usr/bin/env bash
# Deploy the Looker Analyst Agent to Vertex AI Agent Engine (Reasoning Engine)
# so it can be linked directly into Gemini Enterprise (Google Agentspace).

set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-haengeun-429200}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
DISPLAY_NAME="${DISPLAY_NAME:-Looker Knowledge Catalog Analyst Agent}"

echo "================================================================"
echo " Deploying Looker Analyst Agent to Vertex AI Agent Engine"
echo " Project:      $PROJECT_ID"
echo " Region:       $REGION"
echo " Display Name: $DISPLAY_NAME"
echo "================================================================"

# 1. Ensure Vertex AI Reasoning Engine Service Account has permissions
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
RE_SA="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

echo "Granting Dataplex Knowledge Catalog, Looker, and BigQuery IAM roles to Vertex AI Agent Engine SA ($RE_SA)..."
for ROLE in \
  "roles/aiplatform.user" \
  "roles/dataplex.viewer" \
  "roles/dataplex.catalogViewer" \
  "roles/looker.schemaViewer" \
  "roles/bigquery.jobUser" \
  "roles/bigquery.dataViewer"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${RE_SA}" \
    --role="$ROLE" \
    --condition=None \
    --quiet >/dev/null || true
done

# 2. Deploy via ADK CLI to Vertex AI Agent Engine
/usr/local/google/home/haengeun/projects/demo-kc-bq/.venv/bin/adk deploy agent_engine \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --display_name="$DISPLAY_NAME" \
  --description="Enterprise Data Analyst Agent grounded in Looker semantic metadata from Knowledge Catalog (Dataplex) and BigQuery." \
  /usr/local/google/home/haengeun/projects/demo-kc-bq/looker_analyst_agent
