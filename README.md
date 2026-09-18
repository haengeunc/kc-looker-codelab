# Baseline BigQuery Data Analyst Agent (LLM + BigQuery MCP only)

> **Pattern 1 of 3: The Baseline Ungoverned Text-to-SQL Architecture**

This application demonstrates a standard, un-governed generative AI analyst that queries BigQuery directly using the Model Context Protocol (MCP).

---

## Architectural Comparison Context

| Pattern | Architectural Approach | Semantic Layer | Governance / PII |
| :--- | :--- | :--- | :--- |
| **Pattern 1 (This App)** | **LLM + BigQuery MCP only** | None (Guesses raw SQL) | None (Exposes sensitive fields) |
| **Pattern 2** | **LLM + Knowledge Catalog + BigQuery MCP** | LookML via KC aspects | Dataplex PII tags + Gold Certification |
| **Pattern 3** | **LLM + Knowledge Catalog + Looker MCP** | Looker API 4.0 (Text-to-Intent) | 100% Deterministic (Zero raw SQL) |

---

## What This Pattern Demonstrates in a Demo

1. **Ungoverned Metric Calculation**:
   When asked for *"Net Revenue"*, the agent generates `SUM(sale_price)` across all orders, failing to exclude canceled, returned, or disputed orders because it lacks LookML business definitions.
2. **PII Exposure Hazard**:
   When asked for *"Top 5 customers and their emails"*, the agent directly executes `SELECT email FROM users ...` because no Dataplex tags or guardrails intercept the column.
3. **Absence of Corporate Policy Context**:
   The agent cannot explain revenue recognition (ASC 606) or refund rules because it lacks unstructured document grounding.

---

## Running Locally

```bash
# 1. Activate python environment
source ../demo-kc-bq/.venv/bin/activate

# 2. Run ADK Web UI
adk web --port 8082 baseline_analyst_agent
```

Visit `http://localhost:8082/dev-ui/?app=baseline_analyst_agent`.

---

## Deploying to Google Cloud

### Cloud Run (with Web UI)
```bash
export GOOGLE_CLOUD_PROJECT="YOUR-GCP-PROJECT"
./deploy_cloud_run.sh
```

### Vertex AI Agent Engine (for Gemini Enterprise)
```bash
export GOOGLE_CLOUD_PROJECT="YOUR-GCP-PROJECT"
./deploy_agent_engine.sh
```
