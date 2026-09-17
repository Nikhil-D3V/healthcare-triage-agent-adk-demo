"""Local A2A server entry point for the clinical orchestrator."""

from google.adk.a2a.utils.agent_to_a2a import to_a2a

from .agent import root_agent
from .agent_card import agent_card


# Run with:
# uvicorn healthcare_triage_agent.clinical_orchestrator.a2a_server:a2a_app
#     --host 0.0.0.0 --port 8000
a2a_app = to_a2a(
    root_agent,
    host="localhost",
    port=8000,
    agent_card=agent_card,
)
