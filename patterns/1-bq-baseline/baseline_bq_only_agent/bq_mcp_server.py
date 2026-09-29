#!/usr/bin/env python3
"""MCP Server for BigQuery Baseline Analyst.

Delegates core BigQuery operations to the official Managed BigQuery MCP service
(https://bigquery.googleapis.com/mcp) under the hood:
1. list_datasets -> Managed BigQuery MCP list_dataset_ids
2. list_tables -> Managed BigQuery MCP list_table_ids
3. get_table_schema -> Managed BigQuery MCP get_table_info
4. execute_bigquery_sql -> Managed BigQuery MCP execute_sql_readonly
5. generate_data_chart -> Native executive visual chart generation (base64 PNG)
"""

import base64
import io
import json
import os
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


def _get_auth_token() -> str:
    """Gets a valid Google Cloud OAuth2 access token for BigQuery API calls."""
    env_token = os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN")
    if env_token:
        return env_token.strip()

    try:
        auth_fn = getattr(google.auth, "_orig_default", google.auth.default)
        creds, _ = auth_fn(scopes=[
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/bigquery",
        ])
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        if creds.token:
            return creds.token
    except Exception:
        pass

    return ""


def _call_managed_bq_mcp(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Invokes a tool on the official Managed BigQuery MCP server via JSON-RPC 2.0.

    Args:
        tool_name: The name of the tool on the Managed BigQuery MCP (e.g., 'list_dataset_ids').
        arguments: Arguments dictionary for the tool.

    Returns:
        Structured content dictionary or parsed JSON result.
    """
    token = _get_auth_token()
    headers = {
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = {
        "jsonrpc": "2.0",
        "id": 1,
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
        if "structuredContent" in result and result["structuredContent"]:
            return result["structuredContent"]

        for content_item in result.get("content", []):
            if content_item.get("type") == "text":
                text_val = content_item.get("text", "")
                try:
                    return json.loads(text_val)
                except Exception:
                    return {"text": text_val}

        return result
    except Exception as e:
        return {"error": f"Failed calling Managed BigQuery MCP '{tool_name}': {str(e)}"}


@mcp.tool()
def list_datasets(project_id: Optional[str] = None) -> str:
    """Lists available BigQuery datasets in a Google Cloud project via Managed BigQuery MCP.

    Args:
        project_id: GCP project ID (default: current project from environment).
    """
    proj = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "opm-looker-core-demo-instance")
    res = _call_managed_bq_mcp("list_dataset_ids", {"projectId": proj, "pageSize": 50})

    if "error" in res:
        return json.dumps({"error": res["error"]})

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


@mcp.tool()
def list_tables(dataset_id: str = "thelook_ecommerce", project_id: Optional[str] = None) -> str:
    """Lists tables available in a BigQuery dataset via Managed BigQuery MCP.

    Args:
        dataset_id: The BigQuery dataset ID (default: 'thelook_ecommerce').
        project_id: The project containing the dataset (default: current project from environment).
    """
    proj = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "opm-looker-core-demo-instance")
    res = _call_managed_bq_mcp("list_table_ids", {
        "projectId": proj,
        "datasetId": dataset_id,
        "pageSize": 50,
    })

    if "error" in res:
        return json.dumps({"error": res["error"]})

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
        project_id: Project ID (default: current project from environment).
    """
    proj = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "opm-looker-core-demo-instance")
    res = _call_managed_bq_mcp("get_table_info", {
        "projectId": proj,
        "datasetId": dataset_id,
        "tableId": table_id,
    })

    if "error" in res:
        return json.dumps({"error": res["error"]})

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


@mcp.tool()
def execute_bigquery_sql(sql_query: str, project_id: Optional[str] = None) -> str:
    """Executes a GoogleSQL read-only query against BigQuery via Managed BigQuery MCP.

    Args:
        sql_query: The GoogleSQL SELECT query to execute.
        project_id: GCP Project ID to bill for execution (defaults to current project).
    """
    proj = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "opm-looker-core-demo-instance")
    clean_sql = sql_query.strip().rstrip(";")

    res = _call_managed_bq_mcp("execute_sql_readonly", {
        "projectId": proj,
        "query": clean_sql,
    })

    if "error" in res:
        return json.dumps({
            "status": "ERROR",
            "error": res["error"],
            "sql_attempted": clean_sql,
        }, indent=2)

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

    fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=75)
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
    elif chart_type_lower in ("area",):
        ax.plot(x_clean, y_clean, color=color, linewidth=2, zorder=3)
        ax.fill_between(range(len(x_clean)), y_clean, color=color, alpha=0.35, zorder=2)
        ax.grid(linestyle="--", alpha=0.35, zorder=0)
        plt.xticks(range(len(x_clean)), x_clean, rotation=25 if any(len(str(s)) > 8 for s in x_clean) else 0)
    elif chart_type_lower in ("scatter",):
        ax.scatter(x_clean, y_clean, color=color, s=70, alpha=0.85, zorder=3)
        ax.grid(linestyle="--", alpha=0.35, zorder=0)
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


if __name__ == "__main__":
    mcp.run()
