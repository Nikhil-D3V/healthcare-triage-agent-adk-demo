"""
Deploy the Clinical Intake Orchestrator to Vertex AI Agent Runtime.

Authentication: this script uses Application Default Credentials. It loads
GOOGLE_APPLICATION_CREDENTIALS and other deployment settings from `.env`, so
the Google Cloud and Vertex AI SDKs resolve ADC through the standard
environment-based path. Credentials are never passed explicitly to a client.

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

import vertexai
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import A2aAgent

from healthcare_triage_agent.clinical_orchestrator.a2a_agent import SecureA2aAgent
from healthcare_triage_agent.clinical_orchestrator.agent import root_agent
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

    # Agent Runtime preserves extra-package paths in its dependency archive.
    # Use the workspace parent so the healthcare_triage_agent package layout
    # remains importable regardless of the caller's current directory.
    os.chdir(PROJECT_ROOT.parent)


    a2a_agent = SecureA2aAgent(
        agent_card=agent_card,
        agent_executor_builder=ClinicalOrchestratorExecutor,
    )
    client = vertexai.Client(project=project, location=location)
    remote_agent = client.agent_engines.create(
        agent=a2a_agent,
        config={
            "display_name": "clinical-intake-prior-auth-triage",
            "description": (
                "Multi-agent healthcare intake + prior-auth triage demo. "
                "Synthetic data only -- see /synthetic_notes."
            ),
            "requirements": _deployment_requirements(),
            "extra_packages": _extra_packages(),
            "staging_bucket": staging_bucket,
            "env_vars": _runtime_env_vars(),
        },
    )

    print(f"Deployed A2A agent. Resource name: {remote_agent.api_resource.name}")
    print(
        "Next: add this Agent Runtime deployment to Agent Registry and import "
        "it into Gemini Enterprise through the Agent Gateway-backed flow."
    )


def deploy_native_agent():
    """Fallback native ADK deployment retained for rollback/testing."""
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    staging_bucket = os.environ["AGENT_ENGINE_STAGING_BUCKET"]

    vertexai.init(
        project=project,
        location=location,
        staging_bucket=staging_bucket,
    )
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
        extra_packages=_extra_packages(),
        env_vars=_runtime_env_vars(),
    )

    print(f"Native fallback deployed. Resource name: {remote_agent.resource_name}")


def main():
    deploy_a2a_agent()


if __name__ == "__main__":
    main()
