"""
chat.py – Interactive CLI to chat with the deployed Foundry agent.

Usage:
    python src/chat.py [--agent-name foundry-qa-agent]

Required environment variables (set automatically by `azd up`, or via a
.env file during local development):
    AZURE_AI_PROJECT_ENDPOINT  – AI Project endpoint
    AGENT_NAME                 – (optional) override agent name; defaults to 'foundry-qa-agent'

Type your question and press Enter. Type 'quit' or 'exit' to stop.
"""

import argparse
import os
import sys
import time
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import RunStatus

load_dotenv()

DEFAULT_AGENT_NAME = "foundry-qa-agent"
POLL_INTERVAL_SECONDS = 1


def find_agent(client: AIProjectClient, name: str):
    """Return the first agent whose name matches, or None."""
    for agent in client.agents.list_agents():
        if agent.name == name:
            return agent
    return None


def ask(client: AIProjectClient, agent_id: str, thread_id: str, question: str) -> str:
    """Send a message to the agent and return the assistant reply text."""
    client.agents.create_message(
        thread_id=thread_id,
        role="user",
        content=question,
    )

    run = client.agents.create_run(thread_id=thread_id, agent_id=agent_id)

    # Poll until the run completes (REQUIRES_ACTION is not handled here as this
    # agent uses only retrieval tools that do not require function-call approval)
    while run.status in (RunStatus.QUEUED, RunStatus.IN_PROGRESS):
        time.sleep(POLL_INTERVAL_SECONDS)
        run = client.agents.get_run(thread_id=thread_id, run_id=run.id)

    if run.status != RunStatus.COMPLETED:
        return f"[Run ended with status: {run.status}. Last error: {run.last_error}]"

    messages = client.agents.list_messages(thread_id=thread_id)
    # Messages are returned newest-first; find the latest assistant message
    for msg in messages:
        if msg.role == "assistant":
            for block in msg.content:
                if hasattr(block, "text"):
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

    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        print(
            "ERROR: AZURE_AI_PROJECT_ENDPOINT is not set.\n"
            "Run `azd env get-values` and set the variable, or add it to a .env file.",
            file=sys.stderr,
        )
        sys.exit(1)

    credential = DefaultAzureCredential()
    client = AIProjectClient(endpoint=endpoint, credential=credential)

    agent = find_agent(client, args.agent_name)
    if not agent:
        print(
            f"ERROR: Agent '{args.agent_name}' not found in the project.\n"
            "Run `python src/deploy_agent.py` first to create it.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Create a persistent thread for this session
    thread = client.agents.create_thread()

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
