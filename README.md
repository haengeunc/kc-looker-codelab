# Vertex AI Looker Analyst Agent (Knowledge Catalog MCP + BigQuery MCP Toolbox)

This project implements a **Vertex AI / Agent Development Kit (`google-adk`) Data Analyst Agent** (`looker_knowledge_catalog_analyst_agent`) that connects to:
1. **Google Cloud Knowledge Catalog (Dataplex) MCP** — to discover and inspect certified Looker semantic metadata:
   - Looker Explores (`customer_orders`, etc.)
   - Looker Join Graphs (`LEFT OUTER JOIN`, `MANY_TO_ONE`, exact `sqlOn` expressions)
   - Looker Views (`order_items`, `users`, `orders`, `products`, `user_order_facts`)
   - Exact LookML SQL definitions (`annotations.sql` for dimensions and measures, e.g., `net_revenue` = `CASE WHEN order_items.status = 'Complete' THEN order_items.sale_price ELSE 0 END`)
   - Data Certification aspects (`Certified = True`, `Environment = PRODUCTION`, `Certification Tier = Gold`)
2. **BigQuery MCP Toolbox for Databases** — to compile those LookML definitions into BigQuery Standard SQL and execute them against `haengeun-429200` (`bigquery-public-data.thelook_ecommerce`).

---

## Project Structure

```
demo-kc-bq/
├── looker_analyst_agent/
│   ├── __init__.py               # Exports `root_agent` for ADK discovery
│   ├── agent.py                  # Vertex AI LlmAgent (`gemini-2.5-pro`) & MCPToolset wiring
│   ├── kc_bq_mcp_server.py       # Knowledge Catalog & BigQuery MCP Server + Looker semantic tools
│   └── prompt.py                 # 4-step governed analytical system prompt & attribution rules
├── .agents/
│   ├── mcp_config.json           # MCP configuration for Knowledge Catalog & BigQuery Toolbox
│   └── rules/
│       └── governance.md         # Corporate Data Governance & Certification Rules
├── run_demo_query.py             # CLI runner for end-to-end Looker-grounded analytical queries
└── README.md
```

---

## Quick Start

### 1. Run an End-to-End Analytical Query via CLI

```bash
cd /usr/local/google/home/haengeun/projects/demo-kc-bq
./.venv/bin/python run_demo_query.py "What is our total Net Revenue, total completed orders count, and Net Average Order Value (Net AOV) by user country for the top 5 countries?"
```

Or ask any custom Looker question:
```bash
./.venv/bin/python run_demo_query.py "What are the top 5 product categories by Gross Revenue and Net Revenue in 2024?"
```

### 2. Launch the Interactive Vertex AI ADK Web UI (Cloudtop)

When running on a Google Cloudtop, bind `adk web` to `0.0.0.0` so your laptop browser can connect via your Cloudtop hostname:

```bash
cd /usr/local/google/home/haengeun/projects/demo-kc-bq
./.venv/bin/adk web --host 0.0.0.0 --port 8000 --allow_origins "*"
```

Then open **`http://haengeun-demo.c.googlers.com:8000`** in your browser and select **`looker_analyst_agent`**.

### 3. Run the Agent Interactively in the Terminal

```bash
cd /usr/local/google/home/haengeun/projects/demo-kc-bq
./.venv/bin/adk run looker_analyst_agent
```

---

## Using the Native `toolbox` Binary (`--prebuilt dataplex --prebuilt bigquery`)

The project supports both:
- **`kc_bq_mcp_server.py`** (default, includes resilient `gcloud auth print-access-token` authentication and specialized Looker semantic tools like `resolve_looker_explore_and_views`)
- **`/usr/local/google/home/haengeun/.local/bin/toolbox`** (Google's official MCP Toolbox for Databases binary with `--prebuilt dataplex` and `--prebuilt bigquery`)

To enable the native `toolbox` binary alongside the Looker semantic tools:
1. Ensure your Application Default Credentials (ADC) are refreshed:
   ```bash
   gcloud auth application-default login
   ```
2. Set `USE_BINARY_TOOLBOX=1` when running the agent:
   ```bash
   USE_BINARY_TOOLBOX=1 ./.venv/bin/adk web
   ```
