"""
test_product_catalog.py – Unit tests for the product catalog tool.

These tests exercise pure-Python logic in ``product_catalog.py`` and do
**not** require Azure credentials.  Run with:

    pytest chapter-02/tests/

or from chapter-02/:

    pytest tests/
"""

import json
import pathlib
import tempfile

import pytest

# Adjust sys.path so the src package is importable when running from the
# chapter-02 directory or the repository root.
import sys

_CHAPTER_02 = pathlib.Path(__file__).parent.parent
if str(_CHAPTER_02) not in sys.path:
    sys.path.insert(0, str(_CHAPTER_02))

from src.product_catalog import (  # noqa: E402
    _reset_cache,
    get_recommendations,
    list_all_products,
    search_products,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_PRODUCTS = [
    {
        "id": "TEST-001",
        "name": "Widget Pro",
        "description": "A professional widget for enterprise use.",
        "category": "tools",
        "tags": ["tools", "enterprise", "productivity"],
        "price": 99.99,
        "related_products": ["TEST-002"],
    },
    {
        "id": "TEST-002",
        "name": "Widget Lite",
        "description": "A lightweight widget for small teams.",
        "category": "tools",
        "tags": ["tools", "lightweight", "productivity"],
        "price": 49.99,
        "related_products": ["TEST-001"],
    },
    {
        "id": "TEST-003",
        "name": "DataVault",
        "description": "Secure data storage and management platform.",
        "category": "security",
        "tags": ["security", "data", "storage"],
        "price": 199.99,
        "related_products": [],
    },
]


@pytest.fixture()
def catalog_file(tmp_path: pathlib.Path) -> pathlib.Path:
    """Write SAMPLE_PRODUCTS to a temp JSON file and return its path.

    ``tmp_path`` is a built-in pytest fixture that provides a temporary
    directory unique to each test invocation.
    """
    path = tmp_path / "products.json"
    path.write_text(json.dumps(SAMPLE_PRODUCTS), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def reset_catalog_cache():
    """Reset the in-memory catalog cache before each test."""
    _reset_cache()
    yield
    _reset_cache()


# ---------------------------------------------------------------------------
# search_products tests
# ---------------------------------------------------------------------------


class TestSearchProducts:
    """Tests for ``search_products()``."""

    def test_returns_empty_for_blank_query(self, catalog_file):
        assert search_products("", catalog_path=catalog_file) == []

    def test_returns_empty_for_whitespace_query(self, catalog_file):
        assert search_products("   ", catalog_path=catalog_file) == []

    def test_matches_by_name(self, catalog_file):
        results = search_products("Widget Pro", catalog_path=catalog_file)
        ids = [p["id"] for p in results]
        assert "TEST-001" in ids

    def test_case_insensitive_match(self, catalog_file):
        results = search_products("WIDGET", catalog_path=catalog_file)
        ids = [p["id"] for p in results]
        assert "TEST-001" in ids
        assert "TEST-002" in ids

    def test_matches_by_description(self, catalog_file):
        results = search_products("enterprise", catalog_path=catalog_file)
        ids = [p["id"] for p in results]
        assert "TEST-001" in ids

    def test_matches_by_tag(self, catalog_file):
        results = search_products("security", catalog_path=catalog_file)
        ids = [p["id"] for p in results]
        assert "TEST-003" in ids

    def test_no_match_returns_empty(self, catalog_file):
        results = search_products("xyzzy_nonexistent", catalog_path=catalog_file)
        assert results == []

    def test_multi_term_increases_score(self, catalog_file):
        """A product matching more terms should rank higher."""
        results = search_products("widget enterprise", catalog_path=catalog_file)
        # TEST-001 matches both "widget" and "enterprise"; TEST-002 matches only "widget"
        assert results[0]["id"] == "TEST-001"

    def test_returns_list_of_dicts(self, catalog_file):
        results = search_products("widget", catalog_path=catalog_file)
        assert isinstance(results, list)
        for p in results:
            assert isinstance(p, dict)
            assert "id" in p

    def test_all_fields_present(self, catalog_file):
        results = search_products("Widget Pro", catalog_path=catalog_file)
        required_keys = {"id", "name", "description", "category", "tags", "price"}
        assert required_keys.issubset(results[0].keys())


# ---------------------------------------------------------------------------
# get_recommendations tests
# ---------------------------------------------------------------------------


class TestGetRecommendations:
    """Tests for ``get_recommendations()``."""

    def test_returns_empty_for_unknown_id(self, catalog_file):
        results = get_recommendations("DOES-NOT-EXIST", catalog_path=catalog_file)
        assert results == []

    def test_returns_related_products(self, catalog_file):
        results = get_recommendations("TEST-001", catalog_path=catalog_file)
        ids = [p["id"] for p in results]
        assert "TEST-002" in ids

    def test_source_product_not_in_results(self, catalog_file):
        results = get_recommendations("TEST-001", catalog_path=catalog_file)
        ids = [p["id"] for p in results]
        assert "TEST-001" not in ids

    def test_no_duplicates_in_results(self, catalog_file):
        results = get_recommendations("TEST-001", catalog_path=catalog_file)
        ids = [p["id"] for p in results]
        assert len(ids) == len(set(ids))

    def test_shared_tag_products_included(self, catalog_file):
        """Both TEST-001 and TEST-002 share the 'tools' category tag."""
        results = get_recommendations("TEST-001", catalog_path=catalog_file)
        ids = [p["id"] for p in results]
        # TEST-002 is in related_products AND shares tags
        assert "TEST-002" in ids

    def test_returns_list_of_dicts(self, catalog_file):
        results = get_recommendations("TEST-001", catalog_path=catalog_file)
        assert isinstance(results, list)
        for p in results:
            assert isinstance(p, dict)

    def test_empty_related_products_still_checks_tags(self, catalog_file):
        """TEST-003 has no related_products but may match via shared tags."""
        results = get_recommendations("TEST-003", catalog_path=catalog_file)
        # TEST-003 has only "security", "data", "storage" tags – no overlap with others
        ids = [p["id"] for p in results]
        assert "TEST-003" not in ids


# ---------------------------------------------------------------------------
# list_all_products tests
# ---------------------------------------------------------------------------


class TestListAllProducts:
    """Tests for ``list_all_products()``."""

    def test_returns_all_products(self, catalog_file):
        results = list_all_products(catalog_path=catalog_file)
        assert len(results) == len(SAMPLE_PRODUCTS)

    def test_returns_copy(self, catalog_file):
        """Modifying the returned list should not affect the catalog."""
        results = list_all_products(catalog_path=catalog_file)
        results.clear()
        assert len(list_all_products(catalog_path=catalog_file)) == len(SAMPLE_PRODUCTS)


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for error conditions in the catalog tool."""

    def test_missing_file_raises_file_not_found(self, tmp_path):
        missing = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError, match="Product catalog not found"):
            search_products("widget", catalog_path=missing)

    def test_invalid_json_structure_raises_value_error(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text('{"not": "a list"}', encoding="utf-8")
        with pytest.raises(ValueError, match="Expected a JSON array"):
            search_products("widget", catalog_path=bad_file)


# ---------------------------------------------------------------------------
# Integration: use the real bundled products.json
# ---------------------------------------------------------------------------


class TestRealCatalog:
    """Smoke tests against the actual bundled data/products.json."""

    def test_can_load_real_catalog(self):
        """The real catalog should contain at least 10 products."""
        products = list_all_products()
        assert len(products) >= 10

    def test_all_products_have_required_fields(self):
        products = list_all_products()
        required = {"id", "name", "description", "category", "tags", "price"}
        for p in products:
            missing = required - p.keys()
            assert not missing, f"Product {p.get('id')} is missing fields: {missing}"

    def test_monitoring_search(self):
        results = search_products("monitoring")
        assert len(results) > 0

    def test_recommendations_for_known_product(self):
        results = get_recommendations("ACME-MON-001")
        assert len(results) > 0
        ids = [p["id"] for p in results]
        assert "ACME-MON-001" not in ids
