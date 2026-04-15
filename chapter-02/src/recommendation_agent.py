"""
recommendation_agent.py – Product Recommendation Agent using the Microsoft
Agent Framework SDK (agent-framework).

This module creates and manages a code-first agent that uses the Agent
Framework's ``@tool`` decorator to register product catalog lookup tools.
The agent:

* Uses ``FoundryChatClient`` to connect to Azure AI Foundry for model inference.
* Uses the ``Agent`` class for local agent construction – no manual thread or
  run polling required.
* Maintains multi-turn conversations via ``AgentSession``.
* Registers tools using the ``@tool`` decorator, replacing the raw Foundry
  ``FunctionTool`` / ``ToolSet`` approach used in Chapter 1.

Usage (standalone):
    >>> import asyncio
    >>> from src.recommendation_agent import RecommendationAgent
    >>> agent = RecommendationAgent()
    >>> reply = asyncio.run(agent.chat("What monitoring tools do you offer?"))
    >>> print(reply)

Environment variables required for Azure integration (see .env.example):
    AZURE_AI_PROJECT_ENDPOINT – Azure AI Foundry project endpoint
    AZURE_OPENAI_DEPLOYMENT   – Model deployment name (default: gpt-4o)
"""

import json
import logging
from typing import Annotated

from agent_framework import Agent, AgentSession, tool
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential

from src.config import get_settings
from src.product_catalog import get_recommendations, list_all_products, search_products

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent instructions
# ---------------------------------------------------------------------------

AGENT_INSTRUCTIONS = """
You are an expert product advisor for AcmeCorp. Your goal is to help users
discover the right products for their needs and suggest complementary
solutions that deliver greater value together.

Guidelines:
- Always use the search_products_tool to search or retrieve recommendations
  before answering questions about products.
- Present results in a clear, structured format (bullet points or tables).
- Highlight how recommended products complement each other.
- If the user's query is ambiguous, ask a clarifying question.
- Keep responses concise and focused on product benefits.
- Do not invent product names or prices; use only catalog data.
""".strip()


# ---------------------------------------------------------------------------
# Tool definitions using the @tool decorator
# ---------------------------------------------------------------------------


@tool
def search_products_tool(
    query: Annotated[str, "Keywords describing the desired product or capability"],
) -> str:
    """Search the AcmeCorp product catalog for products matching the query.

    Returns a JSON string with a list of matching products (id, name,
    description, category, tags, price).
    """
    results = search_products(query)
    if not results:
        return json.dumps({"results": [], "message": "No products matched the query."})
    return json.dumps({"results": results})


@tool
def get_recommendations_tool(
    product_id: Annotated[str, "The exact product ID (e.g., ACME-MON-001)"],
) -> str:
    """Return products recommended as companions to the given product ID.

    Returns a JSON string with a list of recommended products.
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


@tool
def list_all_products_tool() -> str:
    """Return all products in the AcmeCorp catalog.

    Returns a JSON string with the full product list.
    """
    results = list_all_products()
    return json.dumps({"results": results})


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------


class RecommendationAgent:
    """Code-first product recommendation agent using the Microsoft Agent Framework.

    Uses ``FoundryChatClient`` and the ``Agent`` class for local agent
    construction backed by Azure AI Foundry.  Tools are registered via the
    ``@tool`` decorator; no manual polling loop is required.  Each instance
    manages its own ``AgentSession`` to maintain multi-turn conversation state.

    Args:
        settings: Optional ``Settings`` object; defaults to ``get_settings()``.
    """

    def __init__(self, settings=None) -> None:
        self._settings = settings or get_settings()
        self._agent: Agent | None = None
        self._session: AgentSession | None = None

    def _build_agent(self) -> Agent:
        """Construct an Agent backed by Azure AI Foundry via FoundryChatClient."""
        endpoint = self._settings.azure_ai_project_endpoint
        if not endpoint:
            raise ValueError(
                "AZURE_AI_PROJECT_ENDPOINT is not set. "
                "Add it to your .env file or environment."
            )

        client = FoundryChatClient(
            project_endpoint=endpoint,
            model=self._settings.azure_openai_deployment,
            credential=DefaultAzureCredential(),
        )

        return Agent(
            client=client,
            instructions=AGENT_INSTRUCTIONS,
            tools=[search_products_tool, get_recommendations_tool, list_all_products_tool],
            name=self._settings.agent_name,
        )

    def _get_agent(self) -> Agent:
        """Lazily initialize and return the Agent instance."""
        if self._agent is None:
            self._agent = self._build_agent()
            logger.debug("Agent '%s' initialized.", self._settings.agent_name)
        return self._agent

    def _get_session(self) -> AgentSession:
        """Return the active AgentSession, creating one if needed."""
        if self._session is None:
            self._session = self._get_agent().create_session()
            logger.debug("New AgentSession created (id=%s).", self._session.session_id)
        return self._session

    async def chat(self, message: str) -> str:
        """Send *message* to the agent and return the assistant reply.

        This method is stateful: each call continues the same conversation
        session, enabling multi-turn dialogue.  The Agent Framework handles
        all tool invocation and history management internally – no manual
        polling loop is required.

        Args:
            message: User message text.

        Returns:
            The assistant's reply as a plain string.

        Raises:
            ValueError: If required environment variables are missing.
        """
        agent = self._get_agent()
        session = self._get_session()
        response = await agent.run(message, session=session)
        return response.text or "[No response from agent]"

    def reset(self) -> None:
        """Reset the conversation session, starting a fresh dialogue."""
        self._session = None
        logger.debug("Conversation session reset.")

    def delete_agent(self) -> None:
        """Clear the local Agent instance (releases resources)."""
        self._agent = None
        self._session = None
        logger.debug("Agent instance cleared.")
