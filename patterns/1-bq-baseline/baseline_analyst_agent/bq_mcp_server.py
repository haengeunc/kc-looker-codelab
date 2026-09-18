#!/usr/bin/env python3
"""MCP Server for BigQuery Baseline Analyst.

Provides direct BigQuery access tools without Knowledge Catalog governance:
1. list_tables: Lists tables in a BigQuery dataset.
2. get_table_schema: Retrieves standard column names and types for a BigQuery table.
3. execute_bigquery_sql: Executes standard SQL queries directly against BigQuery.
4. generate_data_chart: Generates executive visual charts (base64 PNG) from query results.
"""

import json
import os
import subprocess
import time
from typing import Any, Dict, List, Optional
import requests

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

mcp = FastMCP("BigQuery-Baseline-Analyst-MCP")


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
_TOKEN_CACHE: Dict[str, Any] = {"token": None, "expires_at": 0}


def _get_access_token() -> str:
    """Gets a valid Google Cloud access token."""
    now = time.time()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expires_at"]:
        return _TOKEN_CACHE["token"]

    env_token = os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN")
    if env_token:
        _TOKEN_CACHE["token"] = env_token.strip()
        _TOKEN_CACHE["expires_at"] = now + 3000
        return _TOKEN_CACHE["token"]

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
                _TOKEN_CACHE["expires_at"] = now + int(token_data.get("expires_in", 3600)) - 60
                return access_token
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode().strip()
        if out:
            _TOKEN_CACHE["token"] = out
            _TOKEN_CACHE["expires_at"] = now + 1800
            return out
    except Exception:
        pass

    return ""


@mcp.tool()
def list_tables(dataset_id: str = "thelook_ecommerce", project_id: str = "bigquery-public-data") -> str:
    """Lists tables available in a BigQuery dataset.
    
    Args:
        dataset_id: The BigQuery dataset ID (default: 'thelook_ecommerce').
        project_id: The project containing the dataset (default: 'bigquery-public-data').
    """
    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=DEFAULT_PROJECT_ID)
        dataset_ref = bigquery.DatasetReference(project_id, dataset_id)
        tables = [t.table_id for t in client.list_tables(dataset_ref)]
        return json.dumps({"project": project_id, "dataset": dataset_id, "tables": tables}, indent=2)
    except Exception:
        pass

    token = _get_access_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}/tables"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            tables = [t.get("tableReference", {}).get("tableId") for t in resp.json().get("tables", [])]
            return json.dumps({"project": project_id, "dataset": dataset_id, "tables": tables}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

    # Fallback to standard thelook_ecommerce tables
    return json.dumps({
        "project": project_id,
        "dataset": dataset_id,
        "tables": ["order_items", "orders", "users", "products", "inventory_items", "distribution_centers", "events"]
    }, indent=2)


@mcp.tool()
def get_table_schema(table_id: str, dataset_id: str = "thelook_ecommerce", project_id: str = "bigquery-public-data") -> str:
    """Gets the column names and data types for a BigQuery table.
    
    Args:
        table_id: Name of the table (e.g., 'order_items', 'users', 'products', 'orders').
        dataset_id: Dataset ID (default: 'thelook_ecommerce').
        project_id: Project ID (default: 'bigquery-public-data').
    """
    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=DEFAULT_PROJECT_ID)
        table_ref = f"{project_id}.{dataset_id}.{table_id}"
        table = client.get_table(table_ref)
        fields = [{"name": f.name, "type": f.field_type} for f in table.schema]
        return json.dumps({"table": table_ref, "columns": fields}, indent=2)
    except Exception:
        pass

    token = _get_access_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset_id}/tables/{table_id}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            schema_fields = resp.json().get("schema", {}).get("fields", [])
            fields = [{"name": f["name"], "type": f["type"]} for f in schema_fields]
            return json.dumps({"table": f"{project_id}.{dataset_id}.{table_id}", "columns": fields}, indent=2)
    except Exception:
        pass

    # Built-in standard schemas for thelook_ecommerce
    schemas = {
        "order_items": [
            {"name": "id", "type": "INTEGER"},
            {"name": "order_id", "type": "INTEGER"},
            {"name": "user_id", "type": "INTEGER"},
            {"name": "product_id", "type": "INTEGER"},
            {"name": "inventory_item_id", "type": "INTEGER"},
            {"name": "status", "type": "STRING"},
            {"name": "created_at", "type": "TIMESTAMP"},
            {"name": "shipped_at", "type": "TIMESTAMP"},
            {"name": "delivered_at", "type": "TIMESTAMP"},
            {"name": "returned_at", "type": "TIMESTAMP"},
            {"name": "sale_price", "type": "FLOAT"},
        ],
        "users": [
            {"name": "id", "type": "INTEGER"},
            {"name": "first_name", "type": "STRING"},
            {"name": "last_name", "type": "STRING"},
            {"name": "email", "type": "STRING"},
            {"name": "age", "type": "INTEGER"},
            {"name": "gender", "type": "STRING"},
            {"name": "state", "type": "STRING"},
            {"name": "street_address", "type": "STRING"},
            {"name": "postal_code", "type": "STRING"},
            {"name": "city", "type": "STRING"},
            {"name": "country", "type": "STRING"},
            {"name": "latitude", "type": "FLOAT"},
            {"name": "longitude", "type": "FLOAT"},
            {"name": "traffic_source", "type": "STRING"},
            {"name": "created_at", "type": "TIMESTAMP"},
        ],
        "products": [
            {"name": "id", "type": "INTEGER"},
            {"name": "cost", "type": "FLOAT"},
            {"name": "category", "type": "STRING"},
            {"name": "name", "type": "STRING"},
            {"name": "brand", "type": "STRING"},
            {"name": "retail_price", "type": "FLOAT"},
            {"name": "department", "type": "STRING"},
            {"name": "sku", "type": "STRING"},
            {"name": "distribution_center_id", "type": "INTEGER"},
        ],
        "orders": [
            {"name": "order_id", "type": "INTEGER"},
            {"name": "user_id", "type": "INTEGER"},
            {"name": "status", "type": "STRING"},
            {"name": "gender", "type": "STRING"},
            {"name": "created_at", "type": "TIMESTAMP"},
            {"name": "returned_at", "type": "TIMESTAMP"},
            {"name": "shipped_at", "type": "TIMESTAMP"},
            {"name": "delivered_at", "type": "TIMESTAMP"},
            {"name": "num_of_item", "type": "INTEGER"},
        ]
    }
    if table_id in schemas:
        return json.dumps({"table": f"{project_id}.{dataset_id}.{table_id}", "columns": schemas[table_id]}, indent=2)
    return json.dumps({"error": f"Schema not found for table {table_id}"})


@mcp.tool()
def execute_bigquery_sql(sql_query: str, project_id: Optional[str] = None) -> str:
    """Executes a GoogleSQL query against BigQuery and returns rows as JSON.
    
    Args:
        sql_query: The GoogleSQL SELECT query to execute.
        project_id: GCP Project ID to bill for execution (defaults to current project).
    """
    proj = project_id or DEFAULT_PROJECT_ID
    clean_sql = sql_query.strip().rstrip(";")

    # 1. Primary: Official google.cloud.bigquery Client (handles ADC & corporate auth natively)
    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=proj)
        job = client.query(clean_sql)
        rows = [dict(row) for row in job.result()]
        return json.dumps({
            "status": "SUCCESS",
            "totalRows": str(len(rows)),
            "rows": rows,
            "sql_executed": clean_sql,
        }, default=str, indent=2)
    except Exception:
        pass

    # 2. REST API fallback
    token = _get_access_token()
    if token:
        try:
            url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{proj}/queries"
            payload = {
                "query": clean_sql,
                "useLegacySql": False,
                "maxResults": 100,
                "timeoutMs": 30000,
            }
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=35)
            if resp.status_code == 200:
                data = resp.json()
                schema_fields = [f["name"] for f in data.get("schema", {}).get("fields", [])]
                rows = []
                for row_obj in data.get("rows", []):
                    row_vals = [cell.get("v") for cell in row_obj.get("f", [])]
                    rows.append(dict(zip(schema_fields, row_vals)))
                return json.dumps({
                    "status": "SUCCESS",
                    "totalRows": data.get("totalRows", str(len(rows))),
                    "rows": rows,
                    "sql_executed": clean_sql,
                }, indent=2)
        except Exception:
            pass

    # CLI fallback
    try:
        cmd = [
            "bq", "query",
            "--nouse_legacy_sql",
            "--format=json",
            f"--project_id={proj}",
            clean_sql,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            rows = json.loads(res.stdout.strip() or "[]")
            return json.dumps({
                "status": "SUCCESS",
                "totalRows": str(len(rows)),
                "rows": rows,
                "sql_executed": clean_sql,
            }, indent=2)
        return json.dumps({
            "status": "ERROR",
            "error": res.stderr.strip(),
            "sql_attempted": clean_sql,
        })
    except Exception as e:
        return json.dumps({
            "status": "ERROR",
            "error": str(e),
            "sql_attempted": clean_sql,
        })


@mcp.tool()
def generate_data_chart(chart_title: str, chart_type: str, labels: List[str], values: List[float], y_axis_label: str = "Value") -> str:
    """Generates an executive-ready chart as an inline base64-encoded PNG image."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import io
        import base64

        fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=75)
        colors = ["#4285F4", "#34A853", "#FBBC05", "#EA4335", "#8AB4F8", "#81C995"]

        if chart_type.lower() == "pie":
            wedges, texts, autotexts = ax.pie(
                values,
                labels=labels,
                autopct="%1.1f%%",
                startangle=140,
                colors=colors[:len(values)],
            )
            for at in autotexts:
                at.set_color("white")
                at.set_fontsize(10)
        elif chart_type.lower() == "line":
            ax.plot(labels, values, marker="o", color="#4285F4", linewidth=2.5, markersize=6)
            ax.set_ylabel(y_axis_label)
            ax.grid(True, linestyle="--", alpha=0.5)
        else:
            bar_colors = [colors[i % len(colors)] for i in range(len(values))]
            bars = ax.bar(labels, values, color=bar_colors, edgecolor="#202124", linewidth=0.5)
            ax.set_ylabel(y_axis_label)
            ax.grid(axis="y", linestyle="--", alpha=0.4)
            for bar in bars:
                h = bar.get_height()
                ax.annotate(
                    f"{h:,.0f}" if h >= 100 else f"{h:,.2f}",
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        ax.set_title(chart_title, fontsize=12, fontweight="bold", pad=12)
        plt.xticks(rotation=25 if len(labels) > 4 else 0, ha="right" if len(labels) > 4 else "center")
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)

        return json.dumps({
            "status": "SUCCESS",
            "chart_title": chart_title,
            "image_markdown": f"![{chart_title}](data:image/png;base64,{img_b64})",
        })
    except Exception as e:
        return json.dumps({"status": "ERROR", "error": f"Failed to render chart: {str(e)}"})


if __name__ == "__main__":
    mcp.run()
