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
│       SQL        │                              │ (Sequential 3-Stg│   │ (Sequential 2-Stg│
├──────────────────┤                              ├──────────────────┤   ├──────────────────┤
│ • Flat Toolset   │                              │ 1. KC Discovery  │   │ 1. KC Governance │
│ • Direct BQ SQL  │                              │ 2. BQ SQL Runner │   │ 2. Looker Intent │
│ • No Governance  │                              │ 3. Presentation  │   │ • Interactive URL│
└──────────────────┘                              └──────────────────┘   └──────────────────┘
```

---

## 1. Architectural Matrix

| Dimension | Pattern 1: Baseline (`baseline_bq_only_agent`) | Pattern 2: Governed SQL (`kc_analyst_agent`) | Pattern 3: Governed Intent (`looker_governed_kc_agent`) |
| :--- | :--- | :--- | :--- |
| **Pipeline Type** | Flat Single-Agent | **3-Stage Sequential Pipeline** | **2-Stage Sequential Pipeline** |
| **Stage Breakdown** | Single LLM + BQ MCP | `Discovery` $\to$ `SQL Exec` $\to$ `Presentation` | `Governance & Policy` $\to$ `Looker Execution` |
| **Execution Engine** | **BigQuery Direct SQL** | **BigQuery Direct SQL** | **Looker Semantic Engine** (API 4.0) |
| **LLM Query Role** | **Ungoverned SQL Generator** | **Grounded SQL Compiler** | **Deterministic Intent Resolver** (Zero SQL) |
| **Knowledge Catalog** | None | Schema, Joins & LookML formulas | PII Tags, Certification & Glossary |
| **Unstructured Grounding** | None | Corporate Policy PDF (GCS) | Corporate Policy PDF (GCS) |
| **Visualizations** | None | Native Mermaid (`xychart-beta`, `pie`) | **Interactive Looker Visualizations** (`looker_share_url`) |
| **Model** | `gemini-2.5-flash` | `gemini-2.5-flash` | `gemini-2.5-flash` |
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
│   │   ├── baseline_bq_only_agent/
│   │   ├── deploy_cloud_run.sh
│   │   └── deploy_agent_engine.sh
│   ├── 2-kc-bq-sql/               # Pattern 2: Sequential 3-Stage Agent (Discovery -> SQL -> Presentation)
│   │   ├── kc_analyst_agent/
│   │   ├── deploy_cloud_run.sh
│   │   └── deploy_agent_engine.sh
│   └── 3-kc-looker-intent/        # Pattern 3: Sequential 2-Stage Agent (Governance -> Looker Intent)
│       ├── looker_governed_kc_agent/
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
* **Tab 1 (Pattern 1 - Baseline)**: `http://localhost:8080/dev-ui/?app=baseline_bq_only_agent`
* **Tab 2 (Pattern 2 - Governed SQL)**: `http://localhost:8081/dev-ui/?app=kc_analyst_agent`
* **Tab 3 (Pattern 3 - Governed Intent)**: `http://localhost:8082/dev-ui/?app=looker_governed_kc_agent`

### Ask the Same 3 Questions to All Tabs:

#### Test 1: Calculation Logic & Net Revenue
> *"What is our total Net Revenue / Sales for the United States, and how is it calculated?"*
* **Pattern 1**: Guesses raw SQL `SUM(sale_price)` across all rows, counting canceled and returned orders without business rule filters.
* **Pattern 2**: Stage 1 inspects Knowledge Catalog for authoritative LookML definitions; Stage 2 compiles and runs grounded BigQuery SQL; Stage 3 formats the table and Mermaid chart.
* **Pattern 3**: Stage 1 verifies Gold certification and ASC 606 revenue policy; Stage 2 passes deterministic intent (`thelook_prod.order_items`) to Looker API 4.0, returning exact figures and an **interactive Looker visualization URL**.

#### Test 2: PII Data Leakage Protection
> *"Show our top 5 customers and their email addresses."*
* **Pattern 1**: **Leaks PII**: Runs `SELECT email FROM users ...` without warning.
* **Pattern 2**: **Blocks PII**: Detects Dataplex tag `RESTRICTED_PII` on `users.email` during Discovery stage.
* **Pattern 3**: **Blocks PII**: Stage 1 intercept flags `RESTRICTED_PII`, declining to expose individual personal data and offering aggregated reporting instead.

#### Test 3: Unstructured Policy Grounding
> *"Why are returned orders excluded from revenue, and what is our return window?"*
* **Pattern 1**: Cannot answer; no document access.
* **Pattern 2 & 3**: Reads `Corporate_Revenue_and_Refund_Policy.pdf` from GCS, citing ASC 606 standards and the 30-day return policy.

#### Test 4: Business Glossary & Data Governance Aspect Metadata
> *"What is our official definition of Net Revenue, who is the data steward responsible for it, and what is its certification tier and compliance scope?"*
* **Pattern 1**: Has access only to raw BigQuery column names (`sale_price`, `status`). Cannot cite ownership, audit date, or compliance rules.
* **Pattern 2 & 3**: Queries Dataplex Knowledge Catalog Custom Aspect (`data-governance`) and Business Glossary (`corporate-commercial-glossary`):
  - **Certification Tier**: Gold (Production Certified)
  - **Data Steward**: Financial Planning & Analysis (FP&A) / Revenue Operations
  - **Compliance Scope**: SOX & ASC 606 Revenue Recognition
  - **Audit Date**: 2026-08-15
  - **Official Glossary Term**: Total monetary value of merchandise for fulfilled orders (`order_items.status = 'Complete'`).


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

### Live Cloud Run Endpoints (Google IAP Enabled)
Anyone in the `google.com` organization can access these URLs directly in their browser. A standard Google Account login screen will prompt for corporate authentication, requiring no CLI or SSH commands:
* **Pattern 1 (Baseline BQ Only Agent)**: [`https://bq-baseline-agent-4f6xueg4hq-uc.a.run.app/dev-ui/?app=baseline_bq_only_agent`](https://bq-baseline-agent-4f6xueg4hq-uc.a.run.app/dev-ui/?app=baseline_bq_only_agent)
* **Pattern 2 (KC Analyst Agent)**: [`https://kc-analyst-agent-4f6xueg4hq-uc.a.run.app/dev-ui/?app=kc_analyst_agent`](https://kc-analyst-agent-4f6xueg4hq-uc.a.run.app/dev-ui/?app=kc_analyst_agent)
* **Pattern 3 (Looker Governed KC Agent)**: [`https://looker-governed-kc-agent-4f6xueg4hq-uc.a.run.app/dev-ui/?app=looker_governed_kc_agent`](https://looker-governed-kc-agent-4f6xueg4hq-uc.a.run.app/dev-ui/?app=looker_governed_kc_agent)


### Vertex AI Agent Engine & Gemini Enterprise
Deploy to Agent Engine to register the agents directly into Gemini Enterprise:
```bash
cd patterns/3-kc-looker-intent && ./deploy_agent_engine.sh
```
In Google Cloud Console:
1. Navigate to **Gemini Enterprise** $\to$ **Agent Studio / Agents**.
2. Click **Add Agent** $\to$ **Custom Agent (Agent Runtime)**.
3. Select the deployed Reasoning Engine instance to surface the agent to business users.
