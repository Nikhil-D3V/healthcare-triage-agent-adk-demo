"""
Deploy the Clinical Intake Orchestrator to Vertex AI Agent Runtime.
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

import vertexai
from vertexai import agent_engines

from healthcare_triage_agent.clinical_orchestrator.a2a_agent import SecureA2aAgent
from healthcare_triage_agent.clinical_orchestrator.a2a_executor import (
    ClinicalOrchestratorExecutor,
)
from healthcare_triage_agent.clinical_orchestrator.agent_card import agent_card


def _deployment_requirements():
    return [
        "google-cloud-aiplatform[agent_engines,adk]==1.149.0",
        "a2a-sdk==0.3.26",
        "google-adk[a2a]==1.29.0",
        "pydantic>=2.0.0,<3.0.0",
        "google-cloud-bigquery>=3.25.0",
        "cloudpickle>=3.0.0",
    ]


def _extra_packages():
    return [
        "healthcare_triage_agent/clinical_orchestrator",
        "healthcare_triage_agent/sub_agents",
        "healthcare_triage_agent/security",
        "healthcare_triage_agent/mock_data",
    ]


def _runtime_env_vars():
    return {
        "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
        "POLICY_DATA_BACKEND": "bigquery",
        "POLICY_BQ_DATASET": os.environ.get(
            "POLICY_BQ_DATASET", "payer_policy_demo"
        ),
    }


def deploy_a2a_agent():
    """Deploy the Agent Runtime A2A endpoint used by Agent Registry."""
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    staging_bucket = os.environ["AGENT_ENGINE_STAGING_BUCKET"]

    vertexai.init(
        project=project,
        location=location,
        staging_bucket=staging_bucket,
    )

    os.chdir(PROJECT_ROOT.parent)

    a2a_agent = SecureA2aAgent(
        agent_card=agent_card,
        agent_executor_builder=ClinicalOrchestratorExecutor,
    )
    client = vertexai.Client(project=project, location=location)
    remote_agent = client.agent_engines.create(
        agent=a2a_agent,
        config={
            "display_name": "Clinical Intake Triage",
            "description": (
                "Automated healthcare intake and prior-authorization triage agent. "
                "Evaluates clinical notes against payer rules and member eligibility."
            ),
            "requirements": _deployment_requirements(),
            "extra_packages": _extra_packages(),
            "staging_bucket": staging_bucket,
            "env_vars": _runtime_env_vars(),
        },
    )

    print(f"Deployed A2A agent. Resource name: {remote_agent.api_resource.name}")


def main():
    deploy_a2a_agent()


if __name__ == "__main__":
    main()