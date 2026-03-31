"""
deploy_agent.py – Create or update the Foundry agent from agent.yaml.

Usage:
    python src/deploy_agent.py

Required environment variables (set automatically by `azd up`, or via a
.env file during local development):
    AZURE_OPENAI_ENDPOINT          – Azure OpenAI endpoint (e.g. https://<name>.openai.azure.com/)
    AZURE_AI_SEARCH_ENDPOINT       – Azure AI Search endpoint
    AZURE_AI_SEARCH_INDEX_NAME     – Name of the search index (default: documents)
"""

import os
import sys
import pathlib
import yaml
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

load_dotenv()

AGENT_YAML_PATH = pathlib.Path(__file__).parent.parent / "agent.yaml"
API_VERSION = "2024-12-01-preview"


def load_agent_spec() -> dict:
    """Load and resolve environment variable placeholders in agent.yaml."""
    raw = AGENT_YAML_PATH.read_text(encoding="utf-8")

    import re

    def _replace(match: re.Match) -> str:
        var = match.group(1)
        value = os.environ.get(var)
        if not value:
            print(f"WARNING: environment variable '{var}' is not set; leaving placeholder.")
            return match.group(0)
        return value

    resolved = re.sub(r"\$\{([^}]+)\}", _replace, raw)
    return yaml.safe_load(resolved)


def deploy(endpoint: str) -> None:
    """Create or update the agent in the given Azure OpenAI resource."""
    spec = load_agent_spec()
    agent_name: str = spec["name"]
    model: str = spec["model"]
    instructions: str = spec.get("instructions", "").strip()

    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version=API_VERSION,
    )

    # Check whether the agent already exists
    existing_agent = None
    for agent in client.beta.assistants.list():
        if agent.name == agent_name:
            existing_agent = agent
            break

    if existing_agent:
        print(f"Updating existing agent '{agent_name}' (id={existing_agent.id}) …")
        client.beta.assistants.update(
            assistant_id=existing_agent.id,
            model=model,
            name=agent_name,
            instructions=instructions,
        )
        print(f"Agent updated: {existing_agent.id}")
    else:
        print(f"Creating agent '{agent_name}' …")
        agent = client.beta.assistants.create(
            model=model,
            name=agent_name,
            instructions=instructions,
        )
        print(f"Agent created: {agent.id}")


def main() -> None:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    if not endpoint:
        print(
            "ERROR: AZURE_OPENAI_ENDPOINT is not set.\n"
            "Run `azd env get-values` and set the variable, or add it to a .env file.",
            file=sys.stderr,
        )
        sys.exit(1)

    deploy(endpoint)


if __name__ == "__main__":
    main()
