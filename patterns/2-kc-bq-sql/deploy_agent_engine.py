#!/usr/bin/env python3
"""Deploys looker_analyst_agent to Vertex AI Agent Engine using active gcloud credentials."""

import os
from pathlib import Path
import subprocess
import sys
import google.auth
from google.oauth2.credentials import Credentials


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
AGENT_DIR = str((Path(__file__).parent / "looker_analyst_agent").resolve())

# 1. Obtain valid access token from gcloud CLI
res = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True, check=True)
token = res.stdout.strip()


# 2. Patch google.auth.default BEFORE importing ADK CLI or Vertex AI SDK
def _patched_default(scopes=None, request=None, quota_project_id=None, default_scopes=None):
    creds = Credentials(token=token, quota_project_id=quota_project_id or PROJECT_ID)
    return creds, PROJECT_ID


google.auth.default = _patched_default

# 3. Invoke ADK CLI deploy agent_engine
from google.adk.cli.cli_tools_click import main

if __name__ == "__main__":
    args = [
        "adk",
        "deploy",
        "agent_engine",
        f"--project={PROJECT_ID}",
        f"--region={REGION}",
        "--display_name=Looker Knowledge Catalog Analyst Agent",
        "--description=Enterprise Data Analyst Agent grounded in Looker semantic metadata from Knowledge Catalog (Dataplex) and BigQuery.",
    ]
    agent_engine_id = os.environ.get("AGENT_ENGINE_ID")
    if agent_engine_id:
        args.append(f"--agent_engine_id={agent_engine_id}")
    args.append(AGENT_DIR)

    sys.argv = args
    main()
