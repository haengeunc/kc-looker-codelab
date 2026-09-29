# Pattern 4: Looker-Free Dataplex-Governed Analyst Agent

## Architecture Overview

Pattern 4 showcases how an AI Agent built on Vertex AI can perform complex, governed enterprise data analysis and visual charting using **ONLY** Google Cloud Dataplex Knowledge Catalog metadata (business glossaries, schema definitions, custom aspects, and table relationships) to formulate and execute direct BigQuery SQL—without needing or accessing any Looker or LookML assets.

```
                      +------------------------------------------+
                      |   Vertex AI ADK Sovereign Agent          |
                      |   (Pattern 4: Looker-Free Governance)    |
                      +--------------------+---------------------+
                                           |
                    +----------------------+----------------------+
                    |                      |                      |
                    v                      v                      v
        +-----------------------+ +------------------+ +----------------------+
        | search_catalog        | | get_current_date | | execute_query        |
        | get_catalog_metadata  | |                  | |                      |
        +-----------+-----------+ +--------+---------+ +----------+-----------+
                    |                      |                      |
                    | (MCP JSON-RPC)       | (Fiscal Bounds)      | (MCP JSON-RPC)
                    v                      v                      v
        +-----------------------+ +------------------+ +----------------------+
        | Managed Dataplex MCP  | | Offset: 1 (Feb)  | | Managed BigQuery MCP |
        | dataplex.googleapis   | | FQ2: May 1-Jul 31| | bigquery.googleapis  |
        +-----------+-----------+ +------------------+ +----------+-----------+
                    |                                             |
                    v                                             v
        +-----------------------------------+         +-----------------------+
        | Dataplex Knowledge Catalog        |         | Google BigQuery       |
        | Target Project                    |         | Target Project        |
        |                                   |         |                       |
        | • AspectTypes:                    |         | • Tables:             |
        |   - business-glossary             |         |   - order_items       |
        |   - table-relationships           |         |   - users             |
        |   - data-sensitivity (PII: EMAIL) |         |   - products          |
        |   - data-certification (Gold)     |         |   - orders            |
        | • Entries:                        |         |                       |
        |   - net-revenue-glossary (ASC 606)|         | Direct GoogleSQL Exec |
        |   - fiscal-calendar-glossary      |         | With Governed JOINs   |
        |   - thelook-table-relationships   |         | & PII Masking/Block   |
        +-----------------------------------+         +-----------------------+
```

---

## Live Data Flow

1. **User Query Received**:
   The user asks an analytical question involving business metrics, time periods, and potential customer data:
   > *"What was our Net Revenue in South Korea for last fiscal quarter? Do we have any customer emails?"*

2. **Mandatory Planning Step**:
   The agent begins by articulating its 5-step execution plan:
   - Step 1: Inspect Dataplex Catalog & Governance Glossary for metric formulas and join keys.
   - Step 2: Resolve calendar & fiscal period boundaries.
   - Step 3: Inspect table schemas and compliance aspects (PII check).
   - Step 4: Formulate and execute governed BigQuery SQL.
   - Step 5: Synthesize findings and render visual chart.

3. **Pure Knowledge Catalog Metadata Discovery**:
   - `search_catalog(query="revenue")` & `get_catalog_metadata(entry_name=".../net-revenue-glossary")`:
     Extracts the ASC 606 Net Revenue formula:
     `SUM(CASE WHEN order_items.status NOT IN ('Cancelled', 'Returned') THEN order_items.sale_price ELSE 0 END)`
     under citation `POL-FIN-2026-V3`.
   - `search_catalog(query="fiscal")` & `get_catalog_metadata(entry_name=".../fiscal-calendar-glossary")`:
     Extracts fiscal month offset 1 (fiscal year starts February 1) under citation `POL-CAL-2026-V1`.
   - `search_catalog(query="relationship")` & `get_catalog_metadata(entry_name=".../thelook-table-relationships")`:
     Extracts governed foreign keys: `order_items.user_id = users.id`.
   - `get_catalog_metadata(entry_name=".../tables/users")`:
     Discovers `data-sensitivity` aspect with `has-pii: true` and `pii-type: EMAIL`.

4. **Deterministic Fiscal Calculation**:
   - Calls `get_current_datetime(fiscal_month_offset=1)` to resolve fiscal quarter date boundaries.
   - Maps to the latest completed fiscal quarter in the database (`2024-05-01` to `2024-07-31`).

5. **BigQuery SQL Formulation & Execution**:
   - Invokes `execute_query` routing to the official Managed BigQuery MCP (`execute_sql_readonly`).
   - Executes multi-table JOIN using Dataplex-certified join keys and applying PII suppression.

6. **Executive Chart Generation & Response**:
   - Invokes `generate_data_chart` passing monthly data points (`May 2024`, `June 2024`, `July 2024`).
   - Generates an executive Matplotlib base64 PNG bar chart.
   - Transparently states PII policy compliance restricting raw customer email addresses.

---

## File Structure

```
patterns/4-kc-pure-governance/
├── __init__.py                # Package exports
├── agent.py                   # ADK LlmAgent definition (root_agent)
├── agent_instructions.txt     # Sovereign Data Analyst instructions & governance directives
├── kc_pure_mcp_server.py      # FastMCP Server (Dataplex MCP, BigQuery MCP, Matplotlib)
├── demo_test.py               # End-to-end automated verification script
├── requirements.txt           # Python dependencies
└── README.md                  # Conceptual architecture and workflow documentation
```

---

## Verification Results

Running `./demo_test.py`:
- 1. Outlines execution plan: **PASSED**
- 2. Searches Dataplex catalog: **PASSED**
- 3. Reads Dataplex glossary: **PASSED**
- 4. Resolves fiscal quarter dates: **PASSED**
- 5. Multi-table JOIN query in BigQuery: **PASSED**
- 6. PII compliance (email protected): **PASSED**
- 7. Generates visual chart: **PASSED**

**Overall Test Result**: **SUCCESS (All 7 assertions verified)**
