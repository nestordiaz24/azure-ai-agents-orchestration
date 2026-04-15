"""
chat.py – Interactive CLI to chat with a simple Foundry Q&A agent.

Creates the agent inline on first run (no separate deploy step required).
The agent is cleaned up automatically when the session ends.

Usage:
    python src/chat.py

Required environment variables (set automatically by `azd up`, or via a
.env file during local development):
    AZURE_AI_PROJECT_ENDPOINT – Azure AI Foundry project endpoint
    AZURE_OPENAI_DEPLOYMENT   – Model deployment name (default: gpt-4o)
    AGENT_NAME                – (optional) agent name (default: foundry-qa-agent)

Type your question and press Enter. Type 'quit' or 'exit' to stop.
"""

import sys
import time

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MessageRole, RunStatus
from azure.identity import DefaultAzureCredential

from src.config import get_settings

POLL_INTERVAL_SECONDS = 0.5

AGENT_INSTRUCTIONS = """
You are a helpful Q&A assistant powered by Azure AI Foundry.
Answer questions accurately and concisely.
If a question is ambiguous, ask for clarification.
Keep answers focused and professional.
""".strip()


def ask(client: AIProjectClient, agent_id: str, thread_id: str, question: str) -> str:
    """Send *question* to the agent thread and return the assistant reply."""
    client.agents.create_message(
        thread_id=thread_id,
        role=MessageRole.USER,
        content=question,
    )

    run = client.agents.create_run(thread_id=thread_id, agent_id=agent_id)

    while run.status in (RunStatus.QUEUED, RunStatus.IN_PROGRESS):
        time.sleep(POLL_INTERVAL_SECONDS)
        run = client.agents.get_run(thread_id=thread_id, run_id=run.id)

    if run.status != RunStatus.COMPLETED:
        return f"[Run ended with status: {run.status}. Last error: {getattr(run, 'last_error', 'unknown')}]"

    messages = client.agents.list_messages(thread_id=thread_id)
    for msg in messages:
        if msg.role == MessageRole.AGENT:
            for block in msg.content:
                if hasattr(block, "text"):
                    return block.text.value
    return "[No response received from agent]"


def main() -> None:
    settings = get_settings()

    if not settings.azure_ai_project_endpoint:
        print(
            "ERROR: AZURE_AI_PROJECT_ENDPOINT is not set.\n"
            "Run `azd env get-values` and set the variable, or add it to a .env file.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = AIProjectClient(
        endpoint=settings.azure_ai_project_endpoint,
        credential=DefaultAzureCredential(),
    )

    print(f"Creating agent '{settings.agent_name}' …")
    agent = client.agents.create_agent(
        model=settings.azure_openai_deployment,
        name=settings.agent_name,
        instructions=AGENT_INSTRUCTIONS,
    )
    print(f"Agent created: {agent.id}")

    thread = client.agents.create_thread()

    print(f"\n🤖  Chatting with agent '{agent.name}' (id={agent.id})")
    print("    Type 'quit' or 'exit' to end the session.\n")

    try:
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
    finally:
        print(f"\nCleaning up agent '{agent.id}' …")
        client.agents.delete_agent(agent.id)
        print("Done.")


if __name__ == "__main__":
    main()
