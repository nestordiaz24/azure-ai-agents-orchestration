"""
recommendation_agent.py – Product Recommendation Agent using the Azure AI
Agents SDK (azure-ai-projects).

This module creates and manages a code-first agent that uses a
``product_lookup`` tool backed by the local product catalog.  The agent:

* Maintains multi-turn conversation via a thread per session.
* Calls ``product_lookup`` whenever the user asks about products, features,
  or recommendations.
* Runs the tool locally and returns the results to the model so it can
  compose a human-friendly answer.

Usage (standalone):
    >>> from src.recommendation_agent import RecommendationAgent
    >>> agent = RecommendationAgent()
    >>> reply = agent.chat("What monitoring tools do you offer?")
    >>> print(reply)

Environment variables required for Azure integration (see .env.example):
    AZURE_AI_PROJECT_ENDPOINT – Azure AI Foundry project endpoint
    AZURE_OPENAI_DEPLOYMENT   – Model deployment name (default: gpt-4o)
"""

import json
import logging
import time
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AgentThread,
    FunctionTool,
    MessageRole,
    RequiredFunctionToolCall,
    RunStatus,
    SubmitToolOutputsAction,
    ToolOutput,
    ToolSet,
)
from azure.identity import DefaultAzureCredential

from src.config import get_settings
from src.product_catalog import get_recommendations, list_all_products, search_products

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool function definitions (registered with the agent)
# ---------------------------------------------------------------------------

AGENT_INSTRUCTIONS = """
You are an expert product advisor for AcmeCorp. Your goal is to help users
discover the right products for their needs and suggest complementary
solutions that deliver greater value together.

Guidelines:
- Always use the product_lookup tool to search or retrieve recommendations
  before answering questions about products.
- Present results in a clear, structured format (bullet points or tables).
- Highlight how recommended products complement each other.
- If the user's query is ambiguous, ask a clarifying question.
- Keep responses concise and focused on product benefits.
- Do not invent product names or prices; use only catalog data.
""".strip()


def _tool_search_products(query: str) -> str:
    """Search the AcmeCorp product catalog for products matching *query*.

    Args:
        query: Keywords describing the desired product or capability.

    Returns:
        JSON string with a list of matching products (id, name, description,
        category, tags, price).
    """
    results = search_products(query)
    if not results:
        return json.dumps({"results": [], "message": "No products matched the query."})
    return json.dumps({"results": results})


def _tool_get_recommendations(product_id: str) -> str:
    """Return products recommended as companions to *product_id*.

    Args:
        product_id: The exact product ID string (e.g., ``ACME-MON-001``).

    Returns:
        JSON string with a list of recommended products.
    """
    results = get_recommendations(product_id)
    if not results:
        return json.dumps(
            {
                "results": [],
                "message": f"No recommendations found for product '{product_id}'.",
            }
        )
    return json.dumps({"results": results})


def _tool_list_all_products() -> str:
    """Return all products in the AcmeCorp catalog.

    Returns:
        JSON string with the full product list.
    """
    results = list_all_products()
    return json.dumps({"results": results})


# ---------------------------------------------------------------------------
# Tool dispatch table
# ---------------------------------------------------------------------------

_TOOL_FUNCTIONS: dict[str, Any] = {
    "search_products": _tool_search_products,
    "get_recommendations": _tool_get_recommendations,
    "list_all_products": _tool_list_all_products,
}

# JSON Schema definitions for the tools (passed to the agent)
_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "search_products",
        "description": (
            "Search the AcmeCorp product catalog using keywords. "
            "Returns a list of products whose name, description, or tags match."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords describing the desired product or capability.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_recommendations",
        "description": (
            "Get recommended companion products for a given product ID. "
            "Returns related products based on shared categories and tags."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "The exact product ID (e.g., ACME-MON-001).",
                }
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "list_all_products",
        "description": "Return the full AcmeCorp product catalog.",
        "parameters": {"type": "object", "properties": {}},
    },
]


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------


class RecommendationAgent:
    """Code-first product recommendation agent backed by Azure AI Agents SDK.

    The agent is created (or reused) on first use and supports multi-turn
    conversations via threads.  Each ``RecommendationAgent`` instance manages
    its own thread so it can be used for a single conversation session.

    Args:
        settings: Optional ``Settings`` object; defaults to ``get_settings()``.
    """

    def __init__(self, settings=None) -> None:
        self._settings = settings or get_settings()
        self._client: AIProjectClient | None = None
        self._agent_id: str | None = None
        self._thread: AgentThread | None = None

    def _get_client(self) -> AIProjectClient:
        """Lazily initialize and return the AI Project client."""
        if self._client is None:
            endpoint = self._settings.azure_ai_project_endpoint
            if not endpoint:
                raise ValueError(
                    "AZURE_AI_PROJECT_ENDPOINT is not set. "
                    "Add it to your .env file or environment."
                )
            self._client = AIProjectClient(
                endpoint=endpoint,
                credential=DefaultAzureCredential(),
            )
        return self._client

    def _ensure_agent(self) -> str:
        """Return the agent ID, creating the agent if it does not exist yet."""
        if self._agent_id is not None:
            return self._agent_id

        client = self._get_client()
        name = self._settings.agent_name
        model = self._settings.azure_openai_deployment

        # Check whether an agent with this name already exists
        for existing in client.agents.list_agents():
            if existing.name == name:
                logger.info("Reusing existing agent '%s' (id=%s)", name, existing.id)
                self._agent_id = existing.id
                return self._agent_id

        # Create a new agent with the product_lookup tool set
        toolset = ToolSet()
        toolset.add(FunctionTool(functions=set(_TOOL_FUNCTIONS.keys())))

        agent = client.agents.create_agent(
            model=model,
            name=name,
            instructions=AGENT_INSTRUCTIONS,
            toolset=toolset,
        )
        logger.info("Created agent '%s' (id=%s)", name, agent.id)
        self._agent_id = agent.id
        return self._agent_id

    def _ensure_thread(self) -> AgentThread:
        """Return the active thread, creating one if needed."""
        if self._thread is None:
            client = self._get_client()
            self._thread = client.agents.create_thread()
            logger.debug("Created thread id=%s", self._thread.id)
        return self._thread

    def _execute_tool_calls(
        self,
        tool_calls: list[RequiredFunctionToolCall],
    ) -> list[ToolOutput]:
        """Execute all pending tool calls and return their outputs.

        Args:
            tool_calls: List of tool-call requests from the model.

        Returns:
            List of ``ToolOutput`` objects containing tool results.
        """
        outputs: list[ToolOutput] = []
        for call in tool_calls:
            fn_name = call.function.name
            raw_args = call.function.arguments or "{}"
            try:
                kwargs = json.loads(raw_args)
            except json.JSONDecodeError:
                kwargs = {}

            fn = _TOOL_FUNCTIONS.get(fn_name)
            if fn is None:
                result = json.dumps({"error": f"Unknown tool: {fn_name}"})
            else:
                try:
                    result = fn(**kwargs)
                except (TypeError, KeyError, ValueError, FileNotFoundError) as exc:
                    logger.exception("Tool '%s' raised an error", fn_name)
                    result = json.dumps({"error": str(exc)})
                except Exception as exc:  # noqa: BLE001 – tool is user-defined; any error must be captured
                    logger.exception("Tool '%s' raised an unexpected error", fn_name)
                    result = json.dumps({"error": f"Unexpected error in tool: {exc}"})

            outputs.append(ToolOutput(tool_call_id=call.id, output=result))
        return outputs

    def chat(self, message: str) -> str:
        """Send *message* to the agent and return the assistant reply.

        This method is stateful: each call continues the same conversation
        thread, enabling multi-turn dialogue.

        Args:
            message: User message text.

        Returns:
            The assistant's reply as a plain string.

        Raises:
            ValueError: If required environment variables are missing.
            RuntimeError: If the run ends in an unexpected terminal state.
        """
        client = self._get_client()
        agent_id = self._ensure_agent()
        thread = self._ensure_thread()

        # Add user message to the thread
        client.agents.create_message(
            thread_id=thread.id,
            role=MessageRole.USER,
            content=message,
        )

        # Start a run
        run = client.agents.create_run(
            thread_id=thread.id,
            agent_id=agent_id,
        )

        # Poll until the run completes (or requires tool execution)
        while run.status in (RunStatus.QUEUED, RunStatus.IN_PROGRESS, RunStatus.REQUIRES_ACTION):
            if run.status == RunStatus.REQUIRES_ACTION and isinstance(
                run.required_action, SubmitToolOutputsAction
            ):
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                outputs = self._execute_tool_calls(tool_calls)
                run = client.agents.submit_tool_outputs_to_run(
                    thread_id=thread.id,
                    run_id=run.id,
                    tool_outputs=outputs,
                )
            else:
                time.sleep(0.5)
                run = client.agents.get_run(thread_id=thread.id, run_id=run.id)

        if run.status == RunStatus.COMPLETED:
            messages = client.agents.list_messages(thread_id=thread.id)
            # The most recent assistant message is the reply
            for msg in messages:
                if msg.role == MessageRole.AGENT:
                    for block in msg.content:
                        if hasattr(block, "text"):
                            return block.text.value
            return "[No response from agent]"

        raise RuntimeError(
            f"Agent run ended with status '{run.status}'. "
            f"Last error: {getattr(run, 'last_error', 'unknown')}"
        )

    def reset(self) -> None:
        """Reset the conversation thread, starting a fresh session."""
        self._thread = None
        logger.debug("Conversation thread reset.")

    def delete_agent(self) -> None:
        """Delete the remote agent resource (cleanup helper)."""
        if self._agent_id and self._client:
            self._client.agents.delete_agent(self._agent_id)
            logger.info("Deleted agent id=%s", self._agent_id)
            self._agent_id = None
