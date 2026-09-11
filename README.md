# Vertex AI Looker Knowledge Catalog & BigQuery Analyst Agent

An enterprise Data Analyst Agent built with the **Google Agent Development Kit (`google-adk`)** and **Gemini 2.5 Pro** that answers analytical questions by combining:
1. **Google Cloud Knowledge Catalog (Dataplex)** — for Looker semantic layer metadata (Looker Explores, Looker Views, Join relationships, and LookML Measure SQL formulas).
2. **Google BigQuery** — for executing governed Standard SQL queries compiled directly from Looker definitions.

Can be run locally via the ADK Web UI, deployed as a container to **Google Cloud Run**, or deployed as a managed **Vertex AI Agent Engine** reasoning engine linked directly into **Gemini Enterprise (Google Agentspace)**.

---

## Repository Structure

```text
.
├── looker_analyst_agent/            # Core Vertex AI ADK Agent Package
│   ├── __init__.py                  # Exports root_agent for ADK CLI & Agent Engine
│   ├── agent.py                     # LlmAgent definition, tools & resilient auth bridge
│   ├── kc_bq_mcp_server.py          # MCP Tools for Knowledge Catalog (Dataplex) & BigQuery
│   ├── prompt.py                    # 4-stage governed analytical system prompt
│   └── requirements.txt             # Python dependencies for agent container
├── ARCHITECTURE_GUIDE.md            # Deep-dive architecture, design & troubleshooting guide
├── Dockerfile                       # Container definition for Cloud Run deployment
├── deploy_cloud_run.sh              # Automated Cloud Run deployment script (with ADK Web UI)
├── deploy_agent_engine.sh           # Automated Vertex AI Agent Engine deployment script (bash)
├── deploy_agent_engine.py           # Programmatic Vertex AI Agent Engine deployment script
├── run_demo_query.py                # CLI runner for testing governed queries locally
└── requirements.txt                 # Root development dependencies
```

---

## Minimum Requirements vs. Optional Custom Enrichments

### 1. Minimum Requirements (Out-of-the-Box Looker Sync)
To run this agent in your own Google Cloud environment, you only need:
1. **A Google Cloud Project** with BigQuery and Dataplex APIs enabled.
2. **Looker Metadata in Dataplex Knowledge Catalog**:
   - When you connect a Looker instance to Dataplex Knowledge Catalog, Dataplex automatically creates a native `@looker` entry group (`projects/YOUR-GCP-PROJECT/locations/<location>/entryGroups/@looker`) and syncs standard LookML aspects:
     - **`dataplex-types.global.looker-explore`**: Contains the Explore's `baseViewName`, `joins` array (`sqlOn`, `relationship`, `type`), and pre-built LookML queries.
     - **`dataplex-types.global.looker-view`**: Contains the underlying BigQuery `sourceTable` (`sql_table_name`) and LookML file path.
     - **`dataplex-types.global.schema`**: Contains every LookML dimension, dimension group, and measure along with its exact LookML `sql` expression (`annotations.sql`).

> **Note on Zero-Setup Demo Mode**: If your Dataplex Knowledge Catalog does not yet have a Looker instance connected, `check_lookml_in_knowledge_catalog` includes a built-in reference snapshot of the certified `customer_orders` LookML semantic model over `bigquery-public-data.thelook_ecommerce` so you can immediately test the agent out-of-the-box.

### 2. Optional Custom Enrichments (Custom Dataplex Aspect Types)
In addition to the standard LookML schema synced by Looker, you can optionally enrich your Looker Explores and Views in Dataplex Knowledge Catalog with **Custom Aspect Types** for enterprise governance.

For example, in our reference implementation, we created and attached custom governance aspects such as:
- **`data-certification-governance`**:
  - `Certified`: `True`
  - `Certification Tier`: `Gold`
  - `Environment`: `PRODUCTION`
  - `Data Owner`: `Finance & Revenue Operations`
- **`pii-security-compliance`**: Flags fields containing sensitive customer PII.
- **`business-glossary-domain`**: Maps technical Looker views to corporate business domains.

#### How to Create a Custom Governance Aspect Type in Dataplex (Optional)
If you want the agent to inspect and cite custom certification tiers (`Gold`, `Silver`, `Bronze`) on your Looker Explores, create a custom Aspect Type in your project:

```bash
export PROJECT_ID=$(gcloud config get-value project)

gcloud dataplex aspect-types create data-certification-governance \
  --project="$PROJECT_ID" \
  --location=us-central1 \
  --description="Enterprise Data Governance and Certification tier for Looker Explores and Views" \
  --metadata-template-file-name=aspect_template.json
```

---

## Step 1: Find Your GCP Project ID & Configure Environment

To find your active Google Cloud Project ID and Project Number:

```bash
# 1. Print your active GCP Project ID
gcloud config get-value project

# 2. Export your GCP Project ID and Region
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
export GOOGLE_CLOUD_LOCATION="us-central1"

# 3. Verify your Project Number (used for Service Account IAM bindings)
gcloud projects describe "$GOOGLE_CLOUD_PROJECT" --format="value(projectNumber)"
```

---

## Step 2: Run Locally with ADK Web UI

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Authenticate locally
gcloud auth login
gcloud auth application-default login

# 3. Test via CLI runner
python3 run_demo_query.py

# 4. Launch the interactive ADK Web UI
adk web --port 8000
```
Open `http://localhost:8000` in your browser and select `looker_analyst_agent`.

---

## Step 3: Deploy to Google Cloud Run

To deploy the agent as a scalable container on Cloud Run (with the ADK Web UI and A2A protocol enabled):

```bash
export GOOGLE_CLOUD_PROJECT="YOUR-GCP-PROJECT"
export GOOGLE_CLOUD_REGION="us-central1"

./deploy_cloud_run.sh
```
The script automatically grants the required Dataplex, Looker (`roles/looker.schemaViewer`), BigQuery, and Vertex AI IAM roles to your project's default Compute Engine service account before deploying.

---

## Step 4: Deploy to Vertex AI Agent Engine & Gemini Enterprise (Agentspace)

To deploy the agent to **Vertex AI Agent Engine (Reasoning Engine)** so it can be added as a Custom Agent in **Gemini Enterprise (Google Agentspace)**:

```bash
export GOOGLE_CLOUD_PROJECT="YOUR-GCP-PROJECT"
export GOOGLE_CLOUD_REGION="us-central1"

./deploy_agent_engine.sh
```

After deployment completes, the script outputs the Reasoning Engine resource path:
```text
projects/YOUR-GCP-PROJECT/locations/us-central1/reasoningEngines/YOUR_REASONING_ENGINE_ID
```

### Connecting to Gemini Enterprise (Agentspace)
1. Open **Google Cloud Console -> Gemini Enterprise (Agentspace) -> Agents**.
2. Click **Create Agent -> Custom Agent (Vertex AI Agent Engine)**.
3. Paste your Reasoning Engine resource path (`projects/YOUR-GCP-PROJECT/locations/us-central1/reasoningEngines/YOUR_REASONING_ENGINE_ID`).
4. Skip OAuth configuration (**Option A: Service Account Auth**) — the agent automatically authenticates using its Vertex AI Reasoning Engine Service Account via the GCP Metadata Server.
