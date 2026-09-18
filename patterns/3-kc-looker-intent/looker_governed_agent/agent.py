"""Vertex AI / ADK Governed Looker & Knowledge Catalog Analyst Agent."""

import os
import subprocess
import sys
from pathlib import Path
import google.auth
from google.oauth2.credentials import Credentials

from looker_governed_agent.kc_looker_mcp_server import (
    _get_gcp_token,
    looker_query,
    looker_get_fields,
    kc_check_governance,
    read_gcs_policy_document,
    generate_data_chart,
)
from looker_governed_agent.prompt import LOOKER_GOVERNED_PROMPT


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

from google.adk.agents import LlmAgent


def build_agent_tools():
    """Builds the toolset combining Looker Semantic Engine, Knowledge Catalog Governance, and GCS Docs."""
    return [
        # 1. Looker Semantic Query (Text-to-Intent)
        looker_query,
        looker_get_fields,
        # 2. Knowledge Catalog Governance (Certification & PII Guardrails)
        kc_check_governance,
        # 3. Unstructured Grounding (GCS Corporate Policy PDFs)
        read_gcs_policy_document,
        # 4. Data Visualization Engine (Base64 PNGs)
        generate_data_chart,
    ]


root_agent = LlmAgent(
    model=os.environ.get("VERTEX_MODEL", "gemini-2.5-pro"),
    name="looker_governed_intent_agent",
    description=(
        "Enterprise Governed Data Analyst Agent that uses Looker as a deterministic semantic engine "
        "(Text-to-Intent without LLM SQL generation), combined with Knowledge Catalog governance "
        "(PII protection & Gold Certification) and GCS unstructured policy documents."
    ),
    instruction=LOOKER_GOVERNED_PROMPT,
    tools=build_agent_tools(),
)
