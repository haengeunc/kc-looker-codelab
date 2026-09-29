# Enterprise Data Agent Architecture Showcase (4-Tier Comparison)

This repository demonstrates four evolving architectural patterns for AI data agents on Google Cloud, contrasting **ungoverned Text-to-SQL**, **governed Text-to-SQL**, **governed Text-to-Intent (Looker)**, and **Looker-Free Dataplex-Governed Analyst Agents** using **Google Cloud Knowledge Catalog (Dataplex)**, **Managed BigQuery MCP**, and **Looker**.

```text
                 ┌────────────────────────────────────────────────────────────────────────┐
                 │                    Gemini Enterprise (Front Door)                      │
                 │       - Unified Business User UI     - Enterprise IAM / OAuth          │
                 └──────────────┬───────────────────┬───────────────────┬─────────────────┘
                                │                   │                   │
         ┌──────────────────────┴───────────┬───────┴───────────┬───────┴─────────────────┐
         ▼                                  ▼                   ▼                         ▼
┌──────────────────┐               ┌──────────────────┐┌──────────────────┐      ┌──────────────────┐
│    Pattern 1     │               │    Pattern 2     ││    Pattern 3     │      │    Pattern 4     │
│ Baseline Text-to-│               │  Governed SQL    ││ Governed Intent  │      │ Pure KC Governed │
│       SQL        │               │ (Sequential 3-Stg││ (Sequential 2-Stg│      │  (Looker-Free)   │
├──────────────────┤               ├──────────────────┤├──────────────────┤      ├──────────────────┤
│ • Flat Toolset   │               │ 1. KC Discovery  ││ 1. KC Governance │      │ • Sovereign ADK  │
│ • Direct BQ SQL  │               │ 2. BQ SQL Runner ││ 2. Looker Intent │      │ • Dataplex Gloss.│
│ • No Governance  │               │ 3. Presentation  ││ • Interactive URL│      │ • Managed BQ MCP │
└──────────────────┘               └──────────────────┘└──────────────────┘      │ • Chart Visuals  │
                                                                                 └──────────────────┘
```

---

## 1. Architectural Matrix

| Dimension | Pattern 1: Baseline (`baseline_bq_only_agent`) | Pattern 2: Governed SQL (`kc_analyst_agent`) | Pattern 3: Governed Intent (`looker_governed_kc_agent`) | Pattern 4: Pure KC Governance (`kc_pure_agent`) |
| :--- | :--- | :--- | :--- | :--- |
| **Pipeline Type** | Flat Single-Agent | **3-Stage Sequential Pipeline** | **2-Stage Sequential Pipeline** | **Autonomous Sovereign Agent** (5-Step Plan) |
| **Stage Breakdown** | Single LLM + BQ MCP | `Discovery` $\to$ `SQL Exec` $\to$ `Presentation` | `Governance & Policy` $\to$ `Looker Execution` | Mandatory Planning $\to$ Catalog $\to$ Dates $\to$ SQL $\to$ Viz |
| **Execution Engine** | **BigQuery Direct SQL** | **BigQuery Direct SQL** | **Looker Semantic Engine** (API 4.0) | **BigQuery Direct SQL** (via Managed MCP) |
| **LLM Query Role** | **Ungoverned SQL Generator** | **Grounded SQL Compiler** | **Deterministic Intent Resolver** (Zero SQL) | **Catalog-Grounded SQL Author** (Zero Looker) |
| **Knowledge Catalog** | None | Schema, Joins & LookML formulas | PII Tags, Certification & Glossary | Business Glossaries, Custom Aspects & Certified Rel. |
| **Looker Dependency** | None | Uses LookML formula metadata | **Direct Looker API 4.0 Integration** | **None (100% Looker-Free)** |
| **Unstructured Grounding** | None | Corporate Policy PDF (GCS) | Corporate Policy PDF (GCS) | Catalog Aspect Documentation & Glossary Policies |
| **Visualizations** | None | **Rendered Visual Charts (Embedded Graphics)** | **Interactive Looker Visualizations** (`looker_share_url`) | **High-Fidelity Executive Charts (Matplotlib Base64)** |
| **Model** | `gemini-2.5-flash` | `gemini-2.5-flash` | `gemini-2.5-flash` | `gemini-2.5-flash` |
| **Metric Consistency** | ❌ Hallucination Risk | ⚠️ Grounded in LookML formulas | 🟢 **100% Dashboard Consistency** | 🟢 **100% Governed via Catalog Glossaries** |
| **PII Data Leakage** | ❌ High risk (Raw columns) | 🟢 **Blocked** via Dataplex tags | 🟢 **Blocked** via pre-exec guardrail | 🟢 **Blocked** via Dataplex `data-sensitivity` aspect |

---

## 2. Directory Structure

```text
kc-looker-codelab/
├── README.md                      # This 4-Tier comparison guide
├── run_all_local.sh               # One-click launcher for all 4 agents (ports 8080, 8081, 8082, 8083)
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
│   ├── 3-kc-looker-intent/        # Pattern 3: Sequential 2-Stage Agent (Governance -> Looker Intent)
│   │   ├── looker_governed_kc_agent/
│   │   ├── deploy_cloud_run.sh
│   │   └── deploy_agent_engine.sh
│   └── 4-kc-pure-governance/      # Pattern 4: Pure KC Governance Agent (Looker-Free)
│       ├── kc_pure_agent/
│       ├── deploy_cloud_run.sh
│       ├── deploy_agent_engine.sh
│       └── demo_test.py
└── requirements.txt               # Unified dependencies
```

---

## 3. Quickstart: Live Side-by-Side "4-Tab" Demo

Run all four agents simultaneously to demonstrate the contrast in real time:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch all 4 agents
./run_all_local.sh all
```

Open four browser tabs:
* **Tab 1 (Pattern 1 - Baseline)**: `http://localhost:8080/dev-ui/?app=baseline_bq_only_agent`
* **Tab 2 (Pattern 2 - Governed SQL)**: `http://localhost:8081/dev-ui/?app=kc_analyst_agent`
* **Tab 3 (Pattern 3 - Governed Intent)**: `http://localhost:8082/dev-ui/?app=looker_governed_kc_agent`
* **Tab 4 (Pattern 4 - Pure KC Governed)**: `http://localhost:8083/dev-ui/?app=kc_pure_agent`

### Ask the Same Questions Across the Tabs:

#### Test 1: Calculation Logic & Net Revenue
> *"What is our total Net Revenue / Sales for the United States, and how is it calculated?"*
* **Pattern 1**: Guesses raw SQL `SUM(sale_price)` across all rows, counting canceled and returned orders without business rule filters.
* **Pattern 2**: Stage 1 inspects Knowledge Catalog for authoritative LookML definitions; Stage 2 compiles and runs grounded BigQuery SQL; Stage 3 formats the table and Mermaid chart.
* **Pattern 3**: Stage 1 verifies Gold certification and ASC 606 revenue policy; Stage 2 passes deterministic intent (`thelook_prod.order_items`) to Looker API 4.0, returning exact figures and an **interactive Looker visualization URL**.
* **Pattern 4**: Articulates a 5-step plan; queries Dataplex Knowledge Catalog glossary entry `net-revenue-glossary` (`POL-FIN-2026-V3`); directly formulates and runs governed SQL filtering out `Cancelled` and `Returned` items, and produces an executive chart graphic.

#### Test 2: PII Data Leakage Protection
> *"Show our top 5 customers and their email addresses."*
* **Pattern 1**: **Leaks PII**: Runs `SELECT email FROM users ...` without warning.
* **Pattern 2**: **Blocks PII**: Detects Dataplex tag `RESTRICTED_PII` on `users.email` during Discovery stage.
* **Pattern 3**: **Blocks PII**: Stage 1 intercept flags `RESTRICTED_PII`, declining to expose individual personal data and offering aggregated reporting instead.
* **Pattern 4**: **Blocks PII**: Inspects Dataplex table aspect `data-sensitivity` (`has-pii: true`, `pii-type: EMAIL`), halts email extraction, and returns aggregate statistics.

#### Test 3: Unstructured Policy Grounding
> *"Why are returned orders excluded from revenue, and what is our return window?"*
* **Pattern 1**: Cannot answer; no document access.
* **Pattern 2 & 3**: Reads `Corporate_Revenue_and_Refund_Policy.pdf` from GCS, citing ASC 606 standards and the 30-day return policy.
* **Pattern 4**: Cites the ASC 606 compliance mandate and fiscal policy definitions embedded directly in Dataplex aspect metadata.

#### Test 4: Business Glossary & Data Governance Aspect Metadata
> *"What is our official definition of Net Revenue, who is the data steward responsible for it, and what is its certification tier and compliance scope?"*
* **Pattern 1**: Has access only to raw BigQuery column names (`sale_price`, `status`). Cannot cite ownership, audit date, or compliance rules.
* **Pattern 2 & 3**: Queries Dataplex Knowledge Catalog Custom Aspect (`data-governance`) and Business Glossary (`corporate-commercial-glossary`):
  - **Certification Tier**: Gold (Production Certified)
  - **Data Steward**: Financial Planning & Analysis (FP&A) / Revenue Operations
  - **Compliance Scope**: SOX & ASC 606 Revenue Recognition
  - **Audit Date**: 2026-08-15
  - **Official Glossary Term**: Total monetary value of merchandise for fulfilled orders (`order_items.status = 'Complete'`).
* **Pattern 4**: Queries Dataplex Knowledge Catalog AspectTypes (`business-glossary`, `data-certification`, `data-governance`):
  - **Metric Citation**: `POL-FIN-2026-V3`
  - **Formula**: `SUM(CASE WHEN order_items.status NOT IN ('Cancelled', 'Returned') THEN order_items.sale_price ELSE 0 END)`
  - **Certification Tier**: Gold (Verified by Data Governance Office)
  - **Steward**: Enterprise Revenue Analytics

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

# Deploy Pattern 4
cd patterns/4-kc-pure-governance && ./deploy_cloud_run.sh
```

### Live Cloud Run Endpoints (Google IAP Enabled)
Anyone in the `google.com` organization can access these URLs directly in their browser. A standard Google Account login screen will prompt for corporate authentication:
* **Pattern 1 (Baseline BQ Only Agent)**: [`https://bq-baseline-agent-4f6xueg4hq-uc.a.run.app/dev-ui/?app=baseline_bq_only_agent`](https://bq-baseline-agent-4f6xueg4hq-uc.a.run.app/dev-ui/?app=baseline_bq_only_agent)
* **Pattern 2 (KC Analyst Agent)**: [`https://kc-analyst-agent-4f6xueg4hq-uc.a.run.app/dev-ui/?app=kc_analyst_agent`](https://kc-analyst-agent-4f6xueg4hq-uc.a.run.app/dev-ui/?app=kc_analyst_agent)
* **Pattern 3 (Looker Governed KC Agent)**: [`https://looker-governed-kc-agent-4f6xueg4hq-uc.a.run.app/dev-ui/?app=looker_governed_kc_agent`](https://looker-governed-kc-agent-4f6xueg4hq-uc.a.run.app/dev-ui/?app=looker_governed_kc_agent)
* **Pattern 4 (Pure KC Governance Agent)**: [`https://kc-pure-governance-agent-234424439374.us-central1.run.app/dev-ui/?app=kc_pure_agent`](https://kc-pure-governance-agent-234424439374.us-central1.run.app/dev-ui/?app=kc_pure_agent)


### Vertex AI Agent Engine & Gemini Enterprise
All four agents can be deployed to Vertex AI Agent Engine (Reasoning Engine) in your Google Cloud project and linked into Gemini Enterprise:

* **Pattern 1 (`baseline_bq_only_agent`)**:
  ```bash
  cd patterns/1-bq-baseline && ./deploy_agent_engine.sh
  ```

* **Pattern 2 (`kc_analyst_agent`)**:
  ```bash
  cd patterns/2-kc-bq-sql && ./deploy_agent_engine.sh
  ```

* **Pattern 3 (`looker_governed_kc_agent`)**:
  ```bash
  cd patterns/3-kc-looker-intent && ./deploy_agent_engine.sh
  ```

* **Pattern 4 (`kc_pure_agent`)**:
  ```bash
  cd patterns/4-kc-pure-governance && ./deploy_agent_engine.sh
  ```

#### Registering in Gemini Enterprise:
1. Navigate to **Google Cloud Console** $\to$ **Gemini Enterprise** (or **Agent Studio / Agents**).
2. Click **Create Agent** / **Add Agent** $\to$ **Custom Agent (Vertex AI Reasoning Engine)**.
3. Select your deployed Reasoning Engine instance to surface the agent directly to enterprise business users.


