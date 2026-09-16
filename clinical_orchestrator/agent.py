"""
Primary Agent: Clinical Orchestrator
--------------------------------------
Entry-point agent exposed to Agent Gateway. Coordinates the two sub-agents
(Clinical Data Extractor -> Coverage & Prior-Auth Evaluator) and compiles the
final structured summary shown in the Gemini Enterprise chat surface.

Payload handling note (per roadmap doc): this agent is invoked via ADK's
standard unary request/response (`query`) path rather than a custom
streaming protocol, specifically so that Model Armor's ingress/egress
inspection at Agent Gateway has a fully-supported payload shape to inspect.
Custom streaming payloads outside the documented ADK streamQuery path are
NOT guaranteed to be sent to Model Armor -- don't build around them for a
compliance demo.
"""

from google.adk.agents import LlmAgent

from ..sub_agents.clinical_extractor.agent import clinical_extractor_agent
from ..sub_agents.coverage_evaluator.agent import coverage_evaluator_agent

ORCHESTRATOR_INSTRUCTION = """
You are the Clinical Intake & Prior-Authorization Triage orchestrator.

You have two specialist sub-agents:
1. clinical_data_extractor -- turns a raw clinical note into structured JSON.
2. coverage_prior_auth_evaluator -- takes that JSON and returns a
   deterministic prior-authorization verdict.

For every user request containing a clinical note:
1. Delegate the raw note to clinical_data_extractor first. Wait for its
   structured JSON output.
2. Pass that JSON to coverage_prior_auth_evaluator. Wait for its verdict.
3. Compile a single, clear response for a Clinical Intake Coordinator /
   Prior-Auth Triage Nurse containing:
   - A clean structured clinical summary (no raw SSNs, DOBs, or other
     identifiers beyond what's needed for the triage decision -- those are
     handled at the gateway, but do not gratuitously repeat identifiers back
     either).
   - The triage status (e.g. "Prior Authorization Required -- Criteria
     Satisfied", "Documentation Deficient", "Fast-Track Approved").
   - Any missing documentation, phrased as a next action (e.g. draft an RFI).

You do not have a tool to modify patient records, insurance status, or any
other write operation. If asked to perform a write/modify action, refuse
and state that record modification is outside this agent's authorized
tool scope -- do not attempt it and do not simulate having done it.

Never fabricate a policy criterion or coverage rule -- only state what the
coverage_prior_auth_evaluator sub-agent actually returned.
"""

root_agent = LlmAgent(
    name="clinical_intake_orchestrator",
    model="gemini-2.5-flash",
    description=(
        "Parent orchestrator for the Patient Intake & Prior-Authorization "
        "Triage multi-agent system."
    ),
    instruction=ORCHESTRATOR_INSTRUCTION,
    sub_agents=[clinical_extractor_agent, coverage_evaluator_agent],
)
