# Grounding BigQuery Conversational Analytics with Knowledge Catalog & Looker Semantic Layer

Welcome! In this codelab, you will build a governed Data Analytics Agent using **Dataplex Knowledge Catalog**, **Looker's Native Semantic Layer (`@looker`)**, and the **BigQuery Conversational Analytics API (BQ CA API)**.

---

## Step 1: Configure Your GCP Project, Enable APIs & Grant Looker Schema Viewer

When **Looker (Google Cloud core)** is provisioned in your project, Dataplex Knowledge Catalog **automatically syncs your Looker Views, Explores, Models, and Dashboards** into the native **`@looker` entry group** (`system=looker`).

To allow your user and agent to discover and read native `@looker` entries in Knowledge Catalog, grant the `roles/looker.schemaViewer` role and enable the required APIs:

```bash
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
echo "Using project: $GOOGLE_CLOUD_PROJECT"

gcloud services enable \
  dataplex.googleapis.com \
  bigquery.googleapis.com \
  geminidataanalytics.googleapis.com \
  aiplatform.googleapis.com \
  --project="$GOOGLE_CLOUD_PROJECT"

# Required IAM role to access native @looker entries in Knowledge Catalog
gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
  --member="user:$(gcloud config get-value account)" \
  --role="roles/looker.schemaViewer"
```

Click **Next** once the APIs and IAM binding are applied.

---

## Step 2: Install Dependencies

Create a Python virtual environment and install the Google ADK, Dataplex, and Gemini Data Analytics (BQ CA) libraries:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Click **Next** once the installation completes.

---

## Step 3: Verify Native `@looker` Entries & Enrich with LookML SQL Formulas

First, verify what Looker assets (`@looker`) are already automatically synced in Knowledge Catalog:

```bash
gcloud dataplex entries list \
  --entry-group=@looker \
  --location=global \
  --project="$GOOGLE_CLOUD_PROJECT"
```

> **Why Enrichment?**
> Native 1P Looker-to-Dataplex sync automatically populates the `schema` aspect (LookML dimension/measure names, types, and descriptions) and `looker-view`/`looker-explore` aspects. However, it does not copy the raw LookML `sql:` expression text (e.g., `SUM(sale_price - cost)`).

Run <walkthrough-editor-open-file filePath="publish_looker_to_kc.py">publish_looker_to_kc.py</walkthrough-editor-open-file> to find your existing native `@looker` entry (`order_items`) and enrich its `overview` aspect with the exact LookML SQL formulas from <walkthrough-editor-open-file filePath="sample_thelook_ecommerce/order_items.view.lkml">sample_thelook_ecommerce/order_items.view.lkml</walkthrough-editor-open-file>:

```bash
python3 publish_looker_to_kc.py --project "$GOOGLE_CLOUD_PROJECT"
```

---

## Step 4: Inspect the Grounded Agent & Launch ADK Web UI

Open <walkthrough-editor-open-file filePath="codelab_agent/agent.py">codelab_agent/agent.py</walkthrough-editor-open-file> to see how the agent connects Knowledge Catalog and BigQuery Conversational Analytics:
1. `search_looker_knowledge_catalog`: Searches Dataplex for `system=looker` and extracts both the native `schema` aspect (LookML dimensions & measures) and the enriched `overview` aspect.
2. `call_bigquery_conversational_analytics`: Passes the governed LookML formulas directly into BQ CA's `system_instruction`.

Start the interactive ADK Web UI:

```bash
adk web --port 8000
```

Now click the <walkthrough-web-preview-icon></walkthrough-web-preview-icon> **Web Preview** icon in the top right of Cloud Shell and select **Preview on port 8000**.

---

## Step 5: Test the "Aha!" Moment

In the ADK Web UI:
1. Select **`codelab_agent`** from the top-left dropdown.
2. Ask:
   `What was our Total Gross Margin ($) and Net Realized Revenue in 2024?`

Observe how the agent:
1. Discovers the native `@looker` entry (`order_items`) in Knowledge Catalog.
2. Injects the LookML `WHERE status NOT IN ('Cancelled', 'Returned')` and `inventory_items.cost` join into **BigQuery Conversational Analytics**.
3. Generates 100% accurate, governed BigQuery SQL!

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy> Congratulations! You have built a Knowledge Catalog & Looker Semantic Layer grounded AI agent!
