"""
chat.py – Interactive CLI to chat with the deployed Foundry agent.

Usage:
    python src/chat.py [--agent-name foundry-qa-agent]

Required environment variables (set automatically by `azd up`, or via a
.env file during local development):
    AZURE_OPENAI_ENDPOINT  – Azure OpenAI endpoint
    AGENT_NAME             – (optional) override agent name; defaults to 'foundry-qa-agent'

Type your question and press Enter. Type 'quit' or 'exit' to stop.
"""

import argparse
import os
import sys
import time
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

load_dotenv()

DEFAULT_AGENT_NAME = "foundry-qa-agent"
POLL_INTERVAL_SECONDS = 1
API_VERSION = "2024-12-01-preview"


def find_agent(client: AzureOpenAI, name: str):
    """Return the first assistant whose name matches, or None."""
    for agent in client.beta.assistants.list():
        if agent.name == name:
            return agent
    return None


def ask(client: AzureOpenAI, agent_id: str, thread_id: str, question: str) -> str:
    """Send a message to the agent and return the assistant reply text."""
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=question,
    )

    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=agent_id)

    while run.status in ("queued", "in_progress"):
        time.sleep(POLL_INTERVAL_SECONDS)
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

    if run.status != "completed":
        return f"[Run ended with status: {run.status}. Last error: {run.last_error}]"

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    for msg in messages:
        if msg.role == "assistant":
            for block in msg.content:
                if block.type == "text":
                    return block.text.value
    return "[No response received from agent]"


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with a Foundry agent.")
    parser.add_argument(
        "--agent-name",
        default=os.environ.get("AGENT_NAME", DEFAULT_AGENT_NAME),
        help=f"Name of the deployed agent (default: {DEFAULT_AGENT_NAME})",
    )
    args = parser.parse_args()

    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    if not endpoint:
        print(
            "ERROR: AZURE_OPENAI_ENDPOINT is not set.\n"
            "Run `azd env get-values` and set the variable, or add it to a .env file.",
            file=sys.stderr,
        )
        sys.exit(1)

    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version=API_VERSION,
    )

    agent = find_agent(client, args.agent_name)
    if not agent:
        print(
            f"ERROR: Agent '{args.agent_name}' not found in the project.\n"
            "Run `python src/deploy_agent.py` first to create it.",
            file=sys.stderr,
        )
        sys.exit(1)

    thread = client.beta.threads.create()

    print(f"\n🤖  Chatting with agent '{agent.name}' (id={agent.id})")
    print("    Type 'quit' or 'exit' to end the session.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Session ended.")
            break

        print("Agent: ", end="", flush=True)
        reply = ask(client, agent.id, thread.id, user_input)
        print(reply)
        print()


if __name__ == "__main__":
    main()
