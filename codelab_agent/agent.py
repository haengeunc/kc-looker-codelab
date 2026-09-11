"""Minimal Cloud Shell Codelab Agent: Knowledge Catalog + Looker Semantic Layer + BigQuery CA API.

This agent demonstrates how Looker semantic definitions (published in Dataplex Knowledge Catalog)
ground BigQuery Conversational Analytics (BQ CA API) to eliminate SQL hallucinations.
"""

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
  """Searches Dataplex Knowledge Catalog for Looker semantic layer views, measures, and SQL definitions."""
  client = dataplex_v1.CatalogServiceClient()
  location_name = f"projects/{PROJECT_ID}/locations/global"

  req = dataplex_v1.SearchEntriesRequest(
      name=location_name,
      query=f"{query} system=Looker",
      page_size=5,
      semantic_search=True,
  )
  results = list(client.search_entries(request=req).results)
  if not results:
    return "No Looker semantic entries found in Knowledge Catalog."

  output = []
  for item in results:
    entry_name = item.dataplex_entry.name
    full_entry = client.get_entry(
        request=dataplex_v1.GetEntryRequest(name=entry_name, view="FULL")
    )
    entry_dict = jsonpb.MessageToDict(full_entry._pb)
    aspects = entry_dict.get("aspects", {})
    overview_text = (
        aspects.get(OVERVIEW_ASPECT_KEY, {}).get("data", {}).get("content", "")
    )
    output.append(
        f"=== Knowledge Catalog Entry: {entry_name} ===\n"
        f"{overview_text or entry_dict.get('description', '')}\n"
    )
  return "\n".join(output)


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
1. **Step 1 — Discover Looker Semantic Layer in Knowledge Catalog**:
   Call `search_looker_knowledge_catalog` to retrieve the official LookML measure definitions, SQL formulas, and filter rules (e.g. `total_gmv`, `net_revenue`, `total_gross_margin`, `return_rate`).
2. **Step 2 — Execute Grounded Query in BigQuery Conversational Analytics**:
   Call `call_bigquery_conversational_analytics` passing:
   - `question`: The user's original question.
   - `lookml_grounding_rules`: Paste the exact LookML measure definitions, SQL expressions, and required `WHERE` filters you discovered from Knowledge Catalog in Step 1.

In your final answer:
- Explain which Looker Semantic Layer definitions were retrieved from Knowledge Catalog.
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
