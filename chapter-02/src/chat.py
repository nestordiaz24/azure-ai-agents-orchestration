"""
chat.py – Interactive CLI for the Product Recommendation Agent.

Usage:
    python src/chat.py [--mode catalog|agent]

Modes:
    catalog  (default) – Use the local product catalog tool directly.
                         No Azure credentials required.
    agent             – Use the full Azure-hosted agent for responses.
                        Requires AZURE_AI_PROJECT_ENDPOINT to be set.

Type your message and press Enter.  Type 'quit' or 'exit' to stop.
Type 'reset' to clear conversation history (agent mode only).
"""

import argparse
import asyncio
import sys
from typing import Callable

from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Catalog-only mode (no Azure required)
# ---------------------------------------------------------------------------


def _catalog_reply(query: str) -> str:
    """Return a formatted recommendation from the local catalog tool.

    Args:
        query: User query string.

    Returns:
        Formatted text with matching products and recommendations.
    """
    from src.product_catalog import get_recommendations, search_products  # noqa: PLC0415

    products = search_products(query)
    if not products:
        return "No products matched your query. Try different keywords."

    lines: list[str] = ["Matching products:"]
    for p in products[:5]:  # Cap to top-5 for readability
        lines.append(
            f"  • [{p['id']}] {p['name']} – ${p['price']:.2f}\n"
            f"    {p['description']}\n"
            f"    Tags: {', '.join(p['tags'])}"
        )

    # Show recommendations for the top match
    top_id = products[0]["id"]
    recs = get_recommendations(top_id)
    if recs:
        lines.append(f"\nYou might also consider (related to {products[0]['name']}):")
        for r in recs[:3]:
            lines.append(f"  → [{r['id']}] {r['name']} – ${r['price']:.2f}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent mode (requires Azure)
# ---------------------------------------------------------------------------


def _build_agent_reply() -> Callable[[str], str]:
    """Create a stateful async reply function backed by the recommendation agent."""
    from src.recommendation_agent import RecommendationAgent  # noqa: PLC0415

    agent = RecommendationAgent()

    async def _reply(message: str) -> str:
        if message.lower() == "reset":
            agent.reset()
            return "[Conversation reset. Starting a new session.]"
        return await agent.chat(message)

    return _reply


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def _print_banner(mode: str) -> None:
    """Print the startup banner."""
    print("\n🤖  AcmeCorp Product Recommendation Agent")
    print(f"    Mode: {mode}")
    if mode == "catalog":
        print("    (Running in catalog mode – no Azure credentials required)")
    print("    Type 'quit' or 'exit' to end the session.")
    if mode == "agent":
        print("    Type 'reset' to start a new conversation thread.")
    print()


async def _main_async(mode: str) -> None:
    """Async main loop for the interactive CLI."""
    if mode == "agent":
        try:
            reply_fn = _build_agent_reply()
        except (ValueError, ImportError) as exc:
            print(f"ERROR: Could not initialize agent: {exc}", file=sys.stderr)
            sys.exit(1)
        except Exception as exc:  # noqa: BLE001 – Azure SDK errors vary widely
            print(f"ERROR: Unexpected error during agent initialization: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        reply_fn = None  # catalog mode uses sync _catalog_reply directly

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

        try:
            if mode == "agent" and reply_fn is not None:
                reply = await reply_fn(user_input)
            else:
                reply = _catalog_reply(user_input)
        except (ValueError, RuntimeError) as exc:
            reply = f"[Error: {exc}]"
        except Exception as exc:  # noqa: BLE001 – defensive catch for unforeseen SDK errors
            reply = f"[Unexpected error: {exc}]"

        print(f"\nAgent: {reply}\n")


def main() -> None:
    """Entry point for the interactive CLI."""
    parser = argparse.ArgumentParser(
        description="Interactive CLI for the AcmeCorp Product Recommendation Agent."
    )
    parser.add_argument(
        "--mode",
        choices=["catalog", "agent"],
        default="catalog",
        help=(
            "catalog: use local keyword search (no Azure required). "
            "agent: use the full Azure AI agent (requires AZURE_AI_PROJECT_ENDPOINT)."
        ),
    )
    args = parser.parse_args()

    _print_banner(args.mode)
    asyncio.run(_main_async(args.mode))


if __name__ == "__main__":
    main()
