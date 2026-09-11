#!/usr/bin/env python3
"""Deploys looker_analyst_agent to Vertex AI Agent Engine using active gcloud credentials."""

import subprocess
import sys
import google.auth
from google.oauth2.credentials import Credentials

# 1. Obtain valid access token from gcloud CLI
res = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True, check=True)
token = res.stdout.strip()

# 2. Patch google.auth.default BEFORE importing ADK CLI or Vertex AI SDK
def _patched_default(scopes=None, request=None, quota_project_id=None, default_scopes=None):
    creds = Credentials(token=token, quota_project_id=quota_project_id or "haengeun-429200")
    return creds, "haengeun-429200"

google.auth.default = _patched_default

# 3. Invoke ADK CLI deploy agent_engine
from google.adk.cli.cli_tools_click import main

if __name__ == "__main__":
    sys.argv = [
        "adk",
        "deploy",
        "agent_engine",
        "--project=haengeun-429200",
        "--region=us-central1",
        "--agent_engine_id=4496964624452681728",
        "--display_name=Looker Knowledge Catalog Analyst Agent",
        "--description=Enterprise Data Analyst Agent grounded in Looker semantic metadata from Knowledge Catalog (Dataplex) and BigQuery.",
        "/usr/local/google/home/haengeun/projects/demo-kc-bq/looker_analyst_agent",
    ]
    main()
