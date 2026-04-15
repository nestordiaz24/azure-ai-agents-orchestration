"""
product_catalog.py – Product catalog tool for the recommendation agent.

Loads a synthetic product catalog from a JSON file and exposes two
pure-Python functions:

* ``search_products(query)``    – keyword search across name/description/tags
* ``get_recommendations(product_id)`` – returns related products by shared tags

These functions are the "tool" implementations that the agent invokes when
answering user queries.  Because they rely only on a local JSON file, they
work without any Azure credentials.
"""

import json
import pathlib
from typing import Any


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CATALOG: list[dict[str, Any]] | None = None
_DEFAULT_PATH = pathlib.Path(__file__).parent.parent / "data" / "products.json"


def _load_catalog(path: pathlib.Path | str | None = None) -> list[dict[str, Any]]:
    """Load and cache the product catalog from *path* (JSON array).

    Args:
        path: Filesystem path to the products JSON file.  Defaults to the
              bundled ``data/products.json`` when *None*.

    Returns:
        List of product dictionaries.

    Raises:
        FileNotFoundError: If the JSON file does not exist at *path*.
        ValueError: If the file does not contain a JSON array.
    """
    global _CATALOG
    if _CATALOG is not None and path is None:
        return _CATALOG

    resolved = pathlib.Path(path) if path else _DEFAULT_PATH
    if not resolved.exists():
        raise FileNotFoundError(f"Product catalog not found: {resolved}")

    with resolved.open(encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, list):
        raise ValueError(
            f"Expected a JSON array in {resolved}, got {type(data).__name__}"
        )

    if path is None:
        _CATALOG = data
    return data


def _reset_cache() -> None:
    """Reset the in-memory catalog cache (used in tests)."""
    global _CATALOG
    _CATALOG = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def search_products(
    query: str,
    catalog_path: pathlib.Path | str | None = None,
) -> list[dict[str, Any]]:
    """Search the product catalog using keyword matching.

    Matches *query* terms (case-insensitive) against each product's ``name``,
    ``description``, and ``tags`` fields.  Returns all products that contain
    **at least one** query term.

    Args:
        query: Space-separated keyword(s) to search for.
        catalog_path: Optional override path to a products JSON file.

    Returns:
        List of matching product dictionaries, ordered by match score
        (number of matching fields) descending.  Empty list if nothing matches
        or *query* is blank.
    """
    query = query.strip()
    if not query:
        return []

    catalog = _load_catalog(catalog_path)
    terms = [t.lower() for t in query.split() if t]

    scored: list[tuple[int, dict[str, Any]]] = []
    for product in catalog:
        searchable = " ".join(
            [
                product.get("name", ""),
                product.get("description", ""),
                " ".join(product.get("tags", [])),
                product.get("category", ""),
            ]
        ).lower()

        score = sum(1 for term in terms if term in searchable)
        if score > 0:
            scored.append((score, product))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored]


def get_recommendations(
    product_id: str,
    catalog_path: pathlib.Path | str | None = None,
) -> list[dict[str, Any]]:
    """Return products recommended for a given product ID.

    Recommendations are determined by the ``related_products`` list on the
    source product, supplemented by any products sharing one or more category
    tags with the source (excluding the source product itself).

    Args:
        product_id: The ``id`` field of the source product.
        catalog_path: Optional override path to a products JSON file.

    Returns:
        List of recommended product dictionaries.  Empty list if *product_id*
        is not found or no related products exist.
    """
    product_id = product_id.strip()
    catalog = _load_catalog(catalog_path)

    # Build an index for O(1) look-ups
    index: dict[str, dict[str, Any]] = {p["id"]: p for p in catalog}

    source = index.get(product_id)
    if source is None:
        return []

    source_tags = set(source.get("tags", []))
    related_ids: list[str] = source.get("related_products", [])

    # Start with explicitly related products (preserve order)
    seen: set[str] = {product_id}
    recommendations: list[dict[str, Any]] = []

    for rid in related_ids:
        if rid != product_id and rid in index and rid not in seen:
            recommendations.append(index[rid])
            seen.add(rid)

    # Supplement with tag-similarity matches not already included
    for product in catalog:
        pid = product["id"]
        if pid in seen:
            continue
        shared_tags = source_tags & set(product.get("tags", []))
        if shared_tags:
            recommendations.append(product)
            seen.add(pid)

    return recommendations


def list_all_products(
    catalog_path: pathlib.Path | str | None = None,
) -> list[dict[str, Any]]:
    """Return the full product catalog.

    Args:
        catalog_path: Optional override path to a products JSON file.

    Returns:
        Full list of product dictionaries.
    """
    return list(_load_catalog(catalog_path))
