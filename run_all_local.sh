#!/usr/bin/env bash
# Script to run all 4 agent patterns locally on Cloudtop for side-by-side comparison.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"
ADK_BIN="${SCRIPT_DIR}/.venv/bin/adk"
HOSTNAME="$(hostname)"

if [[ ! -x "$ADK_BIN" ]]; then
  ADK_BIN="adk"
fi

export PYTHONPATH="${SCRIPT_DIR}:${SCRIPT_DIR}/patterns/1-bq-baseline:${SCRIPT_DIR}/patterns/2-kc-bq-sql:${SCRIPT_DIR}/patterns/3-kc-looker-intent:${SCRIPT_DIR}/patterns/4-kc-pure-governance:${PYTHONPATH:-}"

echo "=================================================================="
echo " 4-Tier Data Agent Demo Launcher (Binding to 0.0.0.0)"
echo " Cloudtop Hostname: $HOSTNAME"
echo "=================================================================="
echo " Pattern 1: Baseline (BQ MCP only)                -> Port 8080"
echo " Pattern 2: Governed SQL (KC + GCS + BQ MCP)     -> Port 8081"
echo " Pattern 3: Governed Intent (KC + GCS + Looker)   -> Port 8082"
echo " Pattern 4: Pure KC Governance (Looker-Free)      -> Port 8083"
echo "=================================================================="

case "${1:-all}" in
  1|baseline)
    echo "Starting Pattern 1 on http://${HOSTNAME}:8080/dev-ui/?app=baseline_bq_only_agent ..."
    cd "${SCRIPT_DIR}/patterns/1-bq-baseline"
    "$ADK_BIN" web --host 0.0.0.0 --port 8080 --allow_origins "*" baseline_bq_only_agent
    ;;
  2|kc-bq)
    echo "Starting Pattern 2 on http://${HOSTNAME}:8081/dev-ui/?app=kc_analyst_agent ..."
    cd "${SCRIPT_DIR}/patterns/2-kc-bq-sql"
    "$ADK_BIN" web --host 0.0.0.0 --port 8081 --allow_origins "*" kc_analyst_agent
    ;;
  3|looker)
    echo "Starting Pattern 3 on http://${HOSTNAME}:8082/dev-ui/?app=looker_governed_kc_agent ..."
    cd "${SCRIPT_DIR}/patterns/3-kc-looker-intent"
    "$ADK_BIN" web --host 0.0.0.0 --port 8082 --allow_origins "*" looker_governed_kc_agent
    ;;
  4|pure-kc)
    echo "Starting Pattern 4 on http://${HOSTNAME}:8083/dev-ui/?app=kc_pure_agent ..."
    cd "${SCRIPT_DIR}/patterns/4-kc-pure-governance"
    "$ADK_BIN" web --host 0.0.0.0 --port 8083 --allow_origins "*" kc_pure_agent
    ;;
  all)
    echo "Launching all 4 agents in parallel background processes..."

    cd "${SCRIPT_DIR}/patterns/1-bq-baseline"
    "$ADK_BIN" web --host 0.0.0.0 --port 8080 --allow_origins "*" baseline_bq_only_agent > /tmp/agent_pattern_1.log 2>&1 &
    PID1=$!

    cd "${SCRIPT_DIR}/patterns/2-kc-bq-sql"
    "$ADK_BIN" web --host 0.0.0.0 --port 8081 --allow_origins "*" kc_analyst_agent > /tmp/agent_pattern_2.log 2>&1 &
    PID2=$!

    cd "${SCRIPT_DIR}/patterns/3-kc-looker-intent"
    "$ADK_BIN" web --host 0.0.0.0 --port 8082 --allow_origins "*" looker_governed_kc_agent > /tmp/agent_pattern_3.log 2>&1 &
    PID3=$!

    cd "${SCRIPT_DIR}/patterns/4-kc-pure-governance"
    "$ADK_BIN" web --host 0.0.0.0 --port 8083 --allow_origins "*" kc_pure_agent > /tmp/agent_pattern_4.log 2>&1 &
    PID4=$!

    echo ""
    echo "Agents are now running! Access them from your laptop browser via Cloudtop proxy:"
    echo " • Pattern 1: http://${HOSTNAME}:8080/dev-ui/?app=baseline_bq_only_agent"
    echo " • Pattern 2: http://${HOSTNAME}:8081/dev-ui/?app=kc_analyst_agent"
    echo " • Pattern 3: http://${HOSTNAME}:8082/dev-ui/?app=looker_governed_kc_agent"
    echo " • Pattern 4: http://${HOSTNAME}:8083/dev-ui/?app=kc_pure_agent"
    echo ""
    echo "Or if using SSH port forwarding from your laptop:"
    echo " ssh -L 8080:localhost:8080 -L 8081:localhost:8081 -L 8082:localhost:8082 -L 8083:localhost:8083 ${HOSTNAME}"
    echo " • Pattern 1: http://localhost:8080/dev-ui/?app=baseline_bq_only_agent"
    echo " • Pattern 2: http://localhost:8081/dev-ui/?app=kc_analyst_agent"
    echo " • Pattern 3: http://localhost:8082/dev-ui/?app=looker_governed_kc_agent"
    echo " • Pattern 4: http://localhost:8083/dev-ui/?app=kc_pure_agent"
    echo ""
    echo "Press Ctrl+C to stop all four servers."
    trap "kill $PID1 $PID2 $PID3 $PID4 2>/dev/null || true; exit 0" INT TERM
    wait
    ;;
  *)
    echo "Usage: $0 [1|2|3|4|all]"
    exit 1
    ;;
esac
