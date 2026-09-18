#!/usr/bin/env bash
# Deploy Baseline BigQuery Analyst Agent to Vertex AI Agent Engine (Reasoning Engine)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
DISPLAY_NAME="${DISPLAY_NAME:-bigquery-baseline-analyst-agent}"

if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "(unset)" ]]; then
  echo "Error: GOOGLE_CLOUD_PROJECT is not set."
  exit 1
fi

echo "================================================================"
echo " Deploying Baseline BigQuery Agent to Vertex AI Agent Engine"
echo " Project:      $PROJECT_ID"
echo " Region:       $REGION"
echo " Display Name: $DISPLAY_NAME"
echo "================================================================"

ADK_BIN="adk"
if [[ -x "${SCRIPT_DIR}/../demo-kc-bq/.venv/bin/adk" ]]; then
  ADK_BIN="${SCRIPT_DIR}/../demo-kc-bq/.venv/bin/adk"
fi

"$ADK_BIN" deploy agent_engine \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --display_name="$DISPLAY_NAME" \
  --description="Baseline BigQuery Analyst Agent (LLM + BigQuery MCP only)" \
  "${SCRIPT_DIR}/baseline_analyst_agent"
