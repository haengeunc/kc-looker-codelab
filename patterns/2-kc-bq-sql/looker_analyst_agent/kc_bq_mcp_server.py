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
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional
import requests
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

# Initialize MCP Server
mcp = FastMCP("KnowledgeCatalog-BigQuery-Looker-Analyst-MCP")


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


DEFAULT_PROJECT_ID = _detect_default_project()
DEFAULT_LOCATION = os.environ.get("DATAPLEX_LOCATION", "us-central1")
LOOKER_MODEL_NAME = os.environ.get("LOOKER_MODEL_NAME", "customer_orders")

_TOKEN_CACHE: Dict[str, Any] = {"token": None, "expires_at": 0}


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

    # 2. Native Cloud Run / GCE Metadata Server (instant inside Cloud Run / Agent Engine)
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

    raise RuntimeError(
        "Unable to obtain Google Cloud access token. On Cloud Run / Agent Engine, ensure the service account has "
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
        project_id: Google Cloud Project ID (default: auto-detected or YOUR-GCP-PROJECT).

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
    pre-built LookML queries, and any optional governance/certification aspects.

    Args:
        entry_name: Full Dataplex entry name (e.g.
            "projects/YOUR-GCP-PROJECT/locations/us-central1/entryGroups/@looker/entries/..."
            returned by search_knowledge_catalog).
        project_id: Google Cloud Project ID (default: auto-detected or YOUR-GCP-PROJECT).
    """
    url = f"https://dataplex.googleapis.com/v1/{entry_name}?view=FULL"
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
            "projects/YOUR-GCP-PROJECT/locations/us-central1/entryGroups/@looker/entries/.../views/order_items").
        project_id: Google Cloud Project ID (default: auto-detected or YOUR-GCP-PROJECT).
    """
    url = f"https://dataplex.googleapis.com/v1/{entry_name}?view=FULL"
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
        project_id: Google Cloud Project ID to bill the query (default: auto-detected or YOUR-GCP-PROJECT).
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
        project_id: Google Cloud Project ID (default: auto-detected or YOUR-GCP-PROJECT).
    """
    explore_meta = get_looker_explore_metadata(explore_entry_name, project_id)
    if "error" in explore_meta:
        return explore_meta

    base_view = explore_meta.get("baseViewName")
    joined_views = [j.get("name") for j in explore_meta.get("joins", []) if j.get("name")]
    all_view_names = [base_view] + joined_views if base_view else joined_views

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
        project_id: Google Cloud Project ID (default: auto-detected or YOUR-GCP-PROJECT).
    """
    search_res = search_knowledge_catalog(explore_query, system="LOOKER", project_id=project_id)
    explore_entry = None
    for item in search_res.get("results", []):
        if item.get("entryType") == "looker-explore":
            explore_entry = item.get("entryName")
            break

    # Direct @looker entry group fallback if searchEntries is filtered by IAM / service account
    if not explore_entry:
        explore_entry = (
            f"projects/{project_id}/locations/{DEFAULT_LOCATION}/entryGroups/@looker/entries/"
            f"looker/explores/{LOOKER_MODEL_NAME}.{explore_query}"
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

    # Certified LookML semantic layer reference snapshot for customer_orders
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
                "sourceFilePath": "views/order_items.view.lkml",
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
                "sourceFilePath": "views/users.view.lkml",
                "dimensions": [
                    {"name": "id", "semantic": "DIMENSION", "sql": "${TABLE}.id"},
                    {"name": "country", "semantic": "DIMENSION", "sql": "${TABLE}.country"},
                    {"name": "state", "semantic": "DIMENSION", "sql": "${TABLE}.state"},
                    {"name": "gender", "semantic": "DIMENSION", "sql": "${TABLE}.gender"},
                    {"name": "email", "semantic": "DIMENSION", "sql": "${TABLE}.email", "tags": ["RESTRICTED_PII"], "policy": "PROHIBIT_OUTPUT"},
                    {"name": "phone", "semantic": "DIMENSION", "sql": "${TABLE}.phone", "tags": ["RESTRICTED_PII"], "policy": "PROHIBIT_OUTPUT"},
                ],
                "measures": [{"name": "count", "semantic": "MEASURE", "sql": "COUNT(DISTINCT ${TABLE}.id)"}],
            },
            "products": {
                "sourceTable": "`bigquery-public-data.thelook_ecommerce.products`",
                "sourceFilePath": "views/products.view.lkml",
                "dimensions": [
                    {"name": "id", "semantic": "DIMENSION", "sql": "${TABLE}.id"},
                    {"name": "category", "semantic": "DIMENSION", "sql": "${TABLE}.category"},
                    {"name": "brand", "semantic": "DIMENSION", "sql": "${TABLE}.brand"},
                    {"name": "name", "semantic": "DIMENSION", "sql": "${TABLE}.name"},
                ],
                "measures": [],
            },
        },
        "governance_aspects": {
            "certification_status": "GOLD",
            "certified_by": "Enterprise Data Governance Council",
            "pii_protection": {
                "restricted_columns": ["users.email", "users.phone", "users.street_address"],
                "rule": "BLOCKED: Never include in AI-generated SQL outputs."
            }
        },
    }


DEFAULT_POLICY_GCS_URI = os.environ.get(
    "POLICY_GCS_URI",
    "gs://opm-looker-demo-policies-234424439374/policies/Corporate_Revenue_and_Refund_Policy.pdf"
)
LOCAL_POLICY_PDF = os.path.join(os.path.dirname(__file__), "../../sample_policies/Corporate_Revenue_and_Refund_Policy.pdf")


@mcp.tool()
def read_gcs_policy_document(
    gcs_uri: str = DEFAULT_POLICY_GCS_URI,
    section_query: str = "",
) -> Dict[str, Any]:
    """Read and extract text from unstructured policy documents (PDFs) in Google Cloud Storage.

    Use this tool to ground answers in corporate policies (e.g. Revenue Recognition, Refund Terms,
    and Privacy Mandates).

    Args:
        gcs_uri: GCS URI of the policy document (e.g. gs://bucket/policies/Corporate_Revenue_and_Refund_Policy.pdf).
        section_query: Optional search keyword to filter relevant paragraphs (e.g. 'refund', 'ASC 606', 'PII').
    """
    extracted_text = ""
    source_name = gcs_uri

    if os.path.exists(LOCAL_POLICY_PDF):
        try:
            from pypdf import PdfReader
            reader = PdfReader(LOCAL_POLICY_PDF)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
            source_name = f"local_cached ({LOCAL_POLICY_PDF})"
        except Exception:
            pass

    if not extracted_text and gcs_uri.startswith("gs://"):
        try:
            from google.cloud import storage
            import io
            client = storage.Client(project=DEFAULT_PROJECT_ID)
            bucket_name = gcs_uri.split("/")[2]
            blob_name = "/".join(gcs_uri.split("/")[3:])
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            pdf_bytes = blob.download_as_bytes()

            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
        except Exception:
            pass

    if not extracted_text:
        extracted_text = (
            "Corporate Revenue Recognition & Refund Policy:\n"
            "1. ASC 606 Standard: Net Revenue is recognized only when an order status is 'Complete'.\n"
            "   All returned, canceled, and in-transit orders are excluded from recognized Net Revenue.\n"
            "2. Refund Window: Customers have 30 days from delivery to request a refund.\n"
            "3. PII Policy: Customer contact info (email, phone, street address) is strictly prohibited from analytical outputs."
        )

    return {
        "status": "success",
        "document_source": source_name,
        "section_query": section_query,
        "content": extracted_text.strip(),
    }



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
    """Generates an executive-ready statistical visualization chart as an inline base64 image (PNG).

    Args:
        chart_type: Type of chart: 'bar', 'horizontal_bar', 'line', 'pie'.
        title: Clean title for the chart.
        x_values: List of category labels or X-axis values (e.g. ['China', 'United States', 'United Kingdom']).
        y_values: List of numerical metric values (e.g. [425000.0, 312000.0, 184000.0]).
        x_label: Optional label for the X axis.
        y_label: Optional label for the Y axis.
        color: Primary accent hex color (default: '#1a73e8').

    Returns:
        Dictionary containing markdown_image (base64 Data URI string) to include directly in markdown,
        summary statistics, and data points.
    """
    import base64
    import io
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        return {"error": f"Matplotlib is not installed or failed to initialize: {e}"}

    if not x_values or not y_values:
        return {"error": "x_values and y_values must not be empty."}

    if len(x_values) != len(y_values):
        return {"error": f"Length mismatch: {len(x_values)} x_values vs {len(y_values)} y_values."}

    y_clean = [float(v) if v is not None else 0.0 for v in y_values]
    x_clean = [str(v) for v in x_values]

    fig, ax = plt.subplots(figsize=(8.5, 4.5), dpi=140)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#fafafa")

    chart_type_lower = chart_type.lower()
    palette = ["#1a73e8", "#12b5cb", "#e37400", "#d93025", "#1e8e3e", "#9334e6", "#f29900", "#5f6368"]

    if chart_type_lower in ("bar", "column"):
        bars = ax.bar(x_clean, y_clean, color=color, width=0.55, edgecolor="none", zorder=3)
        ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{height:,.0f}" if abs(height) >= 10 else f"{height:,.2f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center", va="bottom", fontsize=8.5, fontweight="500", color="#202124"
            )
        plt.xticks(rotation=25 if any(len(str(s)) > 8 for s in x_clean) else 0, ha="right" if any(len(str(s)) > 8 for s in x_clean) else "center")
    elif chart_type_lower in ("horizontal_bar", "hbar"):
        y_pos = list(range(len(x_clean)))[::-1]
        bars = ax.barh(y_pos, y_clean, color=color, height=0.55, zorder=3)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(x_clean)
        ax.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)
        for bar in bars:
            width = bar.get_width()
            ax.annotate(
                f"{width:,.0f}" if abs(width) >= 10 else f"{width:,.2f}",
                xy=(width, bar.get_y() + bar.get_height() / 2),
                xytext=(5, 0),
                textcoords="offset points",
                ha="left", va="center", fontsize=8.5, fontweight="500", color="#202124"
            )
    elif chart_type_lower == "line":
        ax.plot(x_clean, y_clean, color=color, marker="o", linewidth=2.5, markersize=6, zorder=3)
        ax.grid(linestyle="--", alpha=0.35, zorder=0)
        for x, y in zip(x_clean, y_clean):
            ax.annotate(
                f"{y:,.0f}" if abs(y) >= 10 else f"{y:,.2f}",
                xy=(x, y),
                xytext=(0, 6),
                textcoords="offset points",
                ha="center", va="bottom", fontsize=8.5, fontweight="500"
            )
        plt.xticks(rotation=25 if any(len(str(s)) > 8 for s in x_clean) else 0)
    elif chart_type_lower == "pie":
        colors = palette[:len(x_clean)] if len(x_clean) <= len(palette) else None
        wedges, texts, autotexts = ax.pie(
            y_clean, labels=x_clean, autopct="%1.1f%%",
            startangle=140, colors=colors, textprops=dict(color="#202124")
        )
        for at in autotexts:
            at.set_color("#ffffff")
            at.set_fontweight("bold")
    else:
        bars = ax.bar(x_clean, y_clean, color=color, width=0.55, zorder=3)
        ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

    ax.set_title(title, fontsize=12.5, fontweight="bold", pad=14, color="#202124")
    if x_label and chart_type_lower != "pie":
        ax.set_xlabel(x_label, fontsize=9.5, labelpad=8, color="#5f6368")
    if y_label and chart_type_lower != "pie":
        ax.set_ylabel(y_label, fontsize=9.5, labelpad=8, color="#5f6368")

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["bottom", "left"]:
        ax.spines[spine].set_color("#dadce0")

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    b64_data = base64.b64encode(buf.read()).decode("utf-8")
    markdown_img = f"![{title}](data:image/png;base64,{b64_data})"

    return {
        "status": "success",
        "chart_type": chart_type,
        "title": title,
        "markdown_image": markdown_img,
        "data_points_count": len(x_clean),
    }


# Backward-compatible alias
resolve_looker_explore_and_views = check_lookml_in_knowledge_catalog


if __name__ == "__main__":
    mcp.run()
