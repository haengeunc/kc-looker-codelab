"""Vertex AI / ADK Governed Looker & Knowledge Catalog Analyst Agent (2-Stage Sequential Pipeline)."""

import os
import subprocess
import sys
from pathlib import Path
import google.auth
from google.oauth2.credentials import Credentials

from looker_governed_kc_agent.kc_looker_mcp_server import (
    _get_gcp_token,
    looker_query,
    looker_get_fields,
    kc_check_governance,
    read_gcs_policy_document,
    generate_data_chart,
)
from looker_governed_kc_agent.prompt import (
    GOVERNANCE_STAGE_PROMPT,
    LOOKER_STAGE_PROMPT,
)


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
    return "YOUR-GCP-PROJECT"


PROJECT_ID = _detect_default_project()
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", PROJECT_ID)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"))

# Resilient Google Auth bridge for Vertex AI & GCS
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
    token = _get_gcp_token()
    if token:
        creds = Credentials(token=token, quota_project_id=quota_project_id or PROJECT_ID)
        return creds, PROJECT_ID
    return _orig_google_auth_default(scopes=scopes, request=request, quota_project_id=quota_project_id, default_scopes=default_scopes)


google.auth.default = _resilient_google_auth_default

from google.adk.agents import LlmAgent, SequentialAgent

DEFAULT_MODEL = os.environ.get("VERTEX_MODEL", "gemini-2.5-flash")

# --- 2-Stage Deterministic Governed Pipeline ---

# Stage 1: Governance, PII Guardrails & Unstructured Grounding
governance_policy_agent = LlmAgent(
    model=DEFAULT_MODEL,
    name="governance_policy_agent",
    description="Enforces Knowledge Catalog governance (PII guardrails, Gold certification) and reads GCS corporate policies.",
    instruction=GOVERNANCE_STAGE_PROMPT,
    tools=[
        kc_check_governance,
        read_gcs_policy_document,
    ],
)

# Stage 2: Looker Semantic Query & Native Visualization
looker_execution_agent = LlmAgent(
    model=DEFAULT_MODEL,
    name="looker_execution_agent",
    description="Executes deterministic semantic queries via Looker MCP (Text-to-Intent) and provides interactive Looker visualization links.",
    instruction=LOOKER_STAGE_PROMPT,
    tools=[
        looker_query,
        looker_get_fields,
        generate_data_chart,
    ],
)

# Root Sequential Pipeline
root_agent = SequentialAgent(
    name="looker_governed_kc_agent",
    description=(
        "Enterprise 2-Stage Governed Data Analyst Agent powered by Vertex AI, Knowledge Catalog, and Looker. "
        "Stage 1: Enforces data governance, PII guardrails, and corporate policy grounding. "
        "Stage 2: Executes deterministic Looker semantic queries with native interactive visualizations."
    ),
    sub_agents=[
        governance_policy_agent,
        looker_execution_agent,
    ],
)
