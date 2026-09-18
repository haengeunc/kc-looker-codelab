#!/usr/bin/env python3
"""End-to-end runner and test script for the Looker & Knowledge Catalog Governed Agent."""

import asyncio
import os
import sys

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from looker_governed_kc_agent.agent import PROJECT_ID, root_agent

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", PROJECT_ID)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"))


async def ask_analyst(question: str):
    """Run a question through the Governed Looker & Knowledge Catalog Analyst Agent."""
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="looker_governed_app",
        user_id="governed_demo_user",
    )
    runner = Runner(
        agent=root_agent,
        app_name="looker_governed_app",
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
        user_id="governed_demo_user",
        session_id=session.id,
        new_message=content,
    ):
        # Log tool calls made by the agent
        if event.get_function_calls():
            for fc in event.get_function_calls():
                print(f"[Governed Tool Call] -> {fc.name}({fc.args})")
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print("\n--- AGENT GOVERNED RESPONSE ---\n")
                    print(part.text)


if __name__ == "__main__":
    default_q = (
        "What is our total Net Revenue and total completed orders count by user country for the top 5 countries? "
        "Include a visual chart and explain how Net Revenue is recognized according to our corporate policy document."
    )
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else default_q
    asyncio.run(ask_analyst(query))
