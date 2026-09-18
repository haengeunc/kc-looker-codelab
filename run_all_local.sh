#!/usr/bin/env bash
# Script to run all 3 agent patterns locally for side-by-side comparison in 3 browser tabs.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"
ADK_BIN="${SCRIPT_DIR}/.venv/bin/adk"

if [[ ! -x "$ADK_BIN" ]]; then
  echo "ADK binary not found in virtualenv. Using system adk..."
  ADK_BIN="adk"
fi

export PYTHONPATH="${SCRIPT_DIR}:${SCRIPT_DIR}/patterns/1-bq-baseline:${SCRIPT_DIR}/patterns/2-kc-bq-sql:${SCRIPT_DIR}/patterns/3-kc-looker-intent:${PYTHONPATH:-}"

echo "=================================================================="
echo " 3-Tier Data Agent Demo Launcher"
echo "=================================================================="
echo " Pattern 1: Baseline (BQ MCP only)              -> Port 8080"
echo " Pattern 2: Governed SQL (KC + GCS + BQ MCP)   -> Port 8081"
echo " Pattern 3: Governed Intent (KC + GCS + Looker) -> Port 8082"
echo "=================================================================="

case "${1:-all}" in
  1|baseline)
    echo "Starting Pattern 1 (Baseline BQ) on http://localhost:8080/dev-ui/?app=baseline_analyst_agent ..."
    cd "${SCRIPT_DIR}/patterns/1-bq-baseline"
    "$ADK_BIN" web --port 8080 baseline_analyst_agent
    ;;
  2|kc-bq)
    echo "Starting Pattern 2 (Governed BQ) on http://localhost:8081/dev-ui/?app=looker_analyst_agent ..."
    cd "${SCRIPT_DIR}/patterns/2-kc-bq-sql"
    "$ADK_BIN" web --port 8081 looker_analyst_agent
    ;;
  3|looker)
    echo "Starting Pattern 3 (Governed Looker) on http://localhost:8082/dev-ui/?app=looker_governed_agent ..."
    cd "${SCRIPT_DIR}/patterns/3-kc-looker-intent"
    "$ADK_BIN" web --port 8082 looker_governed_agent
    ;;
  all)
    echo "Launching all 3 agents in parallel background processes..."
    echo "Logs will be written to /tmp/agent_pattern_*.log"

    cd "${SCRIPT_DIR}/patterns/1-bq-baseline"
    "$ADK_BIN" web --port 8080 baseline_analyst_agent > /tmp/agent_pattern_1.log 2>&1 &
    PID1=$!

    cd "${SCRIPT_DIR}/patterns/2-kc-bq-sql"
    "$ADK_BIN" web --port 8081 looker_analyst_agent > /tmp/agent_pattern_2.log 2>&1 &
    PID2=$!

    cd "${SCRIPT_DIR}/patterns/3-kc-looker-intent"
    "$ADK_BIN" web --port 8082 looker_governed_agent > /tmp/agent_pattern_3.log 2>&1 &
    PID3=$!

    echo ""
    echo "Agents are running!"
    echo " • Pattern 1: http://localhost:8080/dev-ui/?app=baseline_analyst_agent (PID: $PID1)"
    echo " • Pattern 2: http://localhost:8081/dev-ui/?app=looker_analyst_agent   (PID: $PID2)"
    echo " • Pattern 3: http://localhost:8082/dev-ui/?app=looker_governed_agent  (PID: $PID3)"
    echo ""
    echo "Press Ctrl+C to stop all three servers."
    trap "kill $PID1 $PID2 $PID3 2>/dev/null || true; exit 0" INT TERM
    wait
    ;;
  *)
    echo "Usage: $0 [1|2|3|all]"
    exit 1
    ;;
esac
