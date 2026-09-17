"""
This module intentionally does NOT implement a working
`modify_patient_records` tool.

For this specific tool, the primary enforcement mechanism is this
`PermissionError` stub, alongside the orchestrator's system instruction never
granting `modify_patient_records` as a callable tool. Agent Gateway has no
visibility into in-process Python calls in this architecture, so this is not a
backstop behind a gateway 403 and must not be narrated as one.
"""


def modify_patient_records(*args, **kwargs):
    raise PermissionError(
        "modify_patient_records is not an authorized tool for this agent "
    "identity. The ADK application layer must refuse this call, and this "
    "stub fails loudly instead of silently succeeding."
    )
