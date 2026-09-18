"""Vertex AI / ADK Analyst Agent connected to Knowledge Catalog MCP & BigQuery MCP Toolbox."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
import google.auth
from google.oauth2.credentials import Credentials

from looker_analyst_agent.kc_bq_mcp_server import (
    _get_access_token,
    search_knowledge_catalog,
    get_looker_explore_metadata,
    get_looker_view_metadata,
    check_lookml_in_knowledge_catalog,
    read_gcs_policy_document,
    execute_bigquery_sql,
    generate_data_chart,
)
from looker_analyst_agent.prompt import LOOKER_ANALYST_PROMPT


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
        # Verify token validity
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
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

MCP_SERVER_SCRIPT = str((Path(__file__).parent / "kc_bq_mcp_server.py").resolve())
TOOLBOX_BINARY = shutil.which("toolbox") or os.path.expanduser("~/.local/bin/toolbox")


def build_agent_tools():
    """Constructs the toolset combining Knowledge Catalog MCP and BigQuery MCP Toolbox."""
    tools = [
        # 1. Knowledge Catalog & BigQuery MCP Tools
        check_lookml_in_knowledge_catalog,
        search_knowledge_catalog,
        get_looker_explore_metadata,
        get_looker_view_metadata,
        read_gcs_policy_document,
        execute_bigquery_sql,
        generate_data_chart,
    ]

    # 2. If USE_MCP_STDIO=1 is set, also attach the stdio MCPToolset server
    if os.environ.get("USE_MCP_STDIO", "0") == "1":
        tools.append(
            MCPToolset(
                connection_params=StdioServerParameters(
                    command=sys.executable,
                    args=[MCP_SERVER_SCRIPT],
                    env={
                        "GOOGLE_CLOUD_PROJECT": PROJECT_ID,
                        "DATAPLEX_LOCATION": os.environ.get("DATAPLEX_LOCATION", "us-central1"),
                        "PATH": os.environ.get("PATH", ""),
                    },
                )
            )
        )

    # 3. If USE_BINARY_TOOLBOX=1 is set, attach the GenAI Toolbox binary (--prebuilt dataplex & bigquery)
    if os.environ.get("USE_BINARY_TOOLBOX", "0") == "1" and os.path.exists(TOOLBOX_BINARY):
        tools.append(
            MCPToolset(
                connection_params=StdioServerParameters(
                    command=TOOLBOX_BINARY,
                    args=["--prebuilt", "dataplex", "--prebuilt", "bigquery", "--stdio"],
                    env={
                        "BIGQUERY_PROJECT": PROJECT_ID,
                        "DATAPLEX_PROJECT": PROJECT_ID,
                        "GOOGLE_CLOUD_PROJECT": PROJECT_ID,
                        "PATH": os.environ.get("PATH", ""),
                    },
                )
            )
        )

    return tools


root_agent = LlmAgent(
    model=os.environ.get("VERTEX_MODEL", "gemini-2.5-pro"),
    name="looker_knowledge_catalog_analyst_agent",
    description=(
        "Enterprise Data Analyst Agent powered by Vertex AI that connects to "
        "Knowledge Catalog (Dataplex) MCP for Looker semantic metadata (Views, Explores, Joins, Measures) "
        "and BigQuery MCP Toolbox for SQL execution."
    ),
    instruction=LOOKER_ANALYST_PROMPT,
    tools=build_agent_tools(),
)
