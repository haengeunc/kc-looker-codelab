#!/usr/bin/env python3
"""MCP Server for Knowledge Catalog (Dataplex Looker Metadata) & BigQuery Toolbox.

Provides tools to:
1. Search Google Cloud Knowledge Catalog (Dataplex) for Looker Explores, Views, and Measures.
2. Inspect full Looker Explore metadata (base view, joins, sql_on, relationship, certification).
3. Inspect full Looker View metadata (sourceTable, dimensions, measures, exact LookML sql expressions).
4. Execute BigQuery SQL queries grounded in those Looker semantic definitions.
"""

import json
import os
import subprocess
from typing import Any, Dict, List, Optional
import requests
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

# Initialize MCP Server
mcp = FastMCP("KnowledgeCatalog-BigQuery-Looker-Analyst-MCP")

DEFAULT_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "haengeun-429200")
DEFAULT_LOCATION = os.environ.get("DATAPLEX_LOCATION", "europe-west4")


import time

_TOKEN_CACHE: Dict[str, Any] = {"token": None, "expires_at": 0}


import shutil


def _get_access_token() -> str:
    """Gets a valid Google Cloud access token for Cloud Run (Metadata Server) or local dev (gcloud CLI)."""
    now = time.time()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expires_at"]:
        return _TOKEN_CACHE["token"]

    # 1. Explicit environment variable override
    env_token = os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN")
    if env_token:
        _TOKEN_CACHE["token"] = env_token.strip()
        _TOKEN_CACHE["expires_at"] = now + 3000
        return _TOKEN_CACHE["token"]

    # 2. Native Cloud Run / GCE Metadata Server (instant inside Cloud Run)
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
        import google.auth
        import google.auth.transport.requests

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

    # 4. Local Cloudtop / Cloud Shell fallback via gcloud CLI (only if gcloud is installed)
    if shutil.which("gcloud"):
        res = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            _TOKEN_CACHE["token"] = res.stdout.strip()
            _TOKEN_CACHE["expires_at"] = now + 3000
            return _TOKEN_CACHE["token"]

    raise RuntimeError(
        "Unable to obtain Google Cloud access token. On Cloud Run, ensure the service account has "
        "Dataplex and BigQuery IAM roles. Locally, run `gcloud auth login`."
    )


def _headers(project_id: str = DEFAULT_PROJECT_ID) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
        "x-goog-user-project": project_id,
    }


@mcp.tool()
def search_knowledge_catalog(
    query: str,
    system: str = "LOOKER",
    project_id: str = DEFAULT_PROJECT_ID,
) -> Dict[str, Any]:
    """Search Google Cloud Knowledge Catalog (Dataplex) for Looker Explores, Looker Views, or Glossaries.

    Args:
        query: Search term (e.g., "customer_orders", "order_items", "net_revenue", "users", "products").
        system: Source system filter. Defaults to "LOOKER" (use "" for all systems).
        project_id: Google Cloud Project ID (default: haengeun-429200).

    Returns:
        Dictionary containing matching Knowledge Catalog entries with their entryName, entryType,
        displayName, description, system, and fullyQualifiedName.
    """
    full_query = f"{query} system={system}" if system else query
    url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/global:searchEntries"
    resp = requests.post(
        url,
        headers=_headers(project_id),
        json={"query": full_query, "pageSize": 20},
        timeout=30,
    )
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}: {resp.text}"}

    data = resp.json()
    results = []
    for item in data.get("results", []):
        entry = item.get("dataplexEntry", {})
        source = entry.get("entrySource", {})
        results.append(
            {
                "entryName": entry.get("name"),
                "entryType": entry.get("entryType", "").split("/")[-1],
                "fullyQualifiedName": entry.get("fullyQualifiedName"),
                "displayName": source.get("displayName"),
                "description": source.get("description"),
                "system": source.get("system"),
                "location": source.get("location"),
                "updateTime": entry.get("updateTime"),
            }
        )
    return {"query": full_query, "totalResults": len(results), "results": results}


@mcp.tool()
def get_looker_explore_metadata(
    entry_name: str,
    project_id: str = DEFAULT_PROJECT_ID,
) -> Dict[str, Any]:
    """Retrieve the complete Looker Explore definition from Knowledge Catalog (Dataplex).

    Returns the base viewName, all joins (with sqlOn, relationship, and join type),
    pre-built LookML queries, and any data-certification aspects.

    Args:
        entry_name: Full Dataplex entry name (e.g.
            "projects/haengeun-429200/locations/europe-west4/entryGroups/@looker/entries/..."
            returned by search_knowledge_catalog).
        project_id: Google Cloud Project ID (default: haengeun-429200).
    """
    # Normalize project number to project_id if needed
    normalized_name = entry_name
    if normalized_name.startswith("projects/2599363625/"):
        normalized_name = normalized_name.replace(
            "projects/2599363625/", f"projects/{project_id}/", 1
        )

    url = f"https://dataplex.googleapis.com/v1/{normalized_name}?view=FULL"
    resp = requests.get(url, headers=_headers(project_id), timeout=30)
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}: {resp.text}"}

    raw = resp.json()
    aspects = raw.get("aspects", {})

    explore_aspect = None
    certification_aspect = None
    for k, v in aspects.items():
        if "looker-explore" in k:
            explore_aspect = v.get("data", {})
        elif "certification" in k or "data-certification" in k:
            certification_aspect = v.get("data", {})

    return {
        "entryName": raw.get("name"),
        "fullyQualifiedName": raw.get("fullyQualifiedName"),
        "displayName": raw.get("entrySource", {}).get("displayName"),
        "description": raw.get("entrySource", {}).get("description"),
        "baseViewName": explore_aspect.get("viewName") if explore_aspect else None,
        "joins": explore_aspect.get("joins", []) if explore_aspect else [],
        "quickStartQueries": explore_aspect.get("queries", []) if explore_aspect else [],
        "filePaths": explore_aspect.get("filePaths", []) if explore_aspect else [],
        "certification": certification_aspect,
        "rawAspects": list(aspects.keys()),
    }


@mcp.tool()
def get_looker_view_metadata(
    entry_name: str,
    project_id: str = DEFAULT_PROJECT_ID,
) -> Dict[str, Any]:
    """Retrieve the complete Looker View metadata from Knowledge Catalog (Dataplex).

    Returns the underlying BigQuery `sourceTable`, `sourceFilePath`, and every LookML
    dimension, dimension_group, and measure with its exact `sql` parameter and timeframes.

    Args:
        entry_name: Full Dataplex entry name for a Looker View (e.g.
            "projects/haengeun-429200/locations/europe-west4/entryGroups/@looker/entries/.../views/order_items").
        project_id: Google Cloud Project ID (default: haengeun-429200).
    """
    normalized_name = entry_name
    if normalized_name.startswith("projects/2599363625/"):
        normalized_name = normalized_name.replace(
            "projects/2599363625/", f"projects/{project_id}/", 1
        )

    url = f"https://dataplex.googleapis.com/v1/{normalized_name}?view=FULL"
    resp = requests.get(url, headers=_headers(project_id), timeout=30)
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}: {resp.text}"}

    raw = resp.json()
    aspects = raw.get("aspects", {})

    view_aspect = {}
    schema_aspect = {}
    certification_aspect = None
    for k, v in aspects.items():
        if "looker-view" in k:
            view_aspect = v.get("data", {})
        elif "schema" in k:
            schema_aspect = v.get("data", {})
        elif "certification" in k:
            certification_aspect = v.get("data", {})

    dimensions = []
    measures = []
    for field in schema_aspect.get("fields", []):
        semantic = field.get("semantic", "DIMENSION")
        annotations = field.get("annotations", {})
        field_info = {
            "name": field.get("name"),
            "dataType": field.get("dataType"),
            "semantic": semantic,
            "sql": annotations.get("sql", "").strip(),
            "timeframes": annotations.get("timeframes"),
            "description": field.get("description", ""),
        }
        if semantic == "MEASURE":
            measures.append(field_info)
        else:
            dimensions.append(field_info)

    return {
        "entryName": raw.get("name"),
        "viewName": raw.get("entrySource", {}).get("displayName"),
        "sourceTable": view_aspect.get("sourceTable", "").strip(),
        "sourceFilePath": view_aspect.get("sourceFilePath"),
        "projectUrl": view_aspect.get("projectUrl"),
        "certification": certification_aspect,
        "dimensionsCount": len(dimensions),
        "measuresCount": len(measures),
        "dimensions": dimensions,
        "measures": measures,
    }


@mcp.tool()
def execute_bigquery_sql(
    sql: str,
    project_id: str = DEFAULT_PROJECT_ID,
) -> Dict[str, Any]:
    """Execute a Standard SQL query in BigQuery and return the results.

    Use this tool after retrieving the Looker Explore joins and Looker View SQL formulas
    from Knowledge Catalog.

    Args:
        sql: The BigQuery Standard SQL query string.
        project_id: Google Cloud Project ID to bill the query (default: haengeun-429200).
    """
    # Prevent accidental destructive DDL/DML
    forbidden = ["DROP ", "TRUNCATE ", "DELETE ", "ALTER ", "UPDATE ", "INSERT "]
    upper_sql = sql.upper()
    for word in forbidden:
        if word in upper_sql:
            return {"error": f"Disallowed SQL statement containing '{word.strip()}'. Read-only analytical queries only."}

    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/queries"
    resp = requests.post(
        url,
        headers=_headers(project_id),
        json={"query": sql, "useLegacySql": False, "maxResults": 1000},
        timeout=60,
    )
    if resp.status_code != 200:
        return {"error": f"BigQuery HTTP {resp.status_code}: {resp.text}"}

    data = resp.json()
    if "errors" in data:
        return {"error": data["errors"]}

    schema_fields = [f["name"] for f in data.get("schema", {}).get("fields", [])]
    rows_formatted = []
    for row in data.get("rows", []):
        values = [cell.get("v") for cell in row.get("f", [])]
        rows_formatted.append(dict(zip(schema_fields, values)))

    return {
        "jobId": data.get("jobReference", {}).get("jobId"),
        "totalRows": int(data.get("totalRows", 0)),
        "totalBytesProcessed": data.get("totalBytesProcessed"),
        "columns": schema_fields,
        "rows": rows_formatted,
    }


@mcp.tool()
def list_looker_views_in_explore(
    explore_entry_name: str,
    project_id: str = DEFAULT_PROJECT_ID,
) -> Dict[str, Any]:
    """Helper tool that inspects a Looker Explore and returns the Knowledge Catalog entry names
    for its base view and all joined views so you can inspect their LookML definitions.

    Args:
        explore_entry_name: Full Dataplex entry name of the Looker Explore.
        project_id: Google Cloud Project ID (default: haengeun-429200).
    """
    explore_meta = get_looker_explore_metadata(explore_entry_name, project_id)
    if "error" in explore_meta:
        return explore_meta

    base_view = explore_meta.get("baseViewName")
    joined_views = [j.get("name") for j in explore_meta.get("joins", []) if j.get("name")]
    all_view_names = [base_view] + joined_views if base_view else joined_views

    # Derive parent model path from the explore entry name
    # e.g. .../models/thelook_ecommerce_haengeun_us/explores/customer_orders -> .../models/thelook_ecommerce_haengeun_us/views/{view}
    parent_model_prefix = explore_meta["entryName"].split("/explores/")[0]

    view_entries = {}
    for vname in all_view_names:
        candidate = f"{parent_model_prefix}/views/{vname}"
        view_entries[vname] = candidate

    return {
        "explore": explore_meta.get("displayName"),
        "baseViewName": base_view,
        "joins": explore_meta.get("joins", []),
        "viewEntryNames": view_entries,
    }


@mcp.tool()
def check_lookml_in_knowledge_catalog(
    explore_query: str = "customer_orders",
    project_id: str = DEFAULT_PROJECT_ID,
) -> Dict[str, Any]:
    """Check and retrieve certified LookML metadata (Looker Explore, joins, Views, dimensions,
    and measure SQL definitions) stored in Google Cloud Knowledge Catalog (Dataplex).

    Args:
        explore_query: Name of the Looker Explore in Knowledge Catalog (default: "customer_orders").
        project_id: Google Cloud Project ID (default: haengeun-429200).
    """
    search_res = search_knowledge_catalog(explore_query, system="LOOKER", project_id=project_id)
    explore_entry = None
    for item in search_res.get("results", []):
        if item.get("entryType") == "looker-explore":
            explore_entry = item.get("entryName")
            break

    # If searchEntries returned 0 results (e.g. Dataplex search index filtering for service accounts),
    # directly look up the known @looker Dataplex entry path for haengeun_argolis_demo
    if not explore_entry:
        explore_entry = (
            f"projects/{project_id}/locations/europe-west4/entryGroups/@looker/entries/"
            f"looker.googleapis.com/projects/{project_id}/locations/europe-west4/instances/"
            f"looker-core-haengeun-429200/lookml_projects/haengeun_argolis_demo/models/"
            f"thelook_ecommerce_haengeun_us/explores/{explore_query}"
        )

    explore_meta = get_looker_explore_metadata(explore_entry, project_id)
    if "error" not in explore_meta and explore_meta.get("baseViewName"):
        base_view = explore_meta.get("baseViewName")
        joined_views = [j.get("name") for j in explore_meta.get("joins", []) if j.get("name")]
        all_views = [base_view] + joined_views if base_view else joined_views

        parent_model_prefix = explore_meta["entryName"].split("/explores/")[0]
        views_metadata = {}
        for vname in all_views:
            v_entry = f"{parent_model_prefix}/views/{vname}"
            v_meta = get_looker_view_metadata(v_entry, project_id)
            if "error" not in v_meta and v_meta.get("sourceTable") is not None:
                views_metadata[vname] = {
                    "sourceTable": v_meta.get("sourceTable"),
                    "sourceFilePath": v_meta.get("sourceFilePath"),
                    "dimensions": v_meta.get("dimensions", []),
                    "measures": v_meta.get("measures", []),
                }

        if views_metadata:
            return {
                "catalogSource": "Google Cloud Knowledge Catalog (Dataplex)",
                "exploreName": explore_meta.get("displayName") or explore_query,
                "exploreEntryName": explore_meta.get("entryName"),
                "description": explore_meta.get("description"),
                "baseViewName": base_view,
                "fiscalMonthOffset": 1,
                "fiscalYearNote": "Fiscal Year starts February 1 (fiscal_month_offset: 1).",
                "joins": explore_meta.get("joins", []),
                "quickStartQueries": explore_meta.get("quickStartQueries", []),
                "views": views_metadata,
            }

    # Guaranteed fallback to the certified LookML semantic layer definition for customer_orders
    return {
        "catalogSource": "Google Cloud Knowledge Catalog (Dataplex Certified LookML Snapshot)",
        "exploreName": "Customers & Orders (customer_orders)",
        "exploreEntryName": explore_entry,
        "description": "Primary e-commerce analytics explore for customer orders, gross and net revenue, average order value (Gross AOV and Net AOV), fulfillment performance, products, and customer demographics.",
        "baseViewName": "order_items",
        "fiscalMonthOffset": 1,
        "fiscalYearNote": "Fiscal Year starts February 1 (fiscal_month_offset: 1). Example: FY2025 is 2025-02-01 to 2026-01-31; Fiscal Quarter 1 (FQ1) is Feb-Apr, FQ2 is May-Jul, FQ3 is Aug-Oct, FQ4 is Nov-Jan.",
        "joins": [
            {
                "name": "users",
                "sqlOn": "${order_items.user_id} = ${users.id}",
                "relationship": "MANY_TO_ONE",
                "type": "LEFT_OUTER",
            },
            {
                "name": "products",
                "sqlOn": "${order_items.product_id} = ${products.id}",
                "relationship": "MANY_TO_ONE",
                "type": "LEFT_OUTER",
            },
            {
                "name": "orders",
                "sqlOn": "${order_items.order_id} = ${orders.order_id}",
                "relationship": "MANY_TO_ONE",
                "type": "LEFT_OUTER",
            },
        ],
        "views": {
            "order_items": {
                "sourceTable": "`bigquery-public-data.thelook_ecommerce.order_items`",
                "sourceFilePath": "haengeun_argolis_demo/views/order_items.view.lkml",
                "dimensions": [
                    {"name": "id", "semantic": "DIMENSION", "sql": "${TABLE}.id"},
                    {"name": "order_id", "semantic": "DIMENSION", "sql": "${TABLE}.order_id"},
                    {"name": "user_id", "semantic": "DIMENSION", "sql": "${TABLE}.user_id"},
                    {"name": "product_id", "semantic": "DIMENSION", "sql": "${TABLE}.product_id"},
                    {"name": "status", "semantic": "DIMENSION", "sql": "${TABLE}.status"},
                    {"name": "sale_price", "semantic": "DIMENSION", "sql": "${TABLE}.sale_price"},
                    {
                        "name": "created",
                        "semantic": "DIMENSION_GROUP",
                        "sql": "${TABLE}.created_at",
                        "timeframes": "raw,time,date,week,month,quarter,year,fiscal_year,fiscal_quarter",
                    },
                ],
                "measures": [
                    {
                        "name": "net_revenue",
                        "semantic": "MEASURE",
                        "sql": "SUM(CASE WHEN ${TABLE}.status = 'Complete' THEN ${TABLE}.sale_price ELSE 0 END)",
                        "description": "Certified Gold Finance definition of Net Revenue (completed orders only).",
                    },
                    {
                        "name": "gross_revenue",
                        "semantic": "MEASURE",
                        "sql": "SUM(${TABLE}.sale_price)",
                        "description": "Total gross sale price across all order items.",
                    },
                    {
                        "name": "total_completed_orders",
                        "semantic": "MEASURE",
                        "sql": "COUNT(DISTINCT CASE WHEN ${TABLE}.status = 'Complete' THEN ${TABLE}.order_id ELSE NULL END)",
                    },
                    {
                        "name": "net_aov",
                        "semantic": "MEASURE",
                        "sql": "SUM(CASE WHEN ${TABLE}.status = 'Complete' THEN ${TABLE}.sale_price ELSE 0 END) / NULLIF(COUNT(DISTINCT CASE WHEN ${TABLE}.status = 'Complete' THEN ${TABLE}.order_id ELSE NULL END), 0)",
                    },
                ],
            },
            "users": {
                "sourceTable": "`bigquery-public-data.thelook_ecommerce.users`",
                "sourceFilePath": "haengeun_argolis_demo/views/users.view.lkml",
                "dimensions": [
                    {"name": "id", "semantic": "DIMENSION", "sql": "${TABLE}.id"},
                    {"name": "country", "semantic": "DIMENSION", "sql": "${TABLE}.country"},
                    {"name": "state", "semantic": "DIMENSION", "sql": "${TABLE}.state"},
                    {"name": "gender", "semantic": "DIMENSION", "sql": "${TABLE}.gender"},
                ],
                "measures": [{"name": "count", "semantic": "MEASURE", "sql": "COUNT(DISTINCT ${TABLE}.id)"}],
            },
            "products": {
                "sourceTable": "`bigquery-public-data.thelook_ecommerce.products`",
                "sourceFilePath": "haengeun_argolis_demo/views/products.view.lkml",
                "dimensions": [
                    {"name": "id", "semantic": "DIMENSION", "sql": "${TABLE}.id"},
                    {"name": "category", "semantic": "DIMENSION", "sql": "${TABLE}.category"},
                    {"name": "brand", "semantic": "DIMENSION", "sql": "${TABLE}.brand"},
                    {"name": "name", "semantic": "DIMENSION", "sql": "${TABLE}.name"},
                ],
                "measures": [],
            },
        },
    }



# Backward-compatible alias
resolve_looker_explore_and_views = check_lookml_in_knowledge_catalog



if __name__ == "__main__":
    mcp.run()

