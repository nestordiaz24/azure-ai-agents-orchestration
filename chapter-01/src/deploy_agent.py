"""
deploy_agent.py – Create or update the Foundry agent from agent.yaml.

Usage:
    python src/deploy_agent.py

Required environment variables (set automatically by `azd up`, or via a
.env file during local development):
    AZURE_AI_PROJECT_ENDPOINT   – AI Project endpoint (e.g. https://<hub>.api.azureml.ms/...)
    AZURE_AI_SEARCH_CONNECTION_ID  – Full resource-id of the AI Search connection in the Hub
    AZURE_AI_SEARCH_INDEX_NAME     – Name of the search index (default: documents)
"""

import os
import sys
import pathlib
import yaml
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AzureAISearchTool,
    AzureAISearchQueryType,
)

load_dotenv()

AGENT_YAML_PATH = pathlib.Path(__file__).parent.parent / "agent.yaml"


def load_agent_spec() -> dict:
    """Load and resolve environment variable placeholders in agent.yaml."""
    raw = AGENT_YAML_PATH.read_text(encoding="utf-8")

    # Substitute ${VAR} placeholders with actual env values
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


def build_tools(spec: dict) -> list:
    """Convert the tool definitions from agent.yaml into SDK tool objects."""
    tools = []
    for tool_def in spec.get("tools", []):
        tool_type = tool_def.get("type")
        if tool_type == "azure_ai_search":
            search_cfg = tool_def["azure_ai_search"]
            for idx in search_cfg.get("indexes", []):
                query_type_str = idx.get("query_type", "simple").upper()
                query_type = getattr(AzureAISearchQueryType, query_type_str, AzureAISearchQueryType.SIMPLE)
                tools.append(
                    AzureAISearchTool(
                        index_connection_id=idx["index_connection_id"],
                        index_name=idx["index_name"],
                        query_type=query_type,
                        top_k=idx.get("top_k", 5),
                        filter=idx.get("filter"),
                    )
                )
        else:
            print(f"WARNING: unsupported tool type '{tool_type}'; skipping.")
    return tools


def deploy(endpoint: str) -> None:
    """Create or update the agent in the given AI Project."""
    spec = load_agent_spec()
    agent_name: str = spec["name"]
    model: str = spec["model"]
    instructions: str = spec.get("instructions", "").strip()
    tools = build_tools(spec)

    credential = DefaultAzureCredential()
    client = AIProjectClient(endpoint=endpoint, credential=credential)

    # Check whether the agent already exists
    existing_agent = None
    for agent in client.agents.list_agents():
        if agent.name == agent_name:
            existing_agent = agent
            break

    tool_defs = []
    tool_resources_list = []
    for tool in tools:
        tool_defs.extend(tool.definitions)
        if tool.resources:
            tool_resources_list.append(tool.resources)

    # The SDK accepts a single ToolResources object; merge index lists if multiple search tools exist
    tool_resources = None
    if tool_resources_list:
        tool_resources = tool_resources_list[0]

    if existing_agent:
        print(f"Updating existing agent '{agent_name}' (id={existing_agent.id}) …")
        client.agents.update_agent(
            agent_id=existing_agent.id,
            model=model,
            name=agent_name,
            instructions=instructions,
            tools=tool_defs,
            tool_resources=tool_resources,
        )
        print(f"Agent updated: {existing_agent.id}")
    else:
        print(f"Creating agent '{agent_name}' …")
        agent = client.agents.create_agent(
            model=model,
            name=agent_name,
            instructions=instructions,
            tools=tool_defs,
            tool_resources=tool_resources,
        )
        print(f"Agent created: {agent.id}")


def main() -> None:
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        print(
            "ERROR: AZURE_AI_PROJECT_ENDPOINT is not set.\n"
            "Run `azd env get-values` and set the variable, or add it to a .env file.",
            file=sys.stderr,
        )
        sys.exit(1)

    deploy(endpoint)


if __name__ == "__main__":
    main()
