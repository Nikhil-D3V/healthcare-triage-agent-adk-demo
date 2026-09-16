"""
This module intentionally does NOT implement a working
`modify_patient_records` tool.

For the live demo scenario ("Agent Gateway blocks unauthorized tool calls"),
the correct architecture is:
  - The orchestrator agent is never given a callable `modify_patient_records`
    FunctionTool at all (defense in depth), AND
  - Agent Gateway's authorization policy denies the tool at the gateway layer
    for the demo service account/identity (see
    /security/model_armor_agent_gateway_config.yaml).

If you want the LLM to *attempt* the call so the audience sees the request
leave the agent and get denied at the gateway, register a stub tool that
raises a clear PermissionError locally, so even a misconfigured gateway
cannot accidentally let a write through in front of an audience:
"""


def modify_patient_records(*args, **kwargs):
    raise PermissionError(
        "modify_patient_records is not an authorized tool for this agent "
        "identity. This call should never reach here in the deployed "
        "topology -- Agent Gateway must deny it before it does. "
        "This stub exists only so a local misconfiguration fails loudly "
        "instead of silently 'succeeding'."
    )
