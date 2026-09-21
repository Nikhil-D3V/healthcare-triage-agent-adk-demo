"""A2A Agent Card for the clinical intake triage agent."""

from a2a.types import AgentSkill
from vertexai.preview.reasoning_engines.templates.a2a import create_agent_card


clinical_intake_skill = AgentSkill(
    id="clinical_intake_triage",
    name="Clinical Intake Triage",
    description=(
        "Parses clinical notes, evaluates payer policy criteria in BigQuery, "
        "and generates prior-authorization determination reports."
    ),
    tags=["clinical-intake", "prior-authorization", "healthcare"],
    examples=["Evaluate this clinical note for prior authorization."],
    input_modes=["text/plain"],
    output_modes=["text/plain"],
)

agent_card = create_agent_card(
    agent_name="Clinical Intake Triage",
    description=(
        "Automated healthcare intake and prior-authorization triage agent. "
        "Evaluates clinical medical necessity against payer policy rules and member eligibility."
    ),
    skills=[clinical_intake_skill],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
)

agent_card.url = "https://localhost:8000/"