"""
Sub-Agent 2: Coverage & Prior-Auth Evaluator
----------------------------------------------
Consumes the structured JSON produced by the Clinical Data Extractor,
calls deterministic mock policy/eligibility tools, and returns a strict
prior-authorization verdict. The LLM's job here is narrow: call the right
tool with the right arguments and phrase the result -- it must not invent
policy criteria that didn't come back from the tool.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from .tools import check_coverage_policy, check_member_eligibility

EVALUATOR_INSTRUCTION = """
You are a Coverage & Prior-Authorization Evaluator. You receive structured
clinical JSON (diagnosis, procedure/CPT code, payer, conservative-therapy
history) from the upstream extraction step.

Your job:
1. Call `check_coverage_policy` with the CPT code (and payer_id if present).
2. If a member ID and payer are present, call `check_member_eligibility`.
3. Compare the conservative-therapy history in the input JSON against the
   `criteria` list returned by the tool.
4. Return a structured verdict as JSON:

{
  "prior_auth_required": boolean or null,
  "status": "APPROVED_FAST_TRACK" | "CRITERIA_SATISFIED" | "DOCUMENTATION_DEFICIENT" | "NOT_FOUND",
  "criteria_met": [list of criteria strings that were satisfied],
  "criteria_missing": [list of criteria strings NOT satisfied or not documented],
  "next_action": string  # e.g. "Ready for 1-click pre-auth submission" or
                          # "Draft RFI to ordering provider requesting conservative therapy history"
}

Hard rule: you may ONLY use policy criteria that came back from
`check_coverage_policy`. Never state a criterion, threshold, or exemption
that the tool did not return -- if the tool returns found=false, your status
must be "NOT_FOUND" and next_action must recommend human escalation.
"""

coverage_evaluator_agent = LlmAgent(
    name="coverage_prior_auth_evaluator",
    model="gemini-2.5-flash",
    description=(
        "Deterministically evaluates prior-authorization requirements and "
        "medical-necessity criteria against a mock payer policy table."
    ),
    instruction=EVALUATOR_INSTRUCTION,
    tools=[
        FunctionTool(func=check_coverage_policy),
        FunctionTool(func=check_member_eligibility),
    ],
)
