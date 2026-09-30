#!/usr/bin/env bash
# ==============================================================================
# Master Deployment Orchestrator for All 4 Patterns
# Deploys to Google Cloud Run (ADK Dev UI) AND Vertex AI Agent Engine in-place.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-opm-looker-core-demo-instance}"
export GOOGLE_CLOUD_REGION="${GOOGLE_CLOUD_REGION:-us-central1}"

# Target Reasoning Engine IDs (In-Place Updates)
RE_PATTERN_1="8024503590590611456"
RE_PATTERN_2="1557334525686579200"
RE_PATTERN_3="1416051679563874304"
RE_PATTERN_4="1246414627584081920"

TARGET_PATTERN="${1:-all}"

deploy_pattern_1() {
  echo ""
  echo "================================================================================"
  echo " [1/4] DEPLOYING PATTERN 1: Baseline BigQuery Analyst Agent"
  echo "================================================================================"
  echo "--> 1. Deploying to Cloud Run (Service: bq-baseline-agent)..."
  "${SCRIPT_DIR}/patterns/1-bq-baseline/deploy_cloud_run.sh"
  
  echo "--> 2. Deploying to Vertex AI Agent Engine (RE ID: ${RE_PATTERN_1})..."
  AGENT_ENGINE_ID="${RE_PATTERN_1}" "${SCRIPT_DIR}/patterns/1-bq-baseline/deploy_agent_engine.sh"
  echo "✅ Pattern 1 deployment complete."
}

deploy_pattern_2() {
  echo ""
  echo "================================================================================"
  echo " [2/4] DEPLOYING PATTERN 2: Looker KC Grounded SQL Analyst Agent"
  echo "================================================================================"
  echo "--> 1. Deploying to Cloud Run (Service: kc-analyst-agent)..."
  "${SCRIPT_DIR}/patterns/2-kc-bq-sql/deploy_cloud_run.sh"

  echo "--> 2. Deploying to Vertex AI Agent Engine (RE ID: ${RE_PATTERN_2})..."
  AGENT_ENGINE_ID="${RE_PATTERN_2}" "${SCRIPT_DIR}/patterns/2-kc-bq-sql/deploy_agent_engine.sh"
  echo "✅ Pattern 2 deployment complete."
}

deploy_pattern_3() {
  echo ""
  echo "================================================================================"
  echo " [3/4] DEPLOYING PATTERN 3: Governed Looker Semantic Intent Agent"
  echo "================================================================================"
  echo "--> 1. Deploying to Cloud Run (Service: looker-governed-kc-agent)..."
  "${SCRIPT_DIR}/patterns/3-kc-looker-intent/deploy_cloud_run.sh"

  echo "--> 2. Deploying to Vertex AI Agent Engine (RE ID: ${RE_PATTERN_3})..."
  AGENT_ENGINE_ID="${RE_PATTERN_3}" "${SCRIPT_DIR}/patterns/3-kc-looker-intent/deploy_agent_engine.sh"
  echo "✅ Pattern 3 deployment complete."
}

deploy_pattern_4() {
  echo ""
  echo "================================================================================"
  echo " [4/4] DEPLOYING PATTERN 4: Looker-Free Dataplex-Governed Agent"
  echo "================================================================================"
  echo "--> 1. Deploying to Cloud Run (Service: kc-pure-governance-agent)..."
  "${SCRIPT_DIR}/patterns/4-kc-pure-governance/deploy_cloud_run.sh"

  echo "--> 2. Deploying to Vertex AI Agent Engine (RE ID: ${RE_PATTERN_4})..."
  AGENT_ENGINE_ID="${RE_PATTERN_4}" "${SCRIPT_DIR}/patterns/4-kc-pure-governance/deploy_agent_engine.sh"
  echo "✅ Pattern 4 deployment complete."
}

case "$TARGET_PATTERN" in
  1|"pattern-1"|"pattern1"|"baseline")
    deploy_pattern_1
    ;;
  2|"pattern-2"|"pattern2"|"kc-sql")
    deploy_pattern_2
    ;;
  3|"pattern-3"|"pattern3"|"looker")
    deploy_pattern_3
    ;;
  4|"pattern-4"|"pattern4"|"pure-kc")
    deploy_pattern_4
    ;;
  all|"ALL"|"")
    deploy_pattern_1
    deploy_pattern_2
    deploy_pattern_3
    deploy_pattern_4
    ;;
  *)
    echo "Unknown pattern: $TARGET_PATTERN"
    echo "Usage: ./deploy_all.sh [1|2|3|4|all]"
    exit 1
    ;;
esac

echo ""
echo "================================================================================"
echo " 🎉 ALL REQUESTED DEPLOYMENTS COMPLETED SUCCESSFULLY!"
echo " Both Google Cloud Run and Vertex AI Agent Engine are synchronized."
echo "================================================================================"
