# Enterprise Data Agent Architecture Showcase (3-Tier Comparison)

This repository demonstrates three evolving architectural patterns for AI data agents on Google Cloud, contrasting **ungoverned Text-to-SQL** against **governed Text-to-Intent** using **Google Cloud Knowledge Catalog (Dataplex)** and **Looker**.

```text
                 ┌──────────────────────────────────────────────────────────┐
                 │                Gemini Enterprise (Front Door)            │
                 │   - Unified Business User UI   - Enterprise IAM/OAuth    │
                 └──────────────┬────────────────────────────┬──────────────┘
                                │ (Registered Agents)        │
         ┌──────────────────────┴────────────────────────────┴──────────────────────┐
         ▼                                                  ▼                      ▼
┌──────────────────┐                              ┌──────────────────┐   ┌──────────────────┐
│    Pattern 1     │                              │    Pattern 2     │   │    Pattern 3     │
│ Baseline Text-to-│                              │  Governed SQL    │   │ Governed Intent  │
│       SQL        │                              │ (LLM+KC+BQ MCP)  │   │(LLM+KC+Looker MCP│
├──────────────────┤                              ├──────────────────┤   ├──────────────────┤
│ • LLM            │                              │ • LLM            │   │ • LLM            │
│ • BigQuery MCP   │                              │ • KC MCP (LookML)│   │ • KC MCP (LookML)│
│                  │                              │ • GCS Policy Doc │   │ • GCS Policy Doc │
│                  │                              │ • BQ MCP (SQL)   │   │ • Looker MCP     │
└──────────────────┘                              └──────────────────┘   └──────────────────┘
```

---

## 1. Architectural Matrix

| Dimension | Pattern 1: Baseline | Pattern 2: Governed SQL | Pattern 3: Governed Intent |
| :--- | :--- | :--- | :--- |
| **Directory** | [`patterns/1-bq-baseline`](patterns/1-bq-baseline) | [`patterns/2-kc-bq-sql`](patterns/2-kc-bq-sql) | [`patterns/3-kc-looker-intent`](patterns/3-kc-looker-intent) |
| **Execution Engine** | **BigQuery Direct SQL** | **BigQuery Direct SQL** | **Looker Semantic Engine** (API 4.0) |
| **LLM Query Role** | **Ungoverned SQL Generator** | **Grounded SQL Compiler** | **Deterministic Intent Resolver** |
| **Knowledge Catalog** | None | Schema, Joins & LookML formulas | PII Tags, Certification & Glossary |
| **Unstructured Grounding** | None | Corporate Policy PDF (GCS) | Corporate Policy PDF (GCS) |
| **Metric Consistency** | ❌ Hallucination Risk | ⚠️ Grounded in LookML formulas | 🟢 **100% Dashboard Consistency** |
| **PII Data Leakage** | ❌ High risk (Raw columns) | 🟢 **Blocked** via Dataplex tags | 🟢 **Blocked** via pre-exec guardrail |

---

## 2. Directory Structure

```text
kc-looker-codelab/
├── README.md                      # This 3-Tier comparison guide
├── run_all_local.sh               # One-click launcher for all 3 agents (ports 8080, 8081, 8082)
├── sample_policies/               # Shared corporate policy PDFs
│   └── Corporate_Revenue_and_Refund_Policy.pdf
├── patterns/
│   ├── 1-bq-baseline/             # Pattern 1: LLM + BigQuery MCP only
│   │   ├── baseline_analyst_agent/
│   │   ├── deploy_cloud_run.sh
│   │   └── deploy_agent_engine.sh
│   ├── 2-kc-bq-sql/               # Pattern 2: LLM + Knowledge Catalog + BQ MCP
│   │   ├── looker_analyst_agent/
│   │   ├── deploy_cloud_run.sh
│   │   └── deploy_agent_engine.sh
│   └── 3-kc-looker-intent/        # Pattern 3: LLM + Knowledge Catalog + Looker MCP
│       ├── looker_governed_agent/
│       ├── deploy_cloud_run.sh
│       └── deploy_agent_engine.sh
└── requirements.txt               # Unified dependencies
```

---

## 3. Quickstart: Live Side-by-Side "3-Tab" Demo

Run all three agents simultaneously to demonstrate the contrast in real time:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch all 3 agents
./run_all_local.sh all
```

Open three browser tabs:
* **Tab 1 (Pattern 1)**: `http://localhost:8080/dev-ui/?app=baseline_analyst_agent`
* **Tab 2 (Pattern 2)**: `http://localhost:8081/dev-ui/?app=looker_analyst_agent`
* **Tab 3 (Pattern 3)**: `http://localhost:8082/dev-ui/?app=looker_governed_agent`

### Ask the Same 3 Questions to All Tabs:

#### Test 1: Calculation Logic & Net Revenue
> *"What is our total Net Revenue / Sales for the United States, and how is it calculated?"*
* **Pattern 1**: Guesses raw SQL `SUM(sale_price)` across all rows, counting canceled and returned orders without business rule filters.
* **Pattern 2**: Inspects Knowledge Catalog, retrieves LookML definitions and policy filters, and generates validated SQL.
* **Pattern 3**: Passes `measures: ["order_items.total_sale_price"]` to Looker API 4.0. Looker applies symmetric aggregates and semantic governance with 100% dashboard consistency.

#### Test 2: PII Data Leakage Protection
> *"Show our top 5 customers and their email addresses."*
* **Pattern 1**: **Leaks PII**: Runs `SELECT email FROM users ...` without warning.
* **Pattern 2**: **Blocks PII**: Detects Dataplex tag `RESTRICTED_PII` on `users.email` and refuses the column.
* **Pattern 3**: **Blocks PII**: Pre-execution check intercepts the request before hitting Looker.

#### Test 3: Unstructured Policy Grounding
> *"Why are returned orders excluded from revenue, and what is our return window?"*
* **Pattern 1**: Cannot answer; no document access.
* **Pattern 2 & 3**: Reads `Corporate_Revenue_and_Refund_Policy.pdf` from GCS, citing ASC 606 standards and the 30-day return policy.

---

## 4. Deploying to Google Cloud

### Cloud Run (with ADK Web UI)
Each pattern can be deployed independently to Google Cloud Run:
```bash
# Deploy Pattern 1
cd patterns/1-bq-baseline && ./deploy_cloud_run.sh

# Deploy Pattern 2
cd patterns/2-kc-bq-sql && ./deploy_cloud_run.sh

# Deploy Pattern 3
cd patterns/3-kc-looker-intent && ./deploy_cloud_run.sh
```

### Vertex AI Agent Engine & Gemini Enterprise
Deploy to Agent Engine to register the agents directly into Gemini Enterprise:
```bash
cd patterns/3-kc-looker-intent && ./deploy_agent_engine.sh
```
In Google Cloud Console:
1. Navigate to **Gemini Enterprise** $\to$ **Agent Studio / Agents**.
2. Click **Add Agent** $\to$ **Custom Agent (Agent Runtime)**.
3. Select the deployed Reasoning Engine instance to surface the agent to business users.
