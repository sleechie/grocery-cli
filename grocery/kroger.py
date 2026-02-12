"""Kroger API integration for cart operations."""

import json
import os
import sys
from pathlib import Path

from .config import STORE_ID, KROGER_CLIENT_ID, TOKEN_DIR

# kroger-api library
try:
    from kroger_api import KrogerAPI
except ImportError:
    KrogerAPI = None


def _token_path() -> Path:
    return Path(TOKEN_DIR) / ".kroger_token_user.json"


def get_client() -> "KrogerAPI":
    """Get an authenticated Kroger API client with existing tokens."""
    if KrogerAPI is None:
        raise RuntimeError("kroger-api not installed. Run: pip install kroger-api")

    token_file = _token_path()
    if not token_file.exists():
        raise RuntimeError("Not authenticated. Run: grocery auth")

    client = KrogerAPI()

    with open(token_file) as f:
        token_info = json.load(f)

    client.client.token_info = token_info
    client.client.token_file = str(token_file)

    # Suppress noisy library output during token validation
    _stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    token_valid = client.test_current_token()
    sys.stdout.close()
    sys.stdout = _stdout

    if client.client.token_info and client.client.token_info != token_info:
        with open(token_file, "w") as f:
            json.dump(client.client.token_info, f, indent=2)

    if not token_valid:
        refresh_token = token_info.get("refresh_token")
        if refresh_token:
            try:
                new_token = client.client._get_token(
                    grant_type="refresh_token",
                    refresh_token=refresh_token
                )
                with open(token_file, "w") as f:
                    json.dump(new_token, f, indent=2)
                client.client.token_info = new_token
                if not client.test_current_token():
                    raise RuntimeError("Token refresh failed. Run: grocery auth")
            except Exception as e:
                raise RuntimeError(f"Token expired and refresh failed: {e}. Run: grocery auth")
        else:
            raise RuntimeError("Token expired. Run: grocery auth")

    return client


def search_products(query: str, limit: int = 5) -> list[dict]:
    """Search Kroger product API."""
    client = get_client()
    results = client.product.search_products(
        term=query,
        location_id=STORE_ID,
        limit=limit
    )
    return results.get("data", [])


def add_to_cart(items: list[dict]) -> dict:
    """Add items to Kroger cart. Each item needs 'upc' and 'quantity'."""
    client = get_client()
    cart_items = [{"upc": item["upc"], "quantity": item.get("quantity", 1), "modality": "PICKUP"}
                  for item in items]
    return client.cart.add_to_cart(items=cart_items)


def get_auth_url() -> str:
    """Generate the Kroger OAuth authorization URL."""
    if KrogerAPI is None:
        raise RuntimeError("kroger-api not installed. Run: pip install kroger-api")
    client = KrogerAPI()
    return client.authorization.get_authorization_url(
        scope="cart.basic:write product.compact",
    )


def exchange_code(code: str):
    """Exchange an authorization code (or full redirect URL) for tokens."""
    if KrogerAPI is None:
        raise RuntimeError("kroger-api not installed. Run: pip install kroger-api")

    # Extract code from full URL if needed
    if "code=" in code:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(code)
        code = parse_qs(parsed.query).get("code", [code])[0]

    client = KrogerAPI()
    token_info = client.client.get_token_with_authorization_code(code)

    token_file = _token_path()
    with open(token_file, "w") as f:
        json.dump(token_info, f, indent=2)

    print(f"✓ Authenticated! Token saved to {token_file}")
