"""
Sub-Agent 1: Clinical Data Extractor
-------------------------------------
Unstructured -> structured clinical parsing specialist.

Takes raw clinical intake narratives (referral letters, progress notes,
patient portal text) and converts them into a standardized JSON payload
containing patient identifiers, clinical findings, conservative-therapy
history, and CPT/ICD-10 codes.

NOTE on PHI: this agent receives text AFTER Agent Gateway + Model Armor
ingress inspection in the deployed topology. In local/dev runs (adk web /
adk run) Model Armor is not in the loop, so never point this agent at real
patient data locally -- use the synthetic notes in /synthetic_notes only.
"""

from google.adk.agents import LlmAgent

EXTRACTOR_INSTRUCTION = """
You are a Clinical Data Extraction specialist embedded in a prior-authorization
triage pipeline. You will be given a raw, unstructured clinical intake note
(referral letter, dictation, or patient-portal summary).

Extract the following fields and return ONLY a single valid JSON object
(no markdown fences, no commentary):

{
  "patient_identifiers": {
    "name": string or null,
    "dob": string or null,
    "mrn": string or null
  },
  "payer": {
    "payer_name": string or null,
    "member_id": string or null
  },
  "diagnosis": {
    "icd10_code": string or null,
    "description": string or null
  },
  "procedure": {
    "cpt_code": string or null,
    "description": string or null
  },
  "conservative_therapy_history": {
    "physical_therapy_weeks": number or null,
    "medication_trial": string or null,
    "injections_or_procedures": string or null
  },
  "clinical_flags": {
    "neurological_deficit": boolean,
    "symptom_duration_weeks": number or null,
    "red_flags_present": boolean,
    "notes": string
  }
}

Rules:
- Never fabricate a value. If a field is not present in the note, use null
  (or false/0 where the schema requires a boolean/number default).
- Do not attempt to redact or mask PHI yourself -- that is Model Armor's job
  at the gateway. Your only responsibility is faithful structured extraction.
- Preserve codes exactly as written in the note (do not "correct" a CPT or
  ICD-10 code you believe is wrong -- flag it in clinical_flags.notes instead).
"""

clinical_extractor_agent = LlmAgent(
    name="clinical_data_extractor",
    model="gemini-2.5-flash",
    description=(
        "Parses unstructured clinical intake narratives into standardized "
        "JSON: patient identifiers, diagnosis/procedure codes, and "
        "conservative-therapy history."
    ),
    instruction=EXTRACTOR_INSTRUCTION,
)
