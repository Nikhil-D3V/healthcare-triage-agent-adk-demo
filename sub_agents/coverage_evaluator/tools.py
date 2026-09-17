"""
Deterministic tool bindings for the Coverage & Prior-Auth Evaluator.

Backing store is selected by an env var, not by editing this file:

  POLICY_DATA_BACKEND=bigquery   -> queries BigQuery (deployed/demo-real mode)
  POLICY_DATA_BACKEND=local      -> reads mock_data/policy_rules.json (fast
                                     local iteration, no GCP project needed)

Default is "local" so `run_local_demo.py` keeps working out of the box.
Set POLICY_DATA_BACKEND=bigquery once you've run
deployment/setup_bigquery.sh, and set it that way in the Agent Runtime
deployment's env vars (see deployment/deploy.py) for the live demo.

Auth: the BigQuery client below uses Application Default Credentials only
(bigquery.Client() with no credentials= argument). Locally the project `.env`
sets `GOOGLE_APPLICATION_CREDENTIALS` to the configured ADC file; on Agent
Runtime the attached Reasoning Engine service agent is used.
"""

import json
import os
from typing import Optional

_MOCK_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "mock_data", "policy_rules.json"
)

_bq_client = None  # lazily constructed, only if bigquery backend is selected


def _backend() -> str:
    return os.environ.get("POLICY_DATA_BACKEND", "local").lower()


def _get_bq_client():
    global _bq_client
    if _bq_client is None:
        from google.cloud import bigquery  # imported lazily so local mode
        _bq_client = bigquery.Client()      # doesn't require the dependency
    return _bq_client


def _bq_dataset_ref() -> str:
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    dataset = os.environ.get("POLICY_BQ_DATASET", "payer_policy_demo")
    return f"{project}.{dataset}"


def _load_policy_table() -> dict:
    with open(os.path.abspath(_MOCK_DATA_PATH), "r") as f:
        return json.load(f)


def check_coverage_policy(cpt_code: str, payer_id: Optional[str] = None) -> dict:
    """Looks up prior-authorization requirements for a CPT procedure code.

    Args:
        cpt_code: The CPT procedure code to check, e.g. "27447".
        payer_id: Optional payer identifier, e.g. "BC_SELECT". If a
            payer-specific row exists it overrides the generic rule for
            that CPT code; otherwise the generic (payer_id IS NULL) row
            is used.

    Returns:
        A dict describing whether prior authorization is required and,
        if so, which medical-necessity criteria apply. Deterministic --
        this function never guesses.
    """
    if _backend() == "bigquery":
        client = _get_bq_client()
        from google.cloud import bigquery
        query = f"""
            SELECT cpt_code, payer_id, description, category,
                   prior_auth_required, criteria, summary
            FROM `{_bq_dataset_ref()}.cpt_rules`
            WHERE cpt_code = @cpt_code
              AND (payer_id = @payer_id OR payer_id IS NULL)
            ORDER BY payer_id IS NULL ASC
            LIMIT 1
        """
        job = client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("cpt_code", "STRING", cpt_code),
                    bigquery.ScalarQueryParameter("payer_id", "STRING", payer_id),
                ]
            ),
        )
        rows = list(job.result())
        if not rows:
            return {
                "cpt_code": cpt_code,
                "found": False,
                "prior_auth_required": None,
                "message": (
                    f"No policy rule found for CPT {cpt_code} in "
                    f"{_bq_dataset_ref()}.cpt_rules. Escalate to a human reviewer."
                ),
            }
        row = rows[0]
        return {
            "cpt_code": cpt_code,
            "payer_id": payer_id,
            "found": True,
            "prior_auth_required": row.prior_auth_required,
            "criteria": list(row.criteria),
            "policy_category": row.category,
            "message": row.summary or "",
        }

    # -- local JSON fallback --
    table = _load_policy_table()
    rules = table.get("cpt_rules", {})
    rule = rules.get(cpt_code)
    if rule is None:
        return {
            "cpt_code": cpt_code,
            "found": False,
            "prior_auth_required": None,
            "message": (
                f"No policy rule found for CPT {cpt_code} in the mock "
                "policy table. Escalate to a human reviewer."
            ),
        }
    payer_override = rule.get("payer_overrides", {}).get(payer_id, {}) if payer_id else {}
    merged = {**rule, **payer_override}
    return {
        "cpt_code": cpt_code,
        "payer_id": payer_id,
        "found": True,
        "prior_auth_required": merged.get("prior_auth_required"),
        "criteria": merged.get("criteria", []),
        "policy_category": merged.get("category"),
        "message": merged.get("summary", ""),
    }


def check_member_eligibility(member_id: str, payer_id: str) -> dict:
    """Looks up whether a member ID is active/eligible for a given payer."""
    if _backend() == "bigquery":
        client = _get_bq_client()
        from google.cloud import bigquery
        query = f"""
            SELECT eligible, plan_name, effective_date, termination_date, notes
            FROM `{_bq_dataset_ref()}.member_eligibility`
            WHERE member_id = @member_id AND payer_id = @payer_id
            LIMIT 1
        """
        job = client.query(
            query,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("member_id", "STRING", member_id),
                    bigquery.ScalarQueryParameter("payer_id", "STRING", payer_id),
                ]
            ),
        )
        rows = list(job.result())
        if not rows:
            return {"member_id": member_id, "payer_id": payer_id, "eligible": False,
                     "message": "Member not found in BigQuery eligibility table."}
        row = rows[0]
        return {
            "member_id": member_id,
            "payer_id": payer_id,
            "eligible": row.eligible,
            "plan_name": row.plan_name,
            "effective_date": str(row.effective_date) if row.effective_date else None,
            "termination_date": str(row.termination_date) if row.termination_date else None,
            "notes": row.notes,
        }

    # -- local JSON fallback --
    table = _load_policy_table()
    roster = table.get("member_eligibility", {})
    key = f"{payer_id}:{member_id}"
    record = roster.get(key)
    if record is None:
        return {"member_id": member_id, "payer_id": payer_id, "eligible": False,
                "message": "Member not found in mock eligibility roster."}
    return {"member_id": member_id, "payer_id": payer_id, **record}

def warmup_tools():
    """Pre-warm BigQuery client connection during container initialization."""
    if _backend() == "bigquery":
        try:
            _get_bq_client()
        except Exception:
            pass