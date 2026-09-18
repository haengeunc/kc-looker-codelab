"""Vertex AI / ADK Baseline BigQuery Analyst Agent (LLM + BigQuery MCP only)."""

import os
import subprocess
import google.auth
from google.oauth2.credentials import Credentials

from baseline_bq_only_agent.bq_mcp_server import (
    _get_access_token,
    list_datasets,
    list_tables,
    get_table_schema,
    execute_bigquery_sql,
    generate_data_chart,
)
from baseline_bq_only_agent.prompt import BASELINE_ANALYST_PROMPT


def _detect_default_project() -> str:
    """Detects GCP project from env, gcloud config, or defaults to YOUR-GCP-PROJECT."""
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
    return "YOUR-GCP-PROJECT"


PROJECT_ID = _detect_default_project()
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", PROJECT_ID)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"))

if not hasattr(google.auth, "_orig_default"):
    google.auth._orig_default = google.auth.default
_orig_google_auth_default = google.auth._orig_default


def _resilient_google_auth_default(scopes=None, request=None, quota_project_id=None, default_scopes=None):
    try:
        creds, proj = _orig_google_auth_default(
            scopes=scopes,
            request=request,
            quota_project_id=quota_project_id,
            default_scopes=default_scopes,
        )
        if getattr(creds, "valid", False):
            return creds, proj or PROJECT_ID
    except Exception:
        pass
    creds = Credentials(
        token=_get_access_token(),
        quota_project_id=quota_project_id or PROJECT_ID,
    )
    return creds, PROJECT_ID


google.auth.default = _resilient_google_auth_default

from google.adk.agents import LlmAgent

root_agent = LlmAgent(
    model=os.environ.get("VERTEX_MODEL", "gemini-2.5-pro"),
    name="baseline_bq_only_agent",
    description=(
        "Baseline BigQuery Data Analyst Agent powered by Vertex AI that executes "
        "raw SQL queries directly against BigQuery without Knowledge Catalog or Looker semantic governance."
    ),
    instruction=BASELINE_ANALYST_PROMPT,
    tools=[
        list_datasets,
        list_tables,
        get_table_schema,
        execute_bigquery_sql,
        generate_data_chart,
    ],
)
