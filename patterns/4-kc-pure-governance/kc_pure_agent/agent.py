"""Vertex AI Agent definition for Pattern 4: Looker-Free Dataplex-Governed Analyst Agent."""

import os
import google.auth
from google.oauth2.credentials import Credentials

try:
    from kc_pure_agent.kc_pure_mcp_server import (
        _get_access_token,
        get_current_datetime,
        search_catalog,
        get_catalog_metadata,
        execute_query,
        generate_data_chart,
    )
except ImportError:
    from kc_pure_mcp_server import (
        _get_access_token,
        get_current_datetime,
        search_catalog,
        get_catalog_metadata,
        execute_query,
        generate_data_chart,
    )

TARGET_PROJECT_ID = os.environ.get("TARGET_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "haengeun-f478f"
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", TARGET_PROJECT_ID)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"))

# Load sovereign system instructions
INSTRUCTIONS_PATH = os.path.join(os.path.dirname(__file__), "agent_instructions.txt")
with open(INSTRUCTIONS_PATH, "r", encoding="utf-8") as f:
    SOVEREIGN_INSTRUCTIONS = f.read()

# Setup resilient google auth
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
        return creds, proj or TARGET_PROJECT_ID
    except Exception:
        pass
    token = _get_access_token()
    if token:
        creds = Credentials(token=token, quota_project_id=quota_project_id or TARGET_PROJECT_ID)
        return creds, TARGET_PROJECT_ID
    return _orig_google_auth_default(scopes=scopes, request=request, quota_project_id=quota_project_id, default_scopes=default_scopes)


google.auth.default = _resilient_google_auth_default

from google.adk.agents import LlmAgent

root_agent = LlmAgent(
    model=os.environ.get("VERTEX_MODEL", "gemini-2.5-flash"),
    name="kc_pure_governance_agent",
    description=(
        "Sovereign Enterprise Data Analyst Agent governed exclusively by Google Cloud Dataplex "
        "Knowledge Catalog without Looker or LookML dependencies."
    ),
    instruction=SOVEREIGN_INSTRUCTIONS,
    tools=[
        get_current_datetime,
        search_catalog,
        get_catalog_metadata,
        execute_query,
        generate_data_chart,
    ],
)
