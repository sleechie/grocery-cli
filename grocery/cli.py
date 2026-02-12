#!/usr/bin/env python3
"""Grocery CLI — manage grocery list, search catalog, sync Kroger cart."""

import sys
import os
import argparse


def cmd_list(args):
    """Show or manage the grocery list."""
    from . import tasklist

    if args.action is None:
        items = tasklist.get_items(include_completed=False)
        if not items:
            print("Grocery list is empty.")
            return
        print(f"🛒 Grocery List ({len(items)} items):\n")
        for i, item in enumerate(items, 1):
            title = item.get('title', '(untitled)')
            if not title:
                continue
            print(f"  {i}. {title}")
        print()

    elif args.action == "add":
        added = tasklist.add_items_sorted(args.items)
        for task in added:
            title = task.get("title", "?")
            print(f"  ✓ Added: {title}")
        print(f"\n{len(added)} item(s) added.")

    elif args.action == "remove":
        try:
            title = tasklist.remove_item(args.item)
            print(f"  ✓ Removed: {title}")
        except ValueError as e:
            print(f"  ✗ {e}")
            sys.exit(1)

    elif args.action == "check":
        try:
            title = tasklist.check_item(args.item)
            print(f"  ✓ Checked off: {title}")
        except ValueError as e:
            print(f"  ✗ {e}")
            sys.exit(1)

    elif args.action == "uncheck":
        try:
            title = tasklist.uncheck_item(args.item)
            print(f"  ✓ Unchecked: {title}")
        except ValueError as e:
            print(f"  ✗ {e}")
            sys.exit(1)

    elif args.action == "clear":
        count = tasklist.clear_completed()
        if count:
            print(f"  ✓ Cleared {count} completed item(s).")
        else:
            print("  No completed items to clear.")


def cmd_search(args):
    """Search the product catalog."""
    from . import catalog

    query = " ".join(args.query)
    results = catalog.search(query, limit=args.n if hasattr(args, "n") else 10)
    if not results:
        print(f"No matches for '{query}'.")
        return
    print(f"🔍 Results for '{query}':\n")
    for item in results:
        score = item.get("_score", 0)
        count = item.get("purchaseCount", 0)
        print(f"  {item['name']}")
        print(f"    UPC: {item['upc']}  |  Purchased: {count}x  |  Match: {score}%")
    print()


def cmd_catalog(args):
    """Show top catalog items."""
    from . import catalog

    items = catalog.get_top_items(n=args.n, show_all=args.all)
    label = "Full" if args.all else f"Top {len(items)}"
    print(f"📦 {label} Catalog ({len(items)} items):\n")
    for i, item in enumerate(items, 1):
        count = item.get("purchaseCount", 0)
        last = item.get("lastPurchased", "?")
        print(f"  {i:>3}. {item['name']} ({count}x, last: {last})")
    print()


def _resolve_list_items(items):
    """Resolve list items against catalog and optionally API."""
    from . import catalog
    from . import kroger

    resolved = []
    unresolved = []

    for item in items:
        title = item.get("title", "").strip()
        if not title:
            continue
        results = catalog.search(title, limit=5)
        if results and results[0]["_score"] >= 70:
            match = results[0]
            resolved.append({
                "upc": match["upc"],
                "name": match["name"],
                "quantity": 1,
                "source": "catalog",
                "score": match["_score"],
                "purchaseCount": match.get("purchaseCount", 0),
                "original": title,
            })
        else:
            try:
                api_results = kroger.search_products(title, limit=1)
                if api_results:
                    top = api_results[0]
                    resolved.append({
                        "upc": top["upc"],
                        "name": top.get("description", title),
                        "quantity": 1,
                        "source": "api",
                        "score": None,
                        "purchaseCount": 0,
                        "original": title,
                    })
                else:
                    unresolved.append(title)
            except Exception:
                unresolved.append(title)

    return resolved, unresolved


def cmd_cart(args):
    """Kroger cart operations."""
    from . import tasklist
    from . import kroger
    from . import catalog as cat_mod

    if args.action == "sync":
        items = tasklist.get_items(include_completed=False)
        if not items:
            print("Grocery list is empty — nothing to sync.")
            return

        resolved, unresolved = _resolve_list_items(items)
        total = len(resolved) + len(unresolved)

        if getattr(args, 'dry_run', False):
            print(f"🛒 Dry Run — {total} items to sync:\n")
            for r in resolved:
                score_str = f"{r['score']}%" if r['score'] is not None else "N/A"
                if r['source'] == 'catalog':
                    print(f"  ✓ {r['original']} → {r['name']} (UPC: {r['upc']})")
                    print(f"    Score: {score_str} | Source: catalog | Purchased: {r['purchaseCount']}x")
                else:
                    print(f"  ⚠ {r['original']} → {r['name']} (UPC: {r['upc']})")
                    print(f"    Score: {score_str} | Source: api (not in catalog)")
            for name in unresolved:
                print(f"  ✗ {name} → No match found")
            print()
            return

        if resolved:
            print(f"🛒 Syncing {len(resolved)} item(s) to Kroger cart...\n")
            for r in resolved:
                print(f"  ✓ {r['name']} (UPC: {r['upc']})")
            try:
                kroger.add_to_cart(resolved)
                print(f"\n✓ {len(resolved)} item(s) added to cart.")
            except Exception as e:
                print(f"\n✗ Cart sync failed: {e}")

        if unresolved:
            print(f"\n⚠ Could not resolve {len(unresolved)} item(s):")
            for name in unresolved:
                print(f"  • {name}")

    elif args.action == "add":
        cart_items = []
        for name in args.items:
            match = cat_mod.resolve_item(name)
            if match:
                cart_items.append({"upc": match["upc"], "name": match["name"], "quantity": 1})
                print(f"  ✓ {match['name']} (UPC: {match['upc']})")
            else:
                print(f"  ✗ No catalog match for '{name}'")

        if cart_items:
            try:
                kroger.add_to_cart(cart_items)
                print(f"\n✓ {len(cart_items)} item(s) added to Kroger cart.")
            except Exception as e:
                print(f"\n✗ Cart add failed: {e}")

    else:
        print("Usage: grocery cart [sync|add]")


def cmd_resolve(args):
    """Resolve a query against catalog and optionally Kroger API."""
    from . import catalog

    query = " ".join(args.query)
    results = catalog.search(query, limit=5)

    print(f"🔍 Resolving '{query}':\n")
    if results:
        print("  Catalog matches:")
        for item in results:
            score = item.get("_score", 0)
            count = item.get("purchaseCount", 0)
            print(f"    {item['name']} (UPC: {item['upc']})")
            print(f"      Score: {score}% | Purchased: {count}x")
    else:
        print("  No catalog matches.")

    if getattr(args, 'api', False):
        from . import kroger
        print("\n  Kroger API results:")
        try:
            api_results = kroger.search_products(query, limit=5)
            if api_results:
                for p in api_results:
                    desc = p.get("description", "?")
                    upc = p.get("upc", "?")
                    brand = p.get("brand", "")
                    images = p.get("images", [])
                    img_url = ""
                    for img in images:
                        if img.get("perspective") == "front":
                            for size in img.get("sizes", []):
                                if size.get("size") == "medium":
                                    img_url = size.get("url", "")
                                    break
                    line = f"    {desc} (UPC: {upc})"
                    if brand:
                        line += f" [{brand}]"
                    print(line)
                    if img_url:
                        print(f"      Image: {img_url}")
            else:
                print("    No API results.")
        except Exception as e:
            print(f"    API error: {e}")
    print()


def cmd_catalog_sub(args):
    """Catalog subcommands (add)."""
    if args.catalog_action == "add":
        from . import catalog as cat_mod
        import json
        from .config import CATALOG_PATH

        upc = args.upc
        name = args.name

        with open(CATALOG_PATH) as f:
            data = json.load(f)

        existing = None
        for item in data["items"]:
            if item["upc"] == upc:
                existing = item
                break

        if existing:
            old_name = existing["name"]
            existing["name"] = name
            print(f"  ✓ Updated UPC {upc}: '{old_name}' → '{name}'")
        else:
            new_item = {
                "upc": upc,
                "name": name,
                "purchaseCount": 0,
                "lastPurchased": None,
            }
            data["items"].append(new_item)
            print(f"  ✓ Added: {name} (UPC: {upc})")

        data["items"].sort(key=lambda x: -x.get("purchaseCount", 0))

        with open(CATALOG_PATH, "w") as f:
            json.dump(data, f, indent=2)

        cat_mod._catalog = None
        print(f"  Catalog now has {len(data['items'])} items.")
    else:
        print("Usage: grocery catalog [add]")


def cmd_auth(args):
    """Authenticate with Kroger."""
    from . import kroger
    if args.action == "url":
        url = kroger.get_auth_url()
        print(url)
    elif args.action == "exchange":
        kroger.exchange_code(args.code)
    else:
        # No subcommand — show both steps
        url = kroger.get_auth_url()
        print(f"Step 1: Open this URL and authorize:\n\n{url}\n")
        print("Step 2: Run: grocery auth exchange <CODE_OR_REDIRECT_URL>")


def main():
    parser = argparse.ArgumentParser(prog="grocery", description="Grocery list, catalog & cart CLI")
    subparsers = parser.add_subparsers(dest="command")

    # list
    list_parser = subparsers.add_parser("list", help="View/manage grocery list")
    list_sub = list_parser.add_subparsers(dest="action")

    add_p = list_sub.add_parser("add", help="Add items")
    add_p.add_argument("items", nargs="+")

    rm_p = list_sub.add_parser("remove", help="Remove an item")
    rm_p.add_argument("item")

    chk_p = list_sub.add_parser("check", help="Mark item complete")
    chk_p.add_argument("item")

    unchk_p = list_sub.add_parser("uncheck", help="Unmark completed item")
    unchk_p.add_argument("item")

    list_sub.add_parser("clear", help="Clear completed items")

    # search
    search_parser = subparsers.add_parser("search", help="Search product catalog")
    search_parser.add_argument("query", nargs="+")
    search_parser.add_argument("-n", type=int, default=10)

    # catalog
    cat_parser = subparsers.add_parser("catalog", help="Show top catalog items or manage catalog")
    cat_parser.add_argument("--all", action="store_true")
    cat_parser.add_argument("-n", type=int, default=20)
    cat_sub = cat_parser.add_subparsers(dest="catalog_action")
    cat_add_p = cat_sub.add_parser("add", help="Add a product to the catalog")
    cat_add_p.add_argument("--upc", required=True, help="Product UPC")
    cat_add_p.add_argument("--name", required=True, help="Product name")

    # cart
    cart_parser = subparsers.add_parser("cart", help="Kroger cart operations")
    cart_sub = cart_parser.add_subparsers(dest="action")
    sync_p = cart_sub.add_parser("sync", help="Sync list to Kroger cart")
    sync_p.add_argument("--dry-run", action="store_true", help="Show what would sync without pushing to Kroger")
    cart_add = cart_sub.add_parser("add", help="Add items directly to cart")
    cart_add.add_argument("items", nargs="+")

    # resolve
    resolve_parser = subparsers.add_parser("resolve", help="Resolve a query against catalog/API")
    resolve_parser.add_argument("query", nargs="+")
    resolve_parser.add_argument("--api", action="store_true", help="Also search Kroger product API")

    # auth
    auth_parser = subparsers.add_parser("auth", help="Authenticate with Kroger")
    auth_sub = auth_parser.add_subparsers(dest="action")
    auth_sub.add_parser("url", help="Print the OAuth authorization URL")
    exchange_p = auth_sub.add_parser("exchange", help="Exchange auth code for tokens")
    exchange_p.add_argument("code", help="Authorization code or full redirect URL")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "list": cmd_list,
        "search": cmd_search,
        "catalog": lambda a: cmd_catalog_sub(a) if getattr(a, 'catalog_action', None) else cmd_catalog(a),
        "cart": cmd_cart,
        "resolve": cmd_resolve,
        "auth": cmd_auth,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
