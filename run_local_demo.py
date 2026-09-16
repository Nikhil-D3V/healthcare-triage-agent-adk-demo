"""
Quick local sanity-check runner (no Agent Gateway / Model Armor in this path
-- those only apply once deployed behind Agent Runtime + Gateway).

Usage:
    python run_local_demo.py synthetic_notes/note_01_tka_golden_path.txt

The project .env file is loaded automatically.
"""

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip('"\''))

from google.adk.runners import InMemoryRunner
from google.genai import types

from healthcare_triage_agent.clinical_orchestrator.agent import root_agent


async def main():
    if len(sys.argv) != 2:
        print("Usage: python run_local_demo.py <path-to-note.txt>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        note_text = f.read()

    runner = InMemoryRunner(agent=root_agent, app_name="clinical_triage_demo")
    session = await runner.session_service.create_session(
        app_name="clinical_triage_demo", user_id="demo_user"
    )

    prompt = (
        "Extract all clinical details, check payer authorization rules, "
        f"and generate a pre-auth package recommendation for this note:\n\n{note_text}"
    )

    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    async for event in runner.run_async(
        user_id="demo_user", session_id=session.id, new_message=message
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    print(part.text)


if __name__ == "__main__":
    asyncio.run(main())
