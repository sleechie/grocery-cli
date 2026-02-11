---
name: grocery-list
description: Manage the user's grocery list via Google Tasks. Use when asked to add, remove, check off, view, or clear grocery/shopping items.
---

# Grocery List

The `grocery` CLI manages the grocery list (Google Tasks), product catalog (with purchase history), and Kroger cart sync.

**Designed for agent use** — this CLI is meant for an AI assistant to operate on behalf of the user, not for the user to run directly.

## Workflow

The typical flow for grocery orders:

1. **`grocery list add`** — User says what they need in plain language, agent adds items
2. **`grocery cart sync --dry-run`** — Review what would be synced (product matches, confidence)
3. **Confirm with user** — Show dry-run results, ask if matches look right
4. **`grocery cart sync`** — Push confirmed items to Kroger cart
5. **`grocery catalog add`** — Add any new products (from API fallback) to local catalog for future use

**$35 free pickup threshold** — Remind the user if the cart is under $35, as that's the minimum for free pickup.

## Commands

### List Management

```bash
grocery list                              # Show current list (active items only)
grocery list add "bananas" "ham" "eggs"   # Add one or more items (store-order sorted)
grocery list remove "bananas"             # Remove item by name (fuzzy match)
grocery list check "bananas"              # Mark item as completed
grocery list uncheck "bananas"            # Unmark a completed item
grocery list clear                        # Clear ONLY completed items
```

### Product Catalog

```bash
grocery search <query>        # Fuzzy search local catalog
grocery search yogurt -n 5    # Limit results
grocery catalog               # Top 20 items by purchase frequency
grocery catalog --all         # Full catalog
grocery catalog -n 10         # Top N items
```

#### `grocery catalog add`

Append or update a product in the catalog:

```bash
grocery catalog add --upc "0003077209166" --name "Tide Pods Spring Meadow 76ct"
```

- If UPC exists: updates the name
- If new: appends with `purchaseCount: 0, lastPurchased: null`
- Maintains sorted-by-purchaseCount order
- Use this after API-sourced products are confirmed correct

### Product Resolution

```bash
grocery resolve "ham"           # Show top 5 catalog matches with scores
grocery resolve "ham" --api     # Also search Kroger product API
```

Shows catalog matches with fuzzy scores and purchase counts, plus Kroger API results (with product image URLs) when `--api` is set.

**Product images:** Kroger API returns image URLs for visual confirmation:
```
https://www.kroger.com/product/images/medium/front/<UPC>
```

### Kroger Cart

```bash
grocery cart sync             # Push all active list items → Kroger cart
grocery cart sync --dry-run   # Show what WOULD sync without pushing
grocery cart add "bananas"    # Add item directly to Kroger cart (skip list)
```

### Authentication

```bash
grocery auth                  # Run Kroger OAuth flow (one-time setup)
```

## Confidence Tiers

The fuzzy matching (`thefuzz.token_set_ratio`) produces scores used for resolution:

| Score | Behavior |
|-------|----------|
| **70+ (clear winner)** | Auto-resolve confidently — top match is used |
| **70+ (multiple close)** | Ask user to pick — several strong candidates |
| **50–69** | Low confidence — show match but ask for confirmation |
| **Below 50** | No match — falls through to API or unresolved |

Tiebreaker: when scores are equal, higher `purchaseCount` wins (prefer frequently bought items).

## Agent Workflow — Cart Sync Playbook

When the user says "sync my cart" or "load my cart," follow this sequence:

### Step 1: Dry Run
```bash
grocery cart sync --dry-run
```
Review every item. Look for:
- **⚠ API fallbacks** — items not in catalog that were resolved via Kroger API
- **✗ Unresolved items** — nothing matched at all
- **Multiple close matches** — catalog might pick the wrong variant

### Step 2: Handle Ambiguity
For any item that's ambiguous, uncertain, or API-sourced:
1. Run `grocery resolve "<item>" --api` to see all options
2. Pull product images for visual confirmation
3. Ask the user which one they want
4. If they want price comparison, the API returns pricing — search and compare

### Step 3: Save New Products
After the user confirms an API-sourced product:
```bash
grocery catalog add --upc "<UPC>" --name "Descriptive Name With Size"
```
**Naming convention:** Use descriptive names with size/variant info. Examples:
- ✓ "Takis Fuego Small Bag 3.25oz"
- ✓ "Tide Pods Spring Meadow 76ct"
- ✗ "Takis Fuego Hot Chili Pepper & Lime Tortilla Chips" (which size??)

### Step 4: Sync for Real
Once everything looks good:
```bash
grocery cart sync
```

### Step 5: Remind About Pickup
- $35+ = free pickup, under $35 = fee
- User schedules pickup time in the Kroger app (API doesn't support this)
- Cart is add-only — no way to view cart contents via API

## How It Works

- **List ops** wrap `gog tasks` CLI with `--json` parsing
- **Adding items** inserts each item at the correct aisle-order position using `--previous` flag
- **Store-aisle order:** 12 categories: Produce → Bakery → Dairy → Meat → Frozen → Snacks → Condiments → Canned → Baking → Beverages → Household → Personal Care
- **Fuzzy matching** uses `thefuzz.fuzz.token_set_ratio`, threshold 70+ for confident match, tiebreak by purchaseCount
- **Cart sync** resolves each active list item against local catalog first, falls back to Kroger product API, then pushes to Kroger's cart API

### Kroger Cart API Behavior
- **PUT/add-only** — no GET to view cart, no DELETE to remove items
- **Stacking:** Adding the same UPC multiple times increments quantity. Only sync once per session.
- **Modality:** All items added with `"modality": "PICKUP"`

## Architecture

```
grocery/
├── cli.py        # CLI entry point (argparse)
├── tasklist.py   # Google Tasks wrapper (gog tasks)
├── catalog.py    # Product catalog + fuzzy search
├── kroger.py     # Kroger API (auth, cart, product search)
└── config.py     # Configuration (env vars, aisle-sort logic)
```

Dependencies: `thefuzz[speedup]`, `kroger-api`, `python-dotenv`
