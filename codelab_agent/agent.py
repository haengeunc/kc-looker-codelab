"""Minimal Cloud Shell Codelab Agent: Knowledge Catalog + Native Looker Semantic Layer + BigQuery CA API.

This agent demonstrates how native Looker (Google Cloud core) semantic entries (`@looker` in Dataplex
Knowledge Catalog) ground BigQuery Conversational Analytics (BQ CA API) to eliminate SQL hallucinations.
"""

import json
import os
import uuid
from google.adk.agents import LlmAgent
from google.api_core import client_options
import google.auth
from google.cloud import dataplex_v1
from google.cloud import geminidataanalytics_v1beta as geminidataanalytics
import google.protobuf.json_format as jsonpb

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "haengeun-429200")
OVERVIEW_ASPECT_KEY = "655216118709.global.overview"
SCHEMA_ASPECT_KEY = "655216118709.global.schema"

# Default tables from Looker's sample_thelook_ecommerce BigQuery connection
DEFAULT_THELOOK_TABLES = [
    {
        "project_id": "bigquery-public-data",
        "dataset_id": "thelook_ecommerce",
        "table_id": "order_items",
    },
    {
        "project_id": "bigquery-public-data",
        "dataset_id": "thelook_ecommerce",
        "table_id": "inventory_items",
    },
    {
        "project_id": "bigquery-public-data",
        "dataset_id": "thelook_ecommerce",
        "table_id": "orders",
    },
    {
        "project_id": "bigquery-public-data",
        "dataset_id": "thelook_ecommerce",
        "table_id": "users",
    },
    {
        "project_id": "bigquery-public-data",
        "dataset_id": "thelook_ecommerce",
        "table_id": "products",
    },
]


def search_looker_knowledge_catalog(query: str) -> str:
  """Searches Dataplex Knowledge Catalog for native Looker entries (`@looker`, system=looker).

  Extracts:
  1. Native `schema` aspect (LookML dimensions & measures synced automatically from Looker Core).
  2. Native `looker-view` / `looker-explore` aspect metadata.
  3. Any `overview` aspect or description attached to the entry.
  """
  client = dataplex_v1.CatalogServiceClient()
  location_name = f"projects/{PROJECT_ID}/locations/global"

  # Search across native 1P Looker entries (@looker / system=looker)
  req = dataplex_v1.SearchEntriesRequest(
      name=location_name,
      query=f"{query} system=looker",
      page_size=10,
      semantic_search=True,
  )
  results = list(client.search_entries(request=req).results)
  if not results:
    return (
        "No Looker entries found in Knowledge Catalog. Ensure Looker (Google Cloud core) "
        "is synced to Dataplex and your user has `roles/looker.schemaViewer`."
    )

  output = []
  for item in results:
    entry_name = item.dataplex_entry.name
    full_entry = client.get_entry(
        request=dataplex_v1.GetEntryRequest(name=entry_name, view="FULL")
    )
    entry_dict = jsonpb.MessageToDict(full_entry._pb)
    aspects = entry_dict.get("aspects", {})

    # 1. Extract native Looker Schema Aspect (Dimensions & Measures)
    schema_fields = (
        aspects.get(SCHEMA_ASPECT_KEY, {}).get("data", {}).get("fields", [])
    )
    fields_summary = []
    for f in schema_fields:
      fname = f.get("name", "")
      fdesc = f.get("description", "")
      ftype = f.get("dataType", "")
      fields_summary.append(f"  - `{fname}` ({ftype}): {fdesc}")

    # 2. Extract Overview Aspect (if present)
    overview_text = (
        aspects.get(OVERVIEW_ASPECT_KEY, {}).get("data", {}).get("content", "")
    )

    # 3. Extract any looker-view / looker-explore aspect details
    looker_aspect_dump = {}
    for k, v in aspects.items():
      if "looker" in k.lower():
        looker_aspect_dump[k] = v.get("data", {})

    entry_block = [
        f"=== Native Looker Entry in Knowledge Catalog: {entry_name} ===",
        f"Display Name: {entry_dict.get('entrySource', {}).get('displayName', '')}",
        f"Description: {entry_dict.get('entrySource', {}).get('description', '')}",
    ]
    if fields_summary:
      entry_block.append(
          "LookML Dimensions & Measures (from native `schema` aspect):\n"
          + "\n".join(fields_summary)
      )
    if looker_aspect_dump:
      entry_block.append(
          "Looker Aspect Metadata:\n" + json.dumps(looker_aspect_dump, indent=2)
      )
    if overview_text:
      entry_block.append(f"Enriched Semantic Overview:\n{overview_text}")

    output.append("\n".join(entry_block))

  return "\n\n".join(output)


def call_bigquery_conversational_analytics(
    question: str, lookml_grounding_rules: str
) -> str:
  """Calls BigQuery Conversational Analytics API (BQ CA) grounded with Looker semantic layer rules."""
  creds, _ = google.auth.default()
  opts = client_options.ClientOptions(
      api_endpoint="geminidataanalytics.googleapis.com"
  )
  agent_client = geminidataanalytics.DataAgentServiceClient(
      credentials=creds, client_options=opts
  )
  chat_client = geminidataanalytics.DataChatServiceClient(
      credentials=creds, client_options=opts
  )
  parent = f"projects/{PROJECT_ID}/locations/global"
  agent_id = f"codelab-ca-{uuid.uuid4().hex[:8]}"

  # Inject Looker Semantic Layer definitions directly into BQ CA's system instruction
  system_instruction = (
      "You are a BigQuery Analytics Engine connected to `bigquery-public-data.thelook_ecommerce`.\n"
      "CRITICAL GOVERNANCE RULE: When generating SQL, you MUST strictly apply the following "
      "Looker Semantic Layer measure definitions, filters, and join conditions:\n\n"
      f"{lookml_grounding_rules}"
  )

  inline_ctx = {
      "system_instruction": system_instruction,
      "datasource_references": {
          "bq": {"table_references": DEFAULT_THELOOK_TABLES}
      },
  }

  # 1. Create Ephemeral Data Agent in BQ CA
  data_agent = geminidataanalytics.DataAgent(
      display_name="KC Looker Grounded Agent",
      data_analytics_agent={"published_context": inline_ctx},
  )
  try:
    agent_resp = agent_client.create_data_agent(
        request=geminidataanalytics.CreateDataAgentRequest(
            parent=parent, data_agent_id=agent_id, data_agent=data_agent
        )
    ).result()
    agent_name = agent_resp.name
  except Exception:
    agent_name = f"{parent}/dataAgents/{agent_id}"

  # 2. Create Conversation & Send Question to BQ CA
  conv_name = chat_client.create_conversation(
      request=geminidataanalytics.CreateConversationRequest(
          parent=parent,
          conversation=geminidataanalytics.Conversation(
              agents=[agent_name], labels={"host": "bigquery"}
          ),
      )
  ).name

  responses = chat_client.chat(
      request=geminidataanalytics.ChatRequest(
          parent=parent,
          conversation_reference=geminidataanalytics.ConversationReference(
              conversation=conv_name,
              data_agent_context=geminidataanalytics.DataAgentContext(
                  data_agent=agent_name
              ),
          ),
          messages=[
              geminidataanalytics.Message(
                  user_message=geminidataanalytics.UserMessage(text=question)
              )
          ],
          thinking_mode=geminidataanalytics.ChatRequest.ThinkingMode.THINKING,
      )
  )

  # 3. Collect Generated SQL and Analytical Answer from BQ CA Stream
  final_answer = ""
  generated_sqls = []

  for chunk in responses:
    sys_msg = chunk.system_message
    if not sys_msg:
      continue
    if sys_msg.text and sys_msg.text.parts:
      final_answer += "".join(sys_msg.text.parts)
    if sys_msg.data and sys_msg.data.generated_sql:
      generated_sqls.append(sys_msg.data.generated_sql)

  sql_section = ""
  if generated_sqls:
    sql_section = (
        "\n\n### Governed SQL Generated by BigQuery CA\n```sql\n"
        + "\n\n".join(generated_sqls)
        + "\n```\n"
    )

  return f"{final_answer}{sql_section}"


INSTRUCTION = """You are an Enterprise Data Analytics Agent powered by Dataplex Knowledge Catalog, Looker Semantic Layer (`sample_thelook_ecommerce`), and BigQuery Conversational Analytics (BQ CA).

Follow this strict 2-step workflow for every analytical question:
1. **Step 1 — Discover Native Looker Semantic Layer in Knowledge Catalog**:
   Call `search_looker_knowledge_catalog` to retrieve the LookML views, explores, dimensions, and measure definitions automatically synced from Looker (under `@looker` / `system=looker`).
2. **Step 2 — Execute Grounded Query in BigQuery Conversational Analytics**:
   Call `call_bigquery_conversational_analytics` passing:
   - `question`: The user's original question.
   - `lookml_grounding_rules`: Paste the exact LookML measure definitions, descriptions, SQL formulas, and required `WHERE` filters you discovered from Knowledge Catalog in Step 1.

In your final answer:
- Cite which native Looker View/Explore entry (`@looker`) from Knowledge Catalog grounded your calculation.
- Present the governed SQL query generated by BigQuery CA and the final answer.
"""

root_agent = LlmAgent(
    name="kc_looker_bqca_agent",
    model="gemini-2.5-flash",
    instruction=INSTRUCTION,
    tools=[
        search_looker_knowledge_catalog,
        call_bigquery_conversational_analytics,
    ],
)
