# grocery-cli

A grocery management CLI that bridges a Google Tasks shopping list with Kroger's cart API. Fuzzy-matches casual item names against a personal purchase history catalog and syncs resolved products to your Kroger cart for pickup.

Built to be operated by an AI assistant (Claude, GPT, etc.) on behalf of a human. See [AGENTS.md](AGENTS.md) for agent setup, [skills/SKILL.md](skills/SKILL.md) for the operational playbook, and [docs/catalog-refresh.md](docs/catalog-refresh.md) for keeping your product catalog up to date.

## Features

- **List management** — Add, remove, check off, and clear items on a Google Tasks shopping list
- **Aisle-sorted insertion** — Items are inserted in store-walk order (Produce → Bakery → Dairy → … → Personal Care)
- **Product catalog** — Fuzzy match against your purchase history for fast, accurate resolution
- **Kroger cart sync** — Push your grocery list to a Kroger/City Market cart with one command
- **Dry-run mode** — Preview resolutions with match scores and sources before committing
- **API fallback** — Items not in your catalog are searched via Kroger's product API
- **Product images** — Kroger API returns product image URLs for visual confirmation

## Prerequisites

- Python 3.10+
- [`gog` CLI](https://github.com/jychp/gog) — Google Tasks access (authenticated)
- [Kroger Developer account](https://developer.kroger.com) — Register an app for OAuth credentials

## Quick Start

```bash
# Clone and install
git clone https://github.com/sleechie/grocery-cli.git
cd grocery-cli
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Google Tasks IDs, Kroger API credentials, and store ID

# Set up catalog
cp data/catalog.example.json data/catalog.json

# Authenticate with Kroger
python grocery.py auth url
# Open the URL, authorize, paste back the redirect URL:
python grocery.py auth exchange "http://localhost:8000/callback?code=YOUR_CODE"

# Use it
python grocery.py list add "bananas" "eggs" "bread"
python grocery.py list
python grocery.py cart sync --dry-run
python grocery.py cart sync
```

## Command Reference

| Command | Description |
|---------|-------------|
| `grocery list` | Show current grocery list |
| `grocery list add "item1" "item2"` | Add items (aisle-sorted) |
| `grocery list remove "item"` | Remove item (fuzzy match) |
| `grocery list check "item"` | Mark item complete |
| `grocery list uncheck "item"` | Unmark completed item |
| `grocery list clear` | Delete completed items |
| `grocery search <query>` | Fuzzy search product catalog |
| `grocery catalog` | Show top items by purchase frequency |
| `grocery catalog add --upc UPC --name NAME` | Add/update catalog product |
| `grocery resolve <query>` | Show catalog matches with scores |
| `grocery resolve <query> --api` | Also search Kroger product API |
| `grocery cart sync` | Push list items to Kroger cart |
| `grocery cart sync --dry-run` | Preview sync without pushing |
| `grocery cart add "item"` | Add directly to cart (skip list) |
| `grocery auth url` | Print OAuth URL |
| `grocery auth exchange <code>` | Exchange auth code for tokens |

## Configuration

All configuration lives in `.env` (see `.env.example`):

| Variable | Description |
|----------|-------------|
| `GROCERY_TASK_LIST_ID` | Google Tasks list ID |
| `GROCERY_PARENT_TASK_ID` | Parent task ID for grocery sub-tasks |
| `KROGER_CLIENT_ID` | Kroger API client ID |
| `KROGER_CLIENT_SECRET` | Kroger API client secret |
| `KROGER_REDIRECT_URI` | OAuth redirect URI |
| `KROGER_STORE_ID` | Your Kroger store ID |
| `KROGER_DIVISION` | Store division number |
| `CATALOG_PATH` | Path to product catalog JSON |
| `TOKEN_DIR` | Directory for OAuth token storage |

## Architecture

```
grocery-cli/
├── grocery.py         # Entry point
├── grocery/
│   ├── cli.py         # Argparse CLI
│   ├── tasklist.py    # Google Tasks wrapper
│   ├── catalog.py     # Product catalog + fuzzy search
│   ├── kroger.py      # Kroger OAuth + API
│   └── config.py      # Env var config + aisle-sort logic
├── data/
│   └── catalog.json   # Your product catalog (gitignored)
├── skills/
│   └── SKILL.md       # Agent skill definition
├── AGENTS.md          # Agent setup guide
└── .env               # Your credentials (gitignored)
```

### Resolution Pipeline

```
"ham" → Catalog fuzzy search → Score ≥ 70%? → Use match
                                    ↓ no
                              Kroger API search → Found? → Confirm with user
                                                    ↓ no
                                              Flag as unresolved
```

## Building Your Catalog

Start with the example: `cp data/catalog.example.json data/catalog.json`

The catalog grows organically — every time you confirm a new product during cart sync, add it with `grocery catalog add`. Over time it becomes a personalized database of everything you buy.

For a head start, you can bulk-import your entire Kroger purchase history. See **[Catalog Refresh](docs/catalog-refresh.md)** for the full guide. This uses Kroger's internal browser APIs to extract every product you've ever purchased, with frequency data.

## For AI Agents

This tool is designed to be operated by an AI assistant, not directly by a human. If you're an agent setting this up:

- **[AGENTS.md](AGENTS.md)** — Installation and configuration guide
- **[skills/SKILL.md](skills/SKILL.md)** — Operational playbook (workflow, commands, confidence tiers, ambiguity handling)

## License

MIT
