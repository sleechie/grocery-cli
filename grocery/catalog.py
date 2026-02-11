"""Product catalog search with fuzzy matching."""

import json
from thefuzz import fuzz
from .config import CATALOG_PATH

_catalog = None


def load_catalog() -> list[dict]:
    """Load and cache the product catalog."""
    global _catalog
    if _catalog is None:
        with open(CATALOG_PATH) as f:
            data = json.load(f)
        _catalog = data["items"]
    return _catalog


def search(query: str, limit: int = 10) -> list[dict]:
    """Fuzzy search catalog. Returns matches sorted by score, tiebreak by purchaseCount."""
    catalog = load_catalog()
    results = []
    for item in catalog:
        score = fuzz.token_set_ratio(query.lower(), item["name"].lower())
        if score >= 50:
            results.append({**item, "_score": score})
    results.sort(key=lambda x: (-x["_score"], -x.get("purchaseCount", 0)))
    return results[:limit]


def resolve_item(name: str) -> dict | None:
    """Best single match. Returns top result if score >= 70, else None."""
    results = search(name, limit=5)
    if results and results[0]["_score"] >= 70:
        return results[0]
    return None


def get_top_items(n: int = 20, show_all: bool = False) -> list[dict]:
    """Top N items by purchase count."""
    catalog = load_catalog()
    items = sorted(catalog, key=lambda x: -x.get("purchaseCount", 0))
    if show_all:
        return items
    return items[:n]
