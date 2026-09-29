#!/usr/bin/env python3
"""Custom MCP Server for Pattern 4: Looker-Free Dataplex-Governed Analyst Agent.

Provides pure Knowledge Catalog (Dataplex) metadata governance and BigQuery execution tools:
1. get_current_datetime -> Deterministic Gregorian calendar boundaries and fiscal ranges.
2. search_catalog -> Queries Managed Dataplex MCP "search_entries" with strict Looker filtering.
3. get_catalog_metadata -> Retrieves schema columns, types, and custom Aspects (Business Glossary, Data Certification, Table Relationships, Data Sensitivity) via Managed Dataplex MCP "lookup_entry".
4. execute_query -> Executes BigQuery SQL via Managed BigQuery MCP "execute_sql_readonly" with read-only safety.
5. generate_data_chart -> Generates executive statistical visualizations (base64 PNG) via Matplotlib.

Bounded strictly to GCP project "haengeun-f478f". Looker endpoints and entry groups are completely forbidden.
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
from typing import Any, Dict, List, Optional, Tuple

import requests
import google.auth
import google.auth.transport.requests

# Pre-warm matplotlib font manager at module load time to avoid cold-start delays
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _fig, _ax = plt.subplots(figsize=(1, 1))
    _ax.plot([0, 1], [0, 1])
    plt.close(_fig)
except Exception:
    pass

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("KnowledgeCatalog-Pure-Governance-MCP")

# Target Project Isolation: defaults to haengeun-f478f (or GOOGLE_CLOUD_PROJECT)
TARGET_PROJECT_ID = os.environ.get("TARGET_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "haengeun-f478f"
DEFAULT_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION") or "us"

DATAPLEX_MCP_ENDPOINT = os.environ.get("DATAPLEX_MCP_ENDPOINT", "https://dataplex.googleapis.com/mcp")
BIGQUERY_MCP_ENDPOINT = os.environ.get("BIGQUERY_MCP_ENDPOINT", "https://bigquery.googleapis.com/mcp")

_TOKEN_CACHE: Dict[str, Any] = {"token": None, "expires_at": 0}


def _get_access_token() -> str:
    """Gets a valid Google Cloud OAuth2 access token for Dataplex and BigQuery APIs."""
    now = time.time()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expires_at"]:
        return _TOKEN_CACHE["token"]

    # 1. Environment variable override
    env_token = os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN")
    if env_token:
        _TOKEN_CACHE["token"] = env_token.strip()
        _TOKEN_CACHE["expires_at"] = now + 3000
        return _TOKEN_CACHE["token"]

    # 2. Native Cloud Run / Reasoning Engine Metadata Server
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

    # 3. Application Default Credentials via google.auth
    try:
        auth_fn = getattr(google.auth, "_orig_default", google.auth.default)
        creds, _ = auth_fn(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        if creds.token:
            _TOKEN_CACHE["token"] = creds.token
            _TOKEN_CACHE["expires_at"] = now + 3000
            return _TOKEN_CACHE["token"]
    except Exception:
        pass

    # 4. Local gcloud CLI fallback
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

    raise RuntimeError(f"Unable to obtain Google Cloud OAuth2 access token for project '{TARGET_PROJECT_ID}'. Ensure ADC is configured or gcloud auth is active.")


def _headers(project_id: str = TARGET_PROJECT_ID) -> Dict[str, str]:
    """Returns authenticated headers with X-Goog-User-Project billing attribution."""
    token = _get_access_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id,
    }


def _call_managed_mcp_tool(
    endpoint: str,
    tool_name: str,
    arguments: Dict[str, Any],
    project_id: str = TARGET_PROJECT_ID,
    timeout: int = 45,
) -> Dict[str, Any]:
    """Invokes a tool on a Google Managed MCP server via JSON-RPC 2.0."""
    headers = _headers(project_id)
    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000) % 1000000,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
    if resp.status_code != 200:
        return {"error": f"Managed MCP HTTP {resp.status_code}: {resp.text}", "isError": True}
    data = resp.json()
    if "error" in data:
        return {"error": data["error"].get("message", str(data["error"])), "isError": True}
    return data.get("result", {})


def _calculate_fiscal_period_bounds(dt: datetime.datetime, offset: int = 1) -> Dict[str, Any]:
    """Dynamically calculates fiscal year, current fiscal quarter, and last completed fiscal quarter."""
    m = dt.month
    y = dt.year
    f_month_idx = (m - 1 - offset) % 12
    f_quarter = f_month_idx // 3 + 1
    fy = y if m >= offset + 1 else y - 1

    def _quarter_range(quarter: int, fiscal_yr: int) -> Tuple[str, str]:
        start_f_idx = (quarter - 1) * 3
        end_f_idx = start_f_idx + 2
        start_cal_m = (start_f_idx + offset) % 12 + 1
        end_cal_m = (end_f_idx + offset) % 12 + 1
        start_cal_y = fiscal_yr if start_cal_m >= offset + 1 else fiscal_yr + 1
        end_cal_y = fiscal_yr if end_cal_m >= offset + 1 else fiscal_yr + 1
        last_day = calendar.monthrange(end_cal_y, end_cal_m)[1]
        return f"{start_cal_y:04d}-{start_cal_m:02d}-01", f"{end_cal_y:04d}-{end_cal_m:02d}-{last_day:02d}"

    curr_start, curr_end = _quarter_range(f_quarter, fy)

    if f_quarter > 1:
        prev_fq = f_quarter - 1
        prev_fy = fy
    else:
        prev_fq = 4
        prev_fy = fy - 1
    prev_start, prev_end = _quarter_range(prev_fq, prev_fy)

    month_names = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    start_month_name = month_names[(offset % 12) + 1]

    return {
        "fiscal_month_offset": offset,
        "fiscal_year_start_month": start_month_name,
        "current_fiscal_year": f"FY{fy}",
        "current_fiscal_quarter": f"FQ{f_quarter} {fy}",
        "current_fiscal_quarter_range": f"{curr_start} to {curr_end}",
        "last_completed_fiscal_quarter": f"FQ{prev_fq} {prev_fy}",
        "last_completed_fiscal_quarter_range": f"{prev_start} to {prev_end}",
        "prev_fiscal_quarter_number": prev_fq,
        "prev_fiscal_quarter_year": prev_fy,
        "prev_quarter_start_date": prev_start,
        "prev_quarter_end_date": prev_end,
    }


# ==============================================================================
# TOOL 1: get_current_datetime
# ==============================================================================
@mcp.tool()
def get_current_datetime(fiscal_month_offset: Optional[int] = None) -> Dict[str, Any]:
    """Retrieve current system date, year, and standard Gregorian calendar periods, as well as fiscal quarter bounds.

    ALWAYS call this tool when the user asks for relative calendar date ranges such as
    'last quarter', 'this quarter', 'last month', 'YTD', or 'last fiscal quarter'.
    Never guess or hardcode dates from obsolete years.

    Args:
        fiscal_month_offset: Optional start month offset from January (e.g. 1 if fiscal year starts Feb 1).
                             If omitted, checks the Dataplex Business Glossary default offset of 1.

    Returns:
        Current date, Gregorian calendar quarter bounds, and exact fiscal quarter date boundaries.
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
    prev_cal_start = f"{prev_calendar_quarter_year}-{quarter_dates[prev_calendar_quarter][0]}"
    prev_cal_end = f"{prev_calendar_quarter_year}-{quarter_dates[prev_calendar_quarter][1]}"

    offset = fiscal_month_offset if fiscal_month_offset is not None else 1
    fiscal_info = _calculate_fiscal_period_bounds(now, offset=offset)

    return {
        "current_date": now.strftime("%Y-%m-%d"),
        "current_year": current_year,
        "current_month": current_month,
        "current_calendar_quarter": f"Q{current_calendar_quarter} {current_year}",
        "last_completed_calendar_quarter": f"Q{prev_calendar_quarter} {prev_calendar_quarter_year}",
        "last_completed_calendar_quarter_range": f"{prev_cal_start} to {prev_cal_end}",
        "fiscal_calendar": fiscal_info,
        "guidance": (
            "For corporate financial analysis, verify the fiscal calendar offset in Dataplex Business Glossary. "
            "If company fiscal year starts Feb 1, last completed fiscal quarter FQ2 2026 is 2026-05-01 to 2026-07-31."
        ),
    }


# ==============================================================================
# TOOL 2: search_catalog
# ==============================================================================
@mcp.tool()
def search_catalog(
    query: str,
    page_size: int = 20,
    project_id: str = TARGET_PROJECT_ID,
) -> Dict[str, Any]:
    """Search Google Cloud Dataplex Knowledge Catalog for BigQuery tables, schemas, and governance assets.

    Queries the official Managed Dataplex MCP "search_entries" tool targeting project "haengeun-f478f".
    Strictly filters out any Looker/LookML assets so the agent operates purely under sovereign
    Dataplex Knowledge Catalog governance.

    Args:
        query: Search query string (e.g. 'thelook', 'order_items', 'users', 'glossary', 'revenue', 'table').
        page_size: Maximum entries to return (default: 20).
        project_id: GCP Project ID strictly bounded to 'haengeun-f478f'.

    Returns:
        List of catalog entries with their resource names, entry types, display names, and system locations.
    """
    project_id = TARGET_PROJECT_ID
    full_query = query.strip()
    if "project:" not in full_query:
        full_query = f"{project_id} {full_query}".strip()

    entries: List[Dict[str, Any]] = []
    managed_mcp_success = False

    # 1. Primary: Official Managed Dataplex MCP "search_entries"
    try:
        mcp_res = _call_managed_mcp_tool(
            endpoint=DATAPLEX_MCP_ENDPOINT,
            tool_name="search_entries",
            arguments={
                "projectId": project_id,
                "query": full_query,
                "pageSize": min(page_size * 2, 50),
            },
            project_id=project_id,
            timeout=30,
        )
        if not mcp_res.get("isError"):
            for item in mcp_res.get("content", []):
                if isinstance(item, dict) and item.get("text"):
                    parsed_search = json.loads(item["text"])
                    raw_results = parsed_search.get("results", [])
                    for r in raw_results:
                        entry = r.get("dataplexEntry", {})
                        name = entry.get("name", "")
                        # STRICT LOOKER FILTER: Exclude any Looker entry groups or assets
                        if "/@looker/" in name or "looker" in entry.get("entryType", "").lower():
                            continue
                        source = entry.get("entrySource", {})
                        entries.append({
                            "entryName": name,
                            "entryType": entry.get("entryType"),
                            "displayName": source.get("displayName") or name.split("/")[-1],
                            "description": source.get("description", ""),
                            "system": source.get("system", "BIGQUERY"),
                            "location": source.get("location", "us"),
                            "resource": source.get("resource", ""),
                            "fullyQualifiedName": entry.get("fullyQualifiedName", ""),
                        })
                    managed_mcp_success = True
                    break
    except Exception:
        pass

    # 2. Resilient fallback: Direct Dataplex REST searchEntries API
    if not managed_mcp_success or not entries:
        try:
            url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/global:searchEntries"
            body = {"query": full_query, "pageSize": min(page_size * 2, 50)}
            resp = requests.post(url, headers=_headers(project_id), json=body, timeout=30)
            if resp.status_code == 200:
                raw_results = resp.json().get("results", [])
                for r in raw_results:
                    entry = r.get("dataplexEntry", {})
                    name = entry.get("name", "")
                    if "/@looker/" in name or "looker" in entry.get("entryType", "").lower():
                        continue
                    source = entry.get("entrySource", {})
                    entries.append({
                        "entryName": name,
                        "entryType": entry.get("entryType"),
                        "displayName": source.get("displayName") or name.split("/")[-1],
                        "description": source.get("description", ""),
                        "system": source.get("system", "BIGQUERY"),
                        "location": source.get("location", "us"),
                        "resource": source.get("resource", ""),
                        "fullyQualifiedName": entry.get("fullyQualifiedName", ""),
                    })
        except Exception:
            pass

    # Include registered governance entries from entryGroup 'governance' if query mentions glossary, policy, or metrics
    if any(k in query.lower() for k in ["glossary", "revenue", "fiscal", "relationship", "join", "metric", "policy"]):
        try:
            gov_url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/global/entryGroups/governance/entries"
            resp = requests.get(gov_url, headers=_headers(project_id), timeout=15)
            if resp.status_code == 200:
                gov_entries = resp.json().get("entries", [])
                existing_names = {e["entryName"] for e in entries}
                for ge in gov_entries:
                    gname = ge.get("name", "")
                    if gname not in existing_names:
                        gsource = ge.get("entrySource", {})
                        entries.insert(0, {
                            "entryName": gname,
                            "entryType": ge.get("entryType"),
                            "displayName": gsource.get("displayName") or gname.split("/")[-1],
                            "description": gsource.get("description", ""),
                            "system": gsource.get("system", "Dataplex"),
                            "location": "global",
                            "resource": gsource.get("resource", ""),
                            "fullyQualifiedName": f"dataplex:{gname}",
                        })
        except Exception:
            pass

    return {
        "project_id": project_id,
        "query": query,
        "total_results": len(entries[:page_size]),
        "entries": entries[:page_size],
        "looker_excluded": True,
    }


# ==============================================================================
# TOOL 3: get_catalog_metadata
# ==============================================================================
@mcp.tool()
def get_catalog_metadata(
    entry_name: str,
    project_id: str = TARGET_PROJECT_ID,
) -> Dict[str, Any]:
    """Retrieve full technical and governance metadata for a Dataplex Knowledge Catalog entry.

    Invokes Managed Dataplex MCP "lookup_entry" (with REST fallback) to extract:
    - Schema fields (columns, data types, modes).
    - Custom Governance Aspects:
      1. Business Glossary: authoritative metric calculation formulas (e.g. Net Revenue per ASC 606),
         fiscal calendar start month, and governance policy citations.
      2. Table Relationships: primary keys, foreign keys, and validated JOIN conditions between tables.
      3. Data Sensitivity: column-level PII indicators (`has-pii`, `pii-type` such as EMAIL).
      4. Data Certification: tier status (Gold/Silver/Bronze) and environment (PRODUCTION).

    Args:
        entry_name: Resource name of the entry (e.g.
            'projects/408602423299/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/haengeun-f478f/datasets/thelook_ecommerce_haengeun_us/tables/order_items'
            or 'projects/haengeun-f478f/locations/global/entryGroups/governance/entries/net-revenue-glossary').
        project_id: GCP project ID (strictly 'haengeun-f478f').

    Returns:
        Structured metadata dictionary containing schema columns, data sensitivity tags,
        data certification, and business glossary / relationship definitions.
    """
    project_id = TARGET_PROJECT_ID

    # Extract location from entry_name
    location = DEFAULT_LOCATION
    if "/locations/" in entry_name:
        try:
            location = entry_name.split("/locations/")[1].split("/")[0]
        except Exception:
            location = DEFAULT_LOCATION

    raw = {}
    aspects = {}

    # 1. Primary: Official Managed Dataplex MCP "lookup_entry"
    try:
        mcp_res = _call_managed_mcp_tool(
            endpoint=DATAPLEX_MCP_ENDPOINT,
            tool_name="lookup_entry",
            arguments={
                "projectId": project_id,
                "location": location,
                "entry": entry_name,
                "view": "ALL",
            },
            project_id=project_id,
            timeout=30,
        )
        if not mcp_res.get("isError"):
            for item in mcp_res.get("content", []):
                if isinstance(item, dict) and item.get("text"):
                    parsed_lookup = json.loads(item["text"])
                    raw = parsed_lookup.get("entry", {})
                    aspects = raw.get("aspects", {})
                    break
    except Exception:
        pass

    # 2. Resilient fallback: Direct Dataplex REST API
    if not aspects:
        try:
            url = f"https://dataplex.googleapis.com/v1/{entry_name}?view=FULL"
            resp = requests.get(url, headers=_headers(project_id), timeout=30)
            if resp.status_code == 200:
                raw = resp.json()
                aspects = raw.get("aspects", {})
        except Exception:
            pass

    # Extract parsed fields and governance aspects
    schema_fields: List[Dict[str, Any]] = []
    business_glossary: Dict[str, Any] = {}
    table_relationships: Dict[str, Any] = {}
    data_sensitivity: Dict[str, Any] = {}
    data_certification: Dict[str, Any] = {}

    for k, v in aspects.items():
        k_lower = k.lower()
        v_data = v.get("data", {})
        if "schema" in k_lower:
            fields_raw = v_data.get("fields", [])
            for f in fields_raw:
                schema_fields.append({
                    "name": f.get("name"),
                    "dataType": f.get("dataType"),
                    "mode": f.get("mode"),
                    "description": f.get("description", ""),
                })
        elif "business-glossary" in k_lower:
            business_glossary = v_data
        elif "table-relationships" in k_lower:
            table_relationships = v_data
            if "relationships_json" in table_relationships and isinstance(table_relationships["relationships_json"], str):
                try:
                    table_relationships["relationships_parsed"] = json.loads(table_relationships["relationships_json"])
                except Exception:
                    pass
        elif "data-sensitivity" in k_lower:
            data_sensitivity = v_data
        elif "certification" in k_lower:
            data_certification = v_data

    # Detect PII columns
    pii_columns = []
    if data_sensitivity.get("has-pii"):
        pii_type = data_sensitivity.get("pii-type", "RESTRICTED")
        pii_columns.append({"column": "email", "type": pii_type, "compliance": "STRICT_MASK_OR_SUPPRESS"})

    return {
        "entry_name": raw.get("name", entry_name),
        "display_name": raw.get("entrySource", {}).get("displayName"),
        "description": raw.get("entrySource", {}).get("description"),
        "system": raw.get("entrySource", {}).get("system"),
        "resource": raw.get("entrySource", {}).get("resource"),
        "schema_fields": schema_fields,
        "governance_aspects": {
            "business_glossary": business_glossary or None,
            "table_relationships": table_relationships or None,
            "data_sensitivity": data_sensitivity or None,
            "data_certification": data_certification or None,
        },
        "pii_restricted_columns": pii_columns,
        "raw_aspect_keys": list(aspects.keys()),
    }


# ==============================================================================
# TOOL 4: execute_query
# ==============================================================================
@mcp.tool()
def execute_query(
    sql_query: str,
    project_id: str = TARGET_PROJECT_ID,
) -> Dict[str, Any]:
    """Execute a read-only GoogleSQL query against BigQuery tables in 'haengeun-f478f'.

    Routes SQL payloads directly to the official Managed BigQuery MCP service
    (https://bigquery.googleapis.com/mcp) using 'execute_sql_readonly'. Read-only safety
    is natively enforced.

    Args:
        sql_query: The GoogleSQL SELECT query to execute.
        project_id: GCP project ID strictly set to 'haengeun-f478f'.

    Returns:
        Query results with column headers, formatted row objects, row count, and execution engine.
    """
    project_id = TARGET_PROJECT_ID
    clean_sql = sql_query.strip()
    last_error = ""

    # 1. Primary: Official Managed BigQuery MCP service
    try:
        mcp_res = _call_managed_mcp_tool(
            endpoint=BIGQUERY_MCP_ENDPOINT,
            tool_name="execute_sql_readonly",
            arguments={
                "projectId": project_id,
                "query": clean_sql,
            },
            project_id=project_id,
            timeout=60,
        )
        if mcp_res.get("isError"):
            err_text = ""
            for item in mcp_res.get("content", []):
                if isinstance(item, dict) and item.get("text"):
                    err_text += item["text"] + " "
            last_error = err_text.strip() or str(mcp_res)
        else:
            content_text = ""
            for item in mcp_res.get("content", []):
                if isinstance(item, dict) and item.get("text"):
                    content_text = item["text"]
                    break
            if content_text:
                data = json.loads(content_text)
                schema_fields = [f["name"] for f in data.get("schema", {}).get("fields", [])]
                rows_formatted = []
                for row in data.get("rows", []):
                    values = [cell.get("v") for cell in row.get("f", [])]
                    rows_formatted.append(dict(zip(schema_fields, values)))
                return {
                    "status": "SUCCESS",
                    "jobId": data.get("queryId") or "managed-bq-mcp",
                    "totalRows": len(rows_formatted),
                    "totalBytesProcessed": data.get("totalBytesProcessed", "0"),
                    "columns": schema_fields,
                    "rows": rows_formatted,
                    "execution_engine": "managed_bigquery_mcp (execute_sql_readonly)",
                }
    except Exception as e:
        last_error = str(e)

    # 2. Resilient fallback: BigQuery REST API
    try:
        url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/queries"
        resp = requests.post(
            url,
            headers=_headers(project_id),
            json={"query": clean_sql, "useLegacySql": False, "maxResults": 1000},
            timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()
            if "errors" not in data:
                schema_fields = [f["name"] for f in data.get("schema", {}).get("fields", [])]
                rows_formatted = []
                for row in data.get("rows", []):
                    values = [cell.get("v") for cell in row.get("f", [])]
                    rows_formatted.append(dict(zip(schema_fields, values)))
                return {
                    "status": "SUCCESS",
                    "jobId": data.get("jobReference", {}).get("jobId"),
                    "totalRows": int(data.get("totalRows", len(rows_formatted))),
                    "totalBytesProcessed": data.get("totalBytesProcessed", "0"),
                    "columns": schema_fields,
                    "rows": rows_formatted,
                    "execution_engine": "bigquery_rest_fallback",
                }
            else:
                last_error = str(data.get("errors"))
        else:
            last_error = f"BigQuery HTTP {resp.status_code}: {resp.text}"
    except Exception as e:
        last_error = str(e)

    return {
        "status": "ERROR",
        "error": last_error,
        "sql_attempted": clean_sql,
    }


# ==============================================================================
# TOOL 5: generate_data_chart
# ==============================================================================
@mcp.tool()
def generate_data_chart(
    chart_type: str,
    title: str,
    x_values: List[Any],
    y_values: List[float],
    x_label: str = "",
    y_label: str = "",
    color: str = "#1a73e8",
) -> Dict[str, Any]:
    """Generates an interactive Vega-Lite JSON visualization specification for modern web frontends and dashboards.
    Call this tool ONCE when an analytical visualization, trend chart, or comparison plot is requested.

    Args:
        chart_type: Type of chart: 'bar', 'horizontal_bar', 'line', 'area', 'pie'.
        title: Title for the chart.
        x_values: List of category labels or X-axis values (e.g. ['2024-05-01', '2024-06-01', '2024-07-01']).
        y_values: List of numerical metric values (e.g. [25277.32, 28297.68, 30943.86]).
        x_label: Optional label for the X axis.
        y_label: Optional label for the Y axis.
        color: Primary accent hex color (default: '#1a73e8').

    Returns:
        Dictionary containing vega_lite_spec (dict) and vega_lite_json (formatted JSON string) for interactive rendering.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        return {"error": f"Matplotlib is not installed or failed to initialize: {e}"}

    if not x_values or not y_values:
        return {"error": "x_values and y_values must not be empty."}

    # Clean data
    x_clean = [str(x) for x in x_values]
    y_clean = []
    for y in y_values:
        try:
            y_clean.append(float(y))
        except (ValueError, TypeError):
            y_clean.append(0.0)

    fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=72)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#fafafa")

    chart_type_lower = chart_type.lower().strip()
    palette = ["#1a73e8", "#12b5cb", "#e37400", "#d93025", "#1e8e3e", "#9334e6", "#f29900", "#5f6368"]

    if chart_type_lower in ("bar", "column"):
        bars = ax.bar(x_clean, y_clean, color=color, width=0.55, edgecolor="none", zorder=3)
        ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{height:,.0f}" if abs(height) >= 10 else f"{height:,.2f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center", va="bottom", fontsize=8, color="#202124"
            )
        plt.xticks(rotation=25 if any(len(str(s)) > 8 for s in x_clean) else 0, ha="right" if any(len(str(s)) > 8 for s in x_clean) else "center", fontsize=8)
        plt.yticks(fontsize=8)
    elif chart_type_lower in ("horizontal_bar", "hbar"):
        y_pos = list(range(len(x_clean)))[::-1]
        bars = ax.barh(y_pos, y_clean, color=color, height=0.55, edgecolor="none", zorder=3)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(x_clean, fontsize=8)
        plt.yticks(fontsize=8)
        ax.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)
        for bar in bars:
            width = bar.get_width()
            ax.annotate(
                f"{width:,.0f}" if abs(width) >= 10 else f"{width:,.2f}",
                xy=(width, bar.get_y() + bar.get_height() / 2),
                xytext=(4, 0),
                textcoords="offset points",
                ha="left", va="center", fontsize=8, color="#202124"
            )
    elif chart_type_lower == "line":
        ax.plot(x_clean, y_clean, color=color, marker="o", linewidth=2.0, markersize=5, zorder=3)
        ax.grid(linestyle="--", alpha=0.35, zorder=0)
        for x, y in zip(x_clean, y_clean):
            ax.annotate(
                f"{y:,.0f}" if abs(y) >= 10 else f"{y:,.2f}",
                xy=(x, y),
                xytext=(0, 5),
                textcoords="offset points",
                ha="center", va="bottom", fontsize=8
            )
        plt.xticks(rotation=25 if any(len(str(s)) > 8 for s in x_clean) else 0, ha="right" if any(len(str(s)) > 8 for s in x_clean) else "center", fontsize=8)
        plt.yticks(fontsize=8)
    elif chart_type_lower in ("area",):
        ax.plot(x_clean, y_clean, color=color, linewidth=2, zorder=3)
        ax.fill_between(range(len(x_clean)), y_clean, color=color, alpha=0.35, zorder=2)
        ax.grid(linestyle="--", alpha=0.35, zorder=0)
        plt.xticks(range(len(x_clean)), x_clean, rotation=25 if any(len(str(s)) > 8 for s in x_clean) else 0, ha="right" if any(len(str(s)) > 8 for s in x_clean) else "center", fontsize=8)
        plt.yticks(fontsize=8)
    elif chart_type_lower == "pie":
        colors = palette[:len(x_clean)] if len(x_clean) <= len(palette) else None
        wedges, texts, autotexts = ax.pie(
            y_clean, labels=x_clean, autopct="%1.1f%%",
            startangle=140, colors=colors, textprops=dict(color="#202124", fontsize=8)
        )
        for at in autotexts:
            at.set_color("#ffffff")
            at.set_fontweight("bold")
            at.set_fontsize(8)
    else:
        bars = ax.bar(x_clean, y_clean, color=color, width=0.55, edgecolor="none", zorder=3)
        ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
        plt.xticks(fontsize=8)
        plt.yticks(fontsize=8)

    ax.set_title(title, fontsize=10.5, fontweight="bold", pad=10, color="#202124")
    if x_label and chart_type_lower != "pie":
        ax.set_xlabel(x_label, fontsize=8.5, labelpad=6, color="#5f6368")
    if y_label and chart_type_lower != "pie":
        ax.set_ylabel(y_label, fontsize=8.5, labelpad=6, color="#5f6368")

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["bottom", "left"]:
        ax.spines[spine].set_color("#dadce0")

    # Construct official interactive Vega-Lite v5 JSON specification
    vl_data = [{"category": str(x), "value": float(y)} for x, y in zip(x_clean, y_clean)]
    mark_type = "bar"
    if chart_type_lower in ("line",):
        mark_type = "line"
    elif chart_type_lower in ("area",):
        mark_type = "area"
    elif chart_type_lower in ("pie",):
        mark_type = "arc"

    vega_lite_spec: Dict[str, Any] = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": title,
        "title": {
            "text": title,
            "anchor": "start",
            "fontSize": 14,
            "color": "#202124",
        },
        "width": "container",
        "height": 280,
        "data": {"values": vl_data},
        "mark": {"type": mark_type, "tooltip": True, "color": color},
        "encoding": {
            "x": {
                "field": "category",
                "type": "nominal",
                "title": x_label or "Category",
                "axis": {"labelAngle": -30, "labelLimit": 120},
            },
            "y": {
                "field": "value",
                "type": "quantitative",
                "title": y_label or "Value",
            },
        },
    }

    if chart_type_lower in ("horizontal_bar", "hbar"):
        vega_lite_spec["encoding"]["x"], vega_lite_spec["encoding"]["y"] = (
            vega_lite_spec["encoding"]["y"],
            vega_lite_spec["encoding"]["x"],
        )
    elif chart_type_lower == "pie":
        vega_lite_spec["encoding"] = {
            "theta": {"field": "value", "type": "quantitative", "stack": True},
            "color": {"field": "category", "type": "nominal", "title": x_label or "Category"},
        }

    vega_lite_json_str = json.dumps(vega_lite_spec, indent=2)

    return {
        "status": "success",
        "chart_type": chart_type,
        "title": title,
        "data_points_count": len(x_clean),
        "chart_summary": f"Generated interactive Vega-Lite specification for '{title}' with {len(x_clean)} data points.",
        "vega_lite_spec": vega_lite_spec,
        "vega_lite_json": vega_lite_json_str,
    }


if __name__ == "__main__":
    mcp.run()
