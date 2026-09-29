# Pattern 2: Looker-Grounded BigQuery Analyst Agent (Sequential 3-Stage Pipeline)

> **Pattern 2 of 3: Governed Text-to-SQL Architecture with Knowledge Catalog & BigQuery**

This application demonstrates an enterprise data analyst pipeline that bridges Knowledge Catalog (Dataplex) with BigQuery Standard SQL using a deterministic 3-stage sequential architecture:

1. **Stage 1 (`metadata_discovery_agent`)**: Discovers certified Looker Explores, Views, Joins, and LookML measure definitions from Google Cloud Knowledge Catalog (`@looker` entry group) and corporate governance policies from GCS.
2. **Stage 2 (`sql_execution_agent`)**: Compiles discovered LookML formulas into BigQuery Standard SQL and executes them against `opm-looker-core-demo-instance.thelook_ecommerce`.
3. **Stage 3 (`presentation_agent`)**: Formats executive summary tables, renders rich interactive visualizations (**Vega-Lite v5 JSON** adhering to Google Cloud Conversational Analytics API standards, Mermaid diagrams, or Matplotlib PNGs), and provides Looker governance attributions.

---

## Interactive Visualization Standards (Vega-Lite)

Following Google Cloud Conversational Analytics API visualization standards, Pattern 2 generates native **Vega-Lite v5 JSON specifications** (`generate_vega_lite_chart`) supporting:
- **Area**: Monthly or cumulative trends with gradient fills
- **Bar / Horizontal Bar**: Categorical metrics with formatted tooltips and rounded bar corners
- **Line / Timeseries**: High-resolution trend analysis with data markers
- **Pie / Donut**: Categorical share-of-total distributions with Tableau-10 color schemes
- **Scatter**: Multivariable distributions and correlation analysis
- **Heatmap**: 2D categorical density grids

Vega-Lite outputs can be rendered directly by any client library in the Vega ecosystem (including Altair in Python notebooks or Vega-Embed in web UIs).

---

## Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the agent via CLI
python3 run_demo_query.py "What is our total Net Revenue and total completed orders by user country for the top 5 countries? Include a visual chart."

# 3. Launch ADK Web UI
adk web --port 8081 kc_analyst_agent
```

Visit `http://localhost:8081/dev-ui/?app=kc_analyst_agent`.

---

## Deploying to Google Cloud

### Cloud Run (with ADK Web UI)
```bash
./deploy_cloud_run.sh
```

### Vertex AI Agent Engine (for Gemini Enterprise)
```bash
./deploy_agent_engine.sh
```
