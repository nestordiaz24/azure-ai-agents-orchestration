"""
config.py – Environment configuration loader for Chapter 2.

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

    # Azure AI Project / Foundry endpoint
    azure_ai_project_endpoint: str = field(
        default_factory=lambda: os.environ.get(
            "AZURE_AI_PROJECT_ENDPOINT", ""
        )
    )

    # Azure OpenAI – used for the gpt-4o deployment backing the agent
    azure_openai_endpoint: str = field(
        default_factory=lambda: os.environ.get(
            "AZURE_OPENAI_ENDPOINT", ""
        )
    )
    azure_openai_api_key: str = field(
        default_factory=lambda: os.environ.get(
            "AZURE_OPENAI_API_KEY", ""
        )
    )
    azure_openai_deployment: str = field(
        default_factory=lambda: os.environ.get(
            "AZURE_OPENAI_DEPLOYMENT", "gpt-4o"
        )
    )

    # Agent configuration
    agent_name: str = field(
        default_factory=lambda: os.environ.get(
            "AGENT_NAME", "product-recommendation-agent"
        )
    )

    # Path to the product catalog JSON file
    products_json_path: str = field(
        default_factory=lambda: os.environ.get(
            "PRODUCTS_JSON_PATH",
            str(
                __import__("pathlib").Path(__file__).parent.parent
                / "data"
                / "products.json"
            ),
        )
    )

    # FastAPI server settings
    api_host: str = field(
        default_factory=lambda: os.environ.get("API_HOST", "0.0.0.0")
    )
    api_port: int = field(
        default_factory=lambda: int(os.environ.get("API_PORT", "8000"))
    )


def get_settings() -> Settings:
    """Return a populated Settings instance from environment variables."""
    return Settings()
