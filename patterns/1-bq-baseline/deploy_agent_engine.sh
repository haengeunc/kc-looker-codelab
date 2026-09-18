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

ADK_BIN="adk"
if [[ -x "${SCRIPT_DIR}/../../.venv/bin/adk" ]]; then
  ADK_BIN="${SCRIPT_DIR}/../../.venv/bin/adk"
elif [[ -x "${SCRIPT_DIR}/.venv/bin/adk" ]]; then
  ADK_BIN="${SCRIPT_DIR}/.venv/bin/adk"
fi

"$ADK_BIN" deploy agent_engine \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --display_name="$DISPLAY_NAME" \
  --description="Baseline BigQuery Analyst Agent (LLM + BigQuery MCP only)" \
  "${SCRIPT_DIR}/baseline_analyst_agent"
