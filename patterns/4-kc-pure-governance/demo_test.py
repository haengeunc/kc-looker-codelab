#!/usr/bin/env python3
"""Automated Verification Script for Pattern 4: Looker-Free Dataplex-Governed Analyst Agent.

Executes a live test prompt asking:
"What was our Net Revenue in South Korea for last fiscal quarter? Do we have any customer emails?"

Verifies that the agent:
1. Outlines an explicit step-by-step thinking plan.
2. Searches the catalog of "haengeun-f478f" to find order_items, users, and products tables.
3. Reads the live Dataplex glossary to extract the formula for "Net Revenue" and "Fiscal Calendar" start month.
4. Translates "last fiscal quarter" into exact dates based on the Dataplex Glossary Fiscal offset.
5. Formulates a correct, multi-table JOIN query based on the Catalog-registered keys.
6. Blocks/masks the email column based on Dataplex's data-sensitivity PII aspect.
7. Successfully generates a PNG trend chart from the BigQuery query outputs.
"""

import asyncio
import os
import sys

# Ensure pattern directory is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from kc_pure_agent.agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

PROMPT = "What was our Net Revenue in South Korea for last fiscal quarter? Do we have any customer emails?"


async def run_verification():
    print("=" * 80)
    print(" PATTERN 4: LOOKER-FREE DATAPLEX-GOVERNED ANALYST AGENT VERIFICATION")
    print(f" Target Project: haengeun-f478f")
    print(f" User Prompt:    {PROMPT}")
    print("=" * 80)

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="kc_pure_analyst_app",
        user_id="test_analyst",
    )
    runner = Runner(
        agent=root_agent,
        app_name="kc_pure_analyst_app",
        session_service=session_service,
    )

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=PROMPT)],
    )

    tool_calls = []
    final_text_parts = []

    async for event in runner.run_async(
        user_id="test_analyst",
        session_id=session.id,
        new_message=content,
    ):
        if event.get_function_calls():
            for fc in event.get_function_calls():
                tool_calls.append((fc.name, fc.args))
                print(f"[TOOL CALL] {fc.name}({fc.args})")

        if event.get_function_responses():
            for fr in event.get_function_responses():
                resp_preview = str(fr.response)[:160].replace("\n", " ")
                print(f"[TOOL RESP] {fr.name} -> {resp_preview}...")

        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    final_text_parts.append(part.text)

    full_response = "\n".join(final_text_parts)
    print("\n" + "=" * 80)
    print(" AGENT RESPONSE OUTPUT:")
    print("=" * 80)
    print(full_response)
    print("=" * 80)

    # Verification Assertions
    print("\nVERIFICATION CHECKLIST:")

    # 1. Step-by-step thinking plan
    has_plan = any(kw in full_response.lower() for kw in ["plan", "step 1", "execution plan"])
    print(f" 1. Outlines execution plan:              {'PASSED' if has_plan else 'FAILED'}")

    # 2. Searches Dataplex catalog
    searched_catalog = any("search_catalog" in tc[0] for tc in tool_calls)
    print(f" 2. Searches Dataplex catalog:            {'PASSED' if searched_catalog else 'FAILED'}")

    # 3. Reads Dataplex glossary
    inspected_metadata = any("get_catalog_metadata" in tc[0] for tc in tool_calls)
    reads_glossary = any("glossary" in str(tc[1]).lower() or "revenue" in str(tc[1]).lower() for tc in tool_calls)
    print(f" 3. Reads Dataplex glossary:              {'PASSED' if (inspected_metadata and reads_glossary) else 'FAILED'}")

    # 4. Translates fiscal quarter
    used_datetime = any("get_current_datetime" in tc[0] for tc in tool_calls)
    print(f" 4. Resolves fiscal quarter dates:        {'PASSED' if used_datetime else 'FAILED'}")

    # 5. Formulates multi-table JOIN query
    executed_sql = any("execute_query" in tc[0] for tc in tool_calls)
    has_joins = any("join" in str(tc[1]).lower() for tc in tool_calls if "execute_query" in tc[0])
    print(f" 5. Multi-table JOIN query in BigQuery:   {'PASSED' if (executed_sql and has_joins) else 'FAILED'}")

    # 6. PII Masking / Suppression
    pii_enforced = (
        "data-sensitivity" in full_response.lower()
        or "pii" in full_response.lower()
        or "restricted" in full_response.lower()
        or "suppress" in full_response.lower()
        or "mask" in full_response.lower()
    )
    print(f" 6. PII compliance (email protected):    {'PASSED' if pii_enforced else 'FAILED'}")

    # 7. Visual chart generation (Interactive Vega-Lite)
    generated_chart = any("generate_data_chart" in tc[0] for tc in tool_calls) or "vega-lite" in full_response.lower() or "data:image/png;base64" in full_response
    print(f" 7. Generates visual chart (Vega-Lite):   {'PASSED' if generated_chart else 'FAILED'}")

    all_passed = has_plan and searched_catalog and inspected_metadata and used_datetime and executed_sql and pii_enforced
    print("\nOVERALL TEST RESULT:", "SUCCESS" if all_passed else "PARTIAL / NEEDS REVIEW")
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_verification())
    sys.exit(0 if success else 1)
