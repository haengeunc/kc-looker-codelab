"""Vertex AI / ADK Analyst Agent connected to Knowledge Catalog MCP & BigQuery MCP Toolbox (3-Stage Sequential Pipeline)."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
import google.auth
from google.oauth2.credentials import Credentials

from kc_analyst_agent.kc_bq_mcp_server import (
    _get_access_token,
    search_knowledge_catalog,
    get_looker_explore_metadata,
    get_looker_view_metadata,
    check_lookml_in_knowledge_catalog,
    read_gcs_policy_document,
    execute_bigquery_sql,
    generate_data_chart,
)
from kc_analyst_agent.prompt import (
    DISCOVERY_STAGE_PROMPT,
    SQL_STAGE_PROMPT,
    PRESENTATION_STAGE_PROMPT,
)


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


# Configure Vertex AI environment defaults
PROJECT_ID = _detect_default_project()
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", PROJECT_ID)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"))

# Resilient Google Auth bridge: automatically uses Cloud Run / Agent Engine metadata server
# or gcloud CLI when Application Default Credentials (ADC) RAPT token is expired locally.
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
        return creds, proj or PROJECT_ID
    except Exception:
        pass
    creds = Credentials(
        token=_get_access_token(),
        quota_project_id=quota_project_id or PROJECT_ID,
    )
    return creds, PROJECT_ID


google.auth.default = _resilient_google_auth_default

from google.adk.agents import LlmAgent, SequentialAgent

DEFAULT_MODEL = os.environ.get("VERTEX_MODEL", "gemini-2.5-flash")

# --- 3-Stage Deterministic Sequential Pipeline ---

# Stage 1: Metadata & Governance Discovery
metadata_discovery_agent = LlmAgent(
    model=DEFAULT_MODEL,
    name="metadata_discovery_agent",
    description="Discovers certified Looker Explores, Views, Joins, and Measures from Knowledge Catalog and GCS policy docs.",
    instruction=DISCOVERY_STAGE_PROMPT,
    tools=[
        check_lookml_in_knowledge_catalog,
        search_knowledge_catalog,
        get_looker_explore_metadata,
        get_looker_view_metadata,
        read_gcs_policy_document,
    ],
)

# Stage 2: Grounded BigQuery SQL Execution
sql_execution_agent = LlmAgent(
    model=DEFAULT_MODEL,
    name="sql_execution_agent",
    description="Compiles LookML measure formulas into standard BigQuery SQL grounded in Stage 1 metadata and executes it.",
    instruction=SQL_STAGE_PROMPT,
    tools=[
        execute_bigquery_sql,
    ],
)

# Stage 3: Presentation, Visualizations & Governance Attribution
presentation_agent = LlmAgent(
    model=DEFAULT_MODEL,
    name="presentation_agent",
    description="Formats executive answers, renders data charts (Matplotlib PNG + Mermaid), and attributes Looker governance.",
    instruction=PRESENTATION_STAGE_PROMPT,
    tools=[
        generate_data_chart,
    ],
)

# Root Sequential Pipeline
root_agent = SequentialAgent(
    name="kc_analyst_agent",
    description=(
        "Enterprise 3-Stage Sequential Data Analyst Agent powered by Vertex AI. "
        "Stage 1: Discovers certified Looker metadata from Knowledge Catalog MCP. "
        "Stage 2: Compiles and executes grounded BigQuery SQL. "
        "Stage 3: Generates visual charts and executive attribution."
    ),
    sub_agents=[
        metadata_discovery_agent,
        sql_execution_agent,
        presentation_agent,
    ],
)
