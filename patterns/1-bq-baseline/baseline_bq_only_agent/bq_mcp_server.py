#!/usr/bin/env python3
"""MCP Server for BigQuery Baseline Analyst.

Delegates core BigQuery operations to the official Managed BigQuery MCP service
(https://bigquery.googleapis.com/mcp) under the hood:
1. get_current_datetime -> Real-time UTC system datetime and calendar quarter bounds
2. list_datasets -> Managed BigQuery MCP list_dataset_ids
3. list_tables -> Managed BigQuery MCP list_table_ids
4. get_table_schema -> Managed BigQuery MCP get_table_info
5. execute_bigquery_sql -> Managed BigQuery MCP execute_sql_readonly
"""

import base64
import calendar
import datetime
import io
import json
import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional

import requests
import google.auth
import google.auth.transport.requests

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

mcp = FastMCP("BigQuery-Baseline-Analyst-MCP")

MANAGED_BQ_MCP_URL = "https://bigquery.googleapis.com/mcp"
DEFAULT_PROJECT_ID = "opm-looker-core-demo-instance"
_TOKEN_CACHE: Dict[str, Any] = {"token": None, "expires_at": 0}


def _normalize_project_id(proj: Optional[str] = None) -> str:
    """Normalizes project ID to canonical alphanumeric ID if missing or numeric."""
    if not proj:
        env_proj = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        proj = env_proj or DEFAULT_PROJECT_ID
    # Map project numbers or invalid placeholders to canonical project ID
    if proj in ("234424439374", "YOUR-GCP-PROJECT") or str(proj).isdigit():
        return DEFAULT_PROJECT_ID
    return proj


def _get_auth_token() -> str:
    """Gets a valid Google Cloud OAuth2 access token for BigQuery API calls."""
    now = time.time()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expires_at"]:
        return _TOKEN_CACHE["token"]

    env_token = os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN")
    if env_token:
        _TOKEN_CACHE["token"] = env_token.strip()
        _TOKEN_CACHE["expires_at"] = now + 3000
        return _TOKEN_CACHE["token"]

    # 1. Native Cloud Run / GCE / Reasoning Engine Metadata Server
    try:
        meta_resp = requests.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
            timeout=2,
        )
        if meta_resp.status_code == 200:
            token_data = meta_resp.json()
            access_token = token_data.get("access_token")
            if access_token:
                _TOKEN_CACHE["token"] = access_token
                _TOKEN_CACHE["expires_at"] = now + min(token_data.get("expires_in", 3000), 3000)
                return _TOKEN_CACHE["token"]
    except Exception:
        pass

    # 2. Application Default Credentials via google.auth
    try:
        auth_fn = getattr(google.auth, "_orig_default", google.auth.default)
        creds, _ = auth_fn(scopes=[
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/bigquery",
        ])
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        if creds.token:
            _TOKEN_CACHE["token"] = creds.token
            _TOKEN_CACHE["expires_at"] = now + 3000
            return _TOKEN_CACHE["token"]
    except Exception:
        pass

    # 3. Local Cloudtop fallback via gcloud CLI
    if shutil.which("gcloud"):
        try:
            res = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True,
                text=True,
                check=False,
                timeout=3,
            )
            if res.returncode == 0 and res.stdout.strip():
                _TOKEN_CACHE["token"] = res.stdout.strip()
                _TOKEN_CACHE["expires_at"] = now + 3000
                return _TOKEN_CACHE["token"]
        except Exception:
            pass

    return ""


def _call_managed_bq_mcp(
    tool_name: str,
    arguments: Dict[str, Any],
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Invokes a tool on the official Managed BigQuery MCP server via JSON-RPC 2.0.

    Args:
        tool_name: The name of the tool on the Managed BigQuery MCP (e.g., 'list_dataset_ids').
        arguments: Arguments dictionary for the tool.
        project_id: Project ID to bill and use as user-project context.

    Returns:
        Structured content dictionary or parsed JSON result.
    """
    token = _get_auth_token()
    proj = _normalize_project_id(project_id)
    headers = {
        "Content-Type": "application/json",
        "X-Goog-User-Project": proj,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000) % 1000000,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }

    try:
        resp = requests.post(MANAGED_BQ_MCP_URL, headers=headers, json=body, timeout=45)
        if resp.status_code != 200:
            return {"error": f"Managed BigQuery MCP returned HTTP {resp.status_code}: {resp.text}"}

        rpc_res = resp.json()
        if "error" in rpc_res:
            return {"error": rpc_res["error"]}

        result = rpc_res.get("result", {})
        if result.get("isError"):
            err_msg = ""
            for content_item in result.get("content", []):
                if content_item.get("type") == "text":
                    err_msg += content_item.get("text", "")
            return {"error": err_msg or "Managed BigQuery MCP returned isError=True"}

        # First check text content which contains serialized JSON from Managed BigQuery MCP
        for content_item in result.get("content", []):
            if content_item.get("type") == "text":
                text_val = content_item.get("text", "")
                try:
                    return json.loads(text_val)
                except Exception:
                    return {"text": text_val}

        if "structuredContent" in result and result["structuredContent"]:
            return result["structuredContent"]

        return result
    except Exception as e:
        return {"error": f"Failed calling Managed BigQuery MCP '{tool_name}': {str(e)}"}


@mcp.tool()
def get_current_datetime() -> Dict[str, Any]:
    """Retrieve current system date, year, month, and standard Gregorian calendar periods.

    ALWAYS call this tool when the user asks for relative calendar date ranges such as
    'today', 'last quarter', 'this quarter', 'last month', 'YTD', or 'last year'.
    Never guess or hardcode dates from obsolete years (e.g. 2023 or 2024).
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    current_year = now.year
    current_month = now.month
    current_calendar_quarter = (current_month - 1) // 3 + 1

    if current_calendar_quarter > 1:
        prev_calendar_quarter = current_calendar_quarter - 1
        prev_calendar_quarter_year = current_year
    else:
        prev_calendar_quarter = 4
        prev_calendar_quarter_year = current_year - 1

    quarter_dates = {
        1: ("01-01", "03-31"),
        2: ("04-01", "06-30"),
        3: ("07-01", "09-30"),
        4: ("10-01", "12-31"),
    }
    prev_start = f"{prev_calendar_quarter_year}-{quarter_dates[prev_calendar_quarter][0]}"
    prev_end = f"{prev_calendar_quarter_year}-{quarter_dates[prev_calendar_quarter][1]}"
    curr_start = f"{current_year}-{quarter_dates[current_calendar_quarter][0]}"
    curr_end = f"{current_year}-{quarter_dates[current_calendar_quarter][1]}"

    return {
        "current_timestamp_utc": now.isoformat(),
        "current_date": now.strftime("%Y-%m-%d"),
        "current_year": current_year,
        "current_month": current_month,
        "current_calendar_quarter": f"Q{current_calendar_quarter} {current_year}",
        "current_calendar_quarter_range": f"{curr_start} to {curr_end}",
        "last_completed_calendar_quarter": f"Q{prev_calendar_quarter} {prev_calendar_quarter_year}",
        "last_completed_calendar_quarter_range": f"{prev_start} to {prev_end}",
        "sql_filter_recommendations": {
            "last_completed_quarter": f"BETWEEN '{prev_start}' AND '{prev_end}'",
            "current_quarter": f"BETWEEN '{curr_start}' AND '{now.strftime('%Y-%m-%d')}'",
            "current_year": f"EXTRACT(YEAR FROM created_at) = {current_year}",
        },
    }


@mcp.tool()
def list_datasets(project_id: Optional[str] = None) -> str:
    """Lists available BigQuery datasets in a Google Cloud project via Managed BigQuery MCP.

    Args:
        project_id: GCP project ID (default: current project, e.g. opm-looker-core-demo-instance).
    """
    proj = _normalize_project_id(project_id)
    res = _call_managed_bq_mcp("list_dataset_ids", {"projectId": proj, "pageSize": 50}, project_id=proj)

    if "error" not in res:
        raw_datasets = res.get("datasets", [])
        datasets = []
        for d in raw_datasets:
            did = d.get("id", "")
            if ":" in did:
                did = did.split(":")[-1]
            datasets.append(did)

        return json.dumps({
            "project": proj,
            "datasets": datasets,
            "source": "https://bigquery.googleapis.com/mcp (list_dataset_ids)",
        }, indent=2)

    # Resilient fallback: BigQuery REST API
    token = _get_auth_token()
    headers = {"Content-Type": "application/json", "X-Goog-User-Project": proj}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{proj}/datasets?maxResults=50"
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            d_list = [d.get("datasetReference", {}).get("datasetId") for d in resp.json().get("datasets", [])]
            return json.dumps({
                "project": proj,
                "datasets": d_list,
                "source": "bigquery_rest_fallback",
            }, indent=2)
    except Exception:
        pass

    return json.dumps({"error": res["error"]})


@mcp.tool()
def list_tables(dataset_id: str = "thelook_ecommerce", project_id: Optional[str] = None) -> str:
    """Lists tables available in a BigQuery dataset via Managed BigQuery MCP.

    Args:
        dataset_id: The BigQuery dataset ID (default: 'thelook_ecommerce').
        project_id: The project containing the dataset (default: current project, e.g. opm-looker-core-demo-instance).
    """
    proj = _normalize_project_id(project_id)
    res = _call_managed_bq_mcp("list_table_ids", {
        "projectId": proj,
        "datasetId": dataset_id,
        "pageSize": 50,
    }, project_id=proj)

    if "error" not in res:
        raw_tables = res.get("tables", [])
        tables = []
        for t in raw_tables:
            tid = t.get("id", "")
            if "." in tid:
                tid = tid.split(".")[-1]
            elif ":" in tid:
                tid = tid.split(":")[-1]
            tables.append(tid)

        return json.dumps({
            "project": proj,
            "dataset": dataset_id,
            "tables": tables,
            "source": "https://bigquery.googleapis.com/mcp (list_table_ids)",
        }, indent=2)

    # Resilient fallback: BigQuery REST API
    token = _get_auth_token()
    headers = {"Content-Type": "application/json", "X-Goog-User-Project": proj}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{proj}/datasets/{dataset_id}/tables?maxResults=50"
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            t_list = [t.get("tableReference", {}).get("tableId") for t in resp.json().get("tables", [])]
            return json.dumps({
                "project": proj,
                "dataset": dataset_id,
                "tables": t_list,
                "source": "bigquery_rest_fallback",
            }, indent=2)
    except Exception:
        pass

    return json.dumps({"error": res["error"]})


@mcp.tool()
def get_table_schema(
    table_id: str,
    dataset_id: str = "thelook_ecommerce",
    project_id: Optional[str] = None,
) -> str:
    """Gets the column names and data types for a BigQuery table via Managed BigQuery MCP.

    Args:
        table_id: Name of the table (e.g., 'order_items', 'users', 'products', 'orders').
        dataset_id: Dataset ID (default: 'thelook_ecommerce').
        project_id: Project ID (default: current project, e.g. opm-looker-core-demo-instance).
    """
    proj = _normalize_project_id(project_id)
    res = _call_managed_bq_mcp("get_table_info", {
        "projectId": proj,
        "datasetId": dataset_id,
        "tableId": table_id,
    }, project_id=proj)

    if "error" not in res:
        schema_fields = res.get("schema", {}).get("fields", [])
        fields = [
            {"name": f.get("name"), "type": f.get("type"), "mode": f.get("mode", "NULLABLE")}
            for f in schema_fields
        ]

        return json.dumps({
            "table": f"{proj}.{dataset_id}.{table_id}",
            "columns": fields,
            "numRows": res.get("numRows"),
            "source": "https://bigquery.googleapis.com/mcp (get_table_info)",
        }, indent=2)

    # Resilient fallback: BigQuery REST API
    token = _get_auth_token()
    headers = {"Content-Type": "application/json", "X-Goog-User-Project": proj}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{proj}/datasets/{dataset_id}/tables/{table_id}"
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            table_info = resp.json()
            schema_fields = table_info.get("schema", {}).get("fields", [])
            fields = [
                {"name": f.get("name"), "type": f.get("type"), "mode": f.get("mode", "NULLABLE")}
                for f in schema_fields
            ]
            return json.dumps({
                "table": f"{proj}.{dataset_id}.{table_id}",
                "columns": fields,
                "numRows": table_info.get("numRows"),
                "source": "bigquery_rest_fallback",
            }, indent=2)
    except Exception:
        pass

    return json.dumps({"error": res["error"]})


@mcp.tool()
def execute_bigquery_sql(sql_query: str, project_id: Optional[str] = None) -> str:
    """Executes a GoogleSQL read-only query against BigQuery via Managed BigQuery MCP.

    Args:
        sql_query: The GoogleSQL SELECT query to execute.
        project_id: GCP Project ID to bill for execution (defaults to current project).
    """
    proj = _normalize_project_id(project_id)
    clean_sql = sql_query.strip().rstrip(";")
    last_error = ""

    # 1. Primary: Official Managed BigQuery MCP service
    res = _call_managed_bq_mcp("execute_sql_readonly", {
        "projectId": proj,
        "query": clean_sql,
    }, project_id=proj)

    if "error" not in res:
        schema_fields = [f.get("name") for f in res.get("schema", {}).get("fields", [])]
        raw_rows = res.get("rows", [])
        rows = []
        for r in raw_rows:
            row_cells = r.get("f", [])
            values = [c.get("v") for c in row_cells]
            if schema_fields:
                rows.append(dict(zip(schema_fields, values)))
            else:
                rows.append(values)

        return json.dumps({
            "status": "SUCCESS",
            "totalRows": str(len(rows)),
            "rows": rows,
            "sql_executed": clean_sql,
            "source": "https://bigquery.googleapis.com/mcp (execute_sql_readonly)",
        }, default=str, indent=2)

    last_error = str(res["error"])

    # 2. Resilient fallback: BigQuery REST API if MCP reports transient or formatting error
    token = _get_auth_token()
    headers = {
        "Content-Type": "application/json",
        "X-Goog-User-Project": proj,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{proj}/queries"
        resp = requests.post(
            url,
            headers=headers,
            json={"query": clean_sql, "useLegacySql": False, "maxResults": 1000},
            timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()
            if "errors" not in data:
                schema_fields = [f["name"] for f in data.get("schema", {}).get("fields", [])]
                rows = []
                for row in data.get("rows", []):
                    values = [cell.get("v") for cell in row.get("f", [])]
                    rows.append(dict(zip(schema_fields, values)))

                return json.dumps({
                    "status": "SUCCESS",
                    "totalRows": str(len(rows)),
                    "rows": rows,
                    "sql_executed": clean_sql,
                    "source": "bigquery_rest_fallback",
                }, default=str, indent=2)
    except Exception:
        pass

    return json.dumps({
        "status": "ERROR",
        "error": last_error,
        "sql_attempted": clean_sql,
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
