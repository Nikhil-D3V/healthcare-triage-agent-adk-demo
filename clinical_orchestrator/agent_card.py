"""A2A Agent Card for the clinical intake triage agent."""

from a2a.types import AgentSkill
from vertexai.preview.reasoning_engines.templates.a2a import create_agent_card


clinical_intake_skill = AgentSkill(
    id="clinical_intake_triage",
    name="Clinical Intake Triage",
    description=(
        "Parses a clinical intake note, determines CPT/ICD-10 codes, and "
        "returns a prior-authorization determination."
    ),
    tags=["clinical-intake", "prior-authorization", "healthcare"],
    examples=["Evaluate this clinical note for prior authorization."],
    input_modes=["text/plain"],
    output_modes=["text/plain"],
)

agent_card = create_agent_card(
    agent_name="clinical-intake-prior-auth-triage",
    description=(
        "Multi-agent healthcare intake and prior-authorization triage. "
        "Parses clinical notes, evaluates coverage criteria, and returns "
        "a documented determination."
    ),
    skills=[clinical_intake_skill],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
)
# The local to_a2a server advertises this URL; Agent Runtime rewrites it to
# the managed A2A endpoint during A2aAgent.set_up().
# Strip out the local _forced_https_setattr monkey-patch
agent_card.url = "https://localhost:8000/"
