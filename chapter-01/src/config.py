"""
config.py – Environment configuration loader for Chapter 1.

Reads settings from environment variables (and optionally a `.env` file)
using python-dotenv. All Azure credentials are consumed from environment
variables; no secrets are hardcoded.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load .env file when present (ignored in production container environments
# where variables are injected directly).
load_dotenv()


@dataclass
class Settings:
    """Application settings sourced from environment variables."""

    # Azure AI Foundry project endpoint
    azure_ai_project_endpoint: str = field(
        default_factory=lambda: os.environ.get(
            "AZURE_AI_PROJECT_ENDPOINT", ""
        )
    )

    # Azure OpenAI – model deployment name backing the agent
    azure_openai_deployment: str = field(
        default_factory=lambda: os.environ.get(
            "AZURE_OPENAI_DEPLOYMENT", "gpt-4o"
        )
    )

    # Agent configuration
    agent_name: str = field(
        default_factory=lambda: os.environ.get(
            "AGENT_NAME", "foundry-qa-agent"
        )
    )


def get_settings() -> Settings:
    """Return a populated Settings instance from environment variables."""
    return Settings()
