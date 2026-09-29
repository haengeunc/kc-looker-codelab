# Pattern 2: Looker-Grounded BigQuery Analyst Agent (Sequential 3-Stage Pipeline)

> **Pattern 2 of 3: Governed Text-to-SQL Architecture with Knowledge Catalog & BigQuery**

This application demonstrates an enterprise data analyst pipeline that bridges Knowledge Catalog (Dataplex) with BigQuery Standard SQL using a deterministic 3-stage sequential architecture:

1. **Stage 1 (`metadata_discovery_agent`)**: Discovers certified Looker Explores, Views, Joins, and LookML measure definitions from Google Cloud Knowledge Catalog (`@looker` entry group) and corporate governance policies from GCS.
2. **Stage 2 (`sql_execution_agent`)**: Compiles discovered LookML formulas into BigQuery Standard SQL and executes them against `opm-looker-core-demo-instance.thelook_ecommerce`.
3. **Stage 3 (`presentation_agent`)**: Formats executive summary tables, renders actual visual chart graphics (embedded PNG images), and provides Looker governance attributions strictly grounded in verified query results.

---

## Strict Data Dependency & Visualization Standards

1. **Strict Dependency Enforcement**:
   - The Presentation Agent only generates tables or charts after the SQL Execution Agent has successfully executed the BigQuery SQL query and returned genuine records (`### DATA_EXECUTION_PAYLOAD`).
   - If BigQuery returns 0 records or an error occurs, the Presentation Agent reports the factual result without generating empty or dummy charts.

2. **Zero Hypothetical Data**:
   - The Presentation Agent is strictly prohibited from inferring, estimating, or fabricating mock data or hypothetical categories. Every single number and label originates directly from the BigQuery execution payload.

3. **Direct Visual Chart Rendering**:
   - Visualizations are rendered directly as embedded image graphics (`generate_data_chart`) supporting Bar, Horizontal Bar, Line, Area, Scatter, and Pie charts.
   - Raw specification code (such as Vega-Lite JSON or Mermaid markup) is suppressed so end users see the rendered chart immediately in their chat stream.


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
