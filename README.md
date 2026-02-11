# grocery-cli

An AI-agent-operated grocery CLI that manages a Google Tasks shopping list, fuzzy-matches items against a personal purchase history catalog, and syncs to Kroger cart via API. Designed to be operated by an LLM assistant on behalf of a human.

## Features

- **List management** — Add, remove, check off, and clear grocery items on a Google Tasks list
- **Aisle-sorted insertion** — New items are inserted in store-walk order (Produce → Bakery → Dairy → … → Personal Care)
- **Catalog search** — Fuzzy match against your personal purchase history for fast, accurate product resolution
- **Kroger cart sync** — Push your entire grocery list to a Kroger/City Market cart with one command
- **Dry-run mode** — Preview exactly what would sync (with match scores and sources) before committing
- **Product images** — Kroger API returns product image URLs for visual confirmation
- **API fallback** — Items not in your catalog are searched via Kroger's product API

## Prerequisites

- **Python 3.10+**
- **[`gog` CLI](https://github.com/jychp/gog)** — Google Tasks CLI (authenticated with your Google account)
- **[Kroger Developer account](https://developer.kroger.com)** — Register an app to get client ID/secret

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/grocery-cli.git
cd grocery-cli

# Configure
cp .env.example .env
# Edit .env with your IDs (see comments in .env.example)

# Set up catalog
cp data/catalog.example.json data/catalog.json
# (Replace with your own catalog data over time)

# Install dependencies
pip install -r requirements.txt

# Authenticate with Kroger (one-time)
python grocery auth

# Use it
python grocery list add "bananas" "eggs" "bread"
python grocery list
python grocery cart sync --dry-run
python grocery cart sync
```

## Command Reference

| Command | Description |
|---------|-------------|
| `grocery list` | Show current grocery list |
| `grocery list add "item1" "item2"` | Add items (aisle-sorted) |
| `grocery list remove "item"` | Remove item (fuzzy match) |
| `grocery list check "item"` | Mark item complete |
| `grocery list uncheck "item"` | Unmark completed item |
| `grocery list clear` | Delete all completed items |
| `grocery search <query>` | Fuzzy search product catalog |
| `grocery search <query> -n 5` | Limit search results |
| `grocery catalog` | Show top 20 items by purchase frequency |
| `grocery catalog --all` | Show full catalog |
| `grocery catalog add --upc UPC --name NAME` | Add/update a catalog product |
| `grocery resolve <query>` | Show catalog matches with scores |
| `grocery resolve <query> --api` | Also search Kroger product API |
| `grocery cart sync` | Push active list items to Kroger cart |
| `grocery cart sync --dry-run` | Preview sync without pushing |
| `grocery cart add "item"` | Add item directly to cart |
| `grocery auth` | Run Kroger OAuth flow |

## How It Works

### Architecture

```
grocery-cli/
├── grocery          # Wrapper script (entry point)
├── grocery/
│   ├── cli.py       # CLI (argparse)
│   ├── tasklist.py  # Google Tasks wrapper (gog CLI)
│   ├── catalog.py   # Product catalog + fuzzy search
│   ├── kroger.py    # Kroger API (auth, cart, product search)
│   └── config.py    # Configuration (env vars, aisle-sort logic)
├── data/
│   └── catalog.json # Your product catalog (gitignored)
└── .env             # Your credentials (gitignored)
```

### Resolution Pipeline

When syncing cart, each grocery list item is resolved in order:

1. **Catalog search** — Fuzzy match (`thefuzz.token_set_ratio`) against local catalog
2. **Kroger API fallback** — If no catalog match ≥70%, searches Kroger's product API
3. **Unresolved** — If both fail, item is flagged for manual review

Score tiebreaker: when fuzzy scores are equal, higher `purchaseCount` wins.

### Aisle Sorting

Items are inserted into the Google Tasks list in store-walk order using 12 categories:
Produce → Bakery/Deli → Dairy/Eggs → Meat/Seafood → Frozen → Snacks → Condiments → Canned Goods → Baking/Candy → Beverages → Household → Personal Care

### Kroger Cart API

- **Add-only** — No GET to view cart, no DELETE to remove. Check cart in the Kroger app.
- **Stacking** — Adding the same UPC increments quantity. Only sync once per session.
- **Modality** — All items added as `PICKUP`.

## Designed for AI Agents

This CLI is built to be operated by an LLM assistant (like Claude, GPT, etc.) rather than directly by a human. The typical agent workflow:

1. Human says "add bananas and eggs to my grocery list" in natural language
2. Agent parses intent and runs `grocery list add "bananas" "eggs"`
3. Human says "sync my cart" → Agent runs `grocery cart sync --dry-run`
4. Agent reviews results, asks human to confirm ambiguous matches
5. Agent runs `grocery cart sync` to push confirmed items
6. Agent adds any new API-discovered products to catalog for future use

The fuzzy matching, aisle sorting, and dry-run flow are all designed to minimize back-and-forth while keeping the human in the loop for uncertain matches.

## License

MIT
