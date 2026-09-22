#!/usr/bin/env python3
"""Deploys baseline_bq_only_agent to Vertex AI Agent Engine using active gcloud credentials."""

import os
from pathlib import Path
import subprocess
import sys


def _detect_default_project() -> str:
    for env_var in ("GOOGLE_CLOUD_PROJECT", "GCP_PROJECT", "DEVSHELL_PROJECT_ID"):
        val = os.environ.get(env_var)
        if val:
            return val
    try:
        out = subprocess.check_output(
            ["gcloud", "config", "get-value", "project"],
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).decode().strip()
        if out and out != "(unset)":
            return out
    except Exception:
        pass
    raise RuntimeError(
        "Google Cloud Project ID not found. Set export GOOGLE_CLOUD_PROJECT=YOUR-GCP-PROJECT "
        "or run `gcloud config set project YOUR-GCP-PROJECT`."
    )


PROJECT_ID = _detect_default_project()
REGION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
AGENT_DIR = str((Path(__file__).parent / "baseline_bq_only_agent").resolve())

os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = REGION

# Invoke ADK CLI deploy agent_engine
from google.adk.cli.cli_tools_click import main

if __name__ == "__main__":
    args = [
        "adk",
        "deploy",
        "agent_engine",
        f"--project={PROJECT_ID}",
        f"--region={REGION}",
        "--display_name=bigquery-baseline-analyst-agent",
        "--description=Baseline BigQuery Analyst Agent (LLM + BigQuery MCP only)",
    ]
    agent_engine_id = os.environ.get("AGENT_ENGINE_ID")
    if agent_engine_id:
        args.append(f"--agent_engine_id={agent_engine_id}")
    args.append(AGENT_DIR)

    sys.argv = args
    main()
