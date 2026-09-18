#!/usr/bin/env bash
# Script to run all 3 agent patterns locally on Cloudtop for side-by-side comparison.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"
ADK_BIN="${SCRIPT_DIR}/.venv/bin/adk"
HOSTNAME="$(hostname)"

if [[ ! -x "$ADK_BIN" ]]; then
  ADK_BIN="adk"
fi

export PYTHONPATH="${SCRIPT_DIR}:${SCRIPT_DIR}/patterns/1-bq-baseline:${SCRIPT_DIR}/patterns/2-kc-bq-sql:${SCRIPT_DIR}/patterns/3-kc-looker-intent:${PYTHONPATH:-}"

echo "=================================================================="
echo " 3-Tier Data Agent Demo Launcher (Binding to 0.0.0.0)"
echo " Cloudtop Hostname: $HOSTNAME"
echo "=================================================================="
echo " Pattern 1: Baseline (BQ MCP only)              -> Port 8080"
echo " Pattern 2: Governed SQL (KC + GCS + BQ MCP)   -> Port 8081"
echo " Pattern 3: Governed Intent (KC + GCS + Looker) -> Port 8082"
echo "=================================================================="

case "${1:-all}" in
  1|baseline)
    echo "Starting Pattern 1 on http://${HOSTNAME}:8080/dev-ui/?app=baseline_analyst_agent ..."
    cd "${SCRIPT_DIR}/patterns/1-bq-baseline"
    "$ADK_BIN" web --host 0.0.0.0 --port 8080 --allow_origins "*" baseline_analyst_agent
    ;;
  2|kc-bq)
    echo "Starting Pattern 2 on http://${HOSTNAME}:8081/dev-ui/?app=looker_analyst_agent ..."
    cd "${SCRIPT_DIR}/patterns/2-kc-bq-sql"
    "$ADK_BIN" web --host 0.0.0.0 --port 8081 --allow_origins "*" looker_analyst_agent
    ;;
  3|looker)
    echo "Starting Pattern 3 on http://${HOSTNAME}:8082/dev-ui/?app=looker_governed_agent ..."
    cd "${SCRIPT_DIR}/patterns/3-kc-looker-intent"
    "$ADK_BIN" web --host 0.0.0.0 --port 8082 --allow_origins "*" looker_governed_agent
    ;;
  all)
    echo "Launching all 3 agents in parallel background processes..."

    cd "${SCRIPT_DIR}/patterns/1-bq-baseline"
    "$ADK_BIN" web --host 0.0.0.0 --port 8080 --allow_origins "*" baseline_analyst_agent > /tmp/agent_pattern_1.log 2>&1 &
    PID1=$!

    cd "${SCRIPT_DIR}/patterns/2-kc-bq-sql"
    "$ADK_BIN" web --host 0.0.0.0 --port 8081 --allow_origins "*" looker_analyst_agent > /tmp/agent_pattern_2.log 2>&1 &
    PID2=$!

    cd "${SCRIPT_DIR}/patterns/3-kc-looker-intent"
    "$ADK_BIN" web --host 0.0.0.0 --port 8082 --allow_origins "*" looker_governed_agent > /tmp/agent_pattern_3.log 2>&1 &
    PID3=$!

    echo ""
    echo "Agents are now running! Access them from your laptop browser via Cloudtop proxy:"
    echo " • Pattern 1: http://${HOSTNAME}:8080/dev-ui/?app=baseline_analyst_agent"
    echo " • Pattern 2: http://${HOSTNAME}:8081/dev-ui/?app=looker_analyst_agent"
    echo " • Pattern 3: http://${HOSTNAME}:8082/dev-ui/?app=looker_governed_agent"
    echo ""
    echo "Or if using SSH port forwarding from your laptop:"
    echo " ssh -L 8080:localhost:8080 -L 8081:localhost:8081 -L 8082:localhost:8082 ${HOSTNAME}"
    echo " • Pattern 1: http://localhost:8080/dev-ui/?app=baseline_analyst_agent"
    echo " • Pattern 2: http://localhost:8081/dev-ui/?app=looker_analyst_agent"
    echo " • Pattern 3: http://localhost:8082/dev-ui/?app=looker_governed_agent"
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
