#!/usr/bin/env python3
"""End-to-end Vertex AI Looker Analyst Agent runner and demo script."""

import asyncio
import os
import sys

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from looker_analyst_agent.agent import root_agent

# Ensure Vertex AI configuration
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "haengeun-429200")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")


async def ask_analyst(question: str):
    """Run a question through the Looker Knowledge Catalog & BigQuery Analyst Agent."""
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="looker_analyst_app",
        user_id="haengeun",
    )
    runner = Runner(
        agent=root_agent,
        app_name="looker_analyst_app",
        session_service=session_service,
    )

    print(f"\n==================================================================")
    print(f"USER QUESTION: {question}")
    print(f"==================================================================\n")

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=question)],
    )

    async for event in runner.run_async(
        user_id="haengeun",
        session_id=session.id,
        new_message=content,
    ):
        # Log tool calls made by the agent
        if event.get_function_calls():
            for fc in event.get_function_calls():
                print(f"[Agent Tool Call] -> {fc.name}({fc.args})")
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print("\n--- AGENT FINAL RESPONSE ---\n")
                    print(part.text)


if __name__ == "__main__":
    default_q = (
        "What is our total Net Revenue, total completed orders count, and Net Average Order Value (Net AOV) "
        "by user country for the top 5 countries? Use the Looker customer_orders Explore metadata "
        "and certified LookML definitions from Knowledge Catalog."
    )
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else default_q
    asyncio.run(ask_analyst(query))
