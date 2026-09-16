"""
Deploy the Clinical Intake Orchestrator to Vertex AI Agent Runtime.

Authentication: this script loads Application Default Credentials from the
JSON file configured by GOOGLE_APPLICATION_CREDENTIALS. The project-specific
default path is the credential file used for this demo; set the environment
variable to another path when running elsewhere.

Usage:
  python deployment/deploy.py
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip('"\''))

from google.auth import load_credentials_from_file
import vertexai
from vertexai import agent_engines

from healthcare_triage_agent.clinical_orchestrator.agent import root_agent


def main():
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    staging_bucket = os.environ["AGENT_ENGINE_STAGING_BUCKET"]
    credentials_path = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS",
        r"C:\Users\nikhi\Desktop\Projects\GE Webinar\d3v-agentspace-demo-4c8cfd668d80.json",
    )
    credentials, _ = load_credentials_from_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )

    vertexai.init(
        project=project,
        location=location,
        staging_bucket=staging_bucket,
        credentials=credentials,
    )

    # Agent Runtime preserves extra-package paths in its dependency archive.
    # Use the workspace parent so the healthcare_triage_agent package layout
    # remains importable regardless of the caller's current directory.
    os.chdir(PROJECT_ROOT.parent)

    remote_agent = agent_engines.create(
        agent_engine=root_agent,
        requirements=[
            "google-adk>=1.0.0",
            "google-cloud-aiplatform>=1.70.0",
            "google-cloud-bigquery>=3.25.0",
            "cloudpickle>=3.0.0",
        ],
        display_name="clinical-intake-prior-auth-triage",
        description=(
            "Multi-agent healthcare intake + prior-auth triage demo. "
            "Synthetic data only -- see /synthetic_notes."
        ),
        # Extra source files the deployed package needs alongside the
        # top-level agent code (sub-agents, tools, mock data).
        extra_packages=[
            "healthcare_triage_agent/clinical_orchestrator",
            "healthcare_triage_agent/sub_agents",
            "healthcare_triage_agent/security",
            "healthcare_triage_agent/mock_data",
        ],
        # Once setup_bigquery.sh has been run, the deployed/live-demo agent
        # should read from BigQuery, not the bundled JSON fallback.
        env_vars={
            "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
            "POLICY_DATA_BACKEND": "bigquery",
            "POLICY_BQ_DATASET": os.environ.get("POLICY_BQ_DATASET", "payer_policy_demo"),
        },
    )

    print(f"Deployed. Resource name: {remote_agent.resource_name}")
    print(
        "Next: register this resource name as the backing agent for an "
        "Agent Gateway route, then attach the Model Armor template from "
        "security/model_armor_agent_gateway_config.yaml to that route."
    )


if __name__ == "__main__":
    main()
