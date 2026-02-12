# grocery-cli

A grocery management CLI designed to be operated by an AI assistant. It bridges a human-readable Google Tasks shopping list with Kroger's cart API, using fuzzy matching against a personal purchase history catalog to resolve casual item names ("ham") into exact products (Land O Frost Premium Black Forest Ham, UPC 0005190001613).

Your human adds items throughout the week in plain language. When it's time to order, you resolve everything, confirm ambiguous matches, and push to their Kroger cart in one shot.

## What It Does

- **List management** — CRUD operations on a Google Tasks shopping list, with automatic aisle-order sorting
- **Product catalog** — Fuzzy search against a local catalog built from the user's purchase history
- **Cart sync** — Resolve list items to real Kroger products (UPC codes) and push to cart via API
- **Dry-run mode** — Preview every resolution with match scores and sources before committing
- **API fallback** — Items not in the catalog get searched via Kroger's product API
- **Product images** — Pull Kroger product images for visual confirmation when matches are ambiguous

## Install as a Skill

### OpenClaw

Copy the skill into your workspace skills directory:

```bash
# From your OpenClaw workspace (e.g., ~/clawd/)
git clone https://github.com/sleechie/grocery-cli.git projects/grocery-cli

# Symlink the skill so OpenClaw discovers it
ln -s $(pwd)/projects/grocery-cli/skills/grocery-list $(pwd)/skills/grocery-list

# Install dependencies
pip install -r projects/grocery-cli/requirements.txt

# Make the CLI available
ln -s $(pwd)/projects/grocery-cli/grocery.py ~/bin/grocery
chmod +x projects/grocery-cli/grocery.py
```

OpenClaw loads skills from `<workspace>/skills/` at session start. The skill's `SKILL.md` tells the agent when and how to use the grocery commands. The agent will automatically invoke it when the user mentions groceries, shopping lists, or cart syncing.

Configure your credentials:

```bash
cp projects/grocery-cli/.env.example projects/grocery-cli/.env
# Edit .env with your IDs (see Configuration section below)
```

### Claude Code

Claude Code discovers skills from `.claude/skills/` directories in your project:

```bash
# From your project root
mkdir -p .claude/skills
git clone https://github.com/sleechie/grocery-cli.git .claude/skills/grocery-list

# Install dependencies
pip install -r .claude/skills/grocery-list/requirements.txt

# Configure
cp .claude/skills/grocery-list/.env.example .claude/skills/grocery-list/.env
# Edit .env with your IDs
```

Claude Code will automatically discover the `SKILL.md` and load it when relevant. You can also invoke it directly with `/grocery-list`.

For personal (cross-project) access, install to `~/.claude/skills/grocery-list/` instead.

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```env
# Google Tasks — get these from `gog tasks list --json`
GROCERY_TASK_LIST_ID=your-task-list-id
GROCERY_PARENT_TASK_ID=your-parent-task-id

# Kroger API — register at https://developer.kroger.com
KROGER_CLIENT_ID=your-client-id
KROGER_CLIENT_SECRET=your-client-secret
KROGER_REDIRECT_URI=http://localhost:8000/callback

# Your Kroger store — find yours at https://www.kroger.com/stores/search
KROGER_STORE_ID=70100123
KROGER_DIVISION=620

# Local paths
CATALOG_PATH=./data/catalog.json
TOKEN_DIR=.
```

### Google Tasks Setup

1. Install the [`gog` CLI](https://github.com/jychp/gog) and authenticate with your Google account
2. Create a task called "GROCERY LIST" in Google Tasks (or use an existing one)
3. Run `gog tasks list --json` to find your task list ID and the parent task ID

### Kroger Auth

The CLI uses OAuth2 to access Kroger's cart and product APIs. Auth is non-interactive so agents can drive the entire flow:

```bash
# Step 1: Generate the authorization URL
grocery auth url

# Step 2: Send the URL to your user — they open it, authorize, and get redirected
# The redirect will fail to load (localhost) — that's expected

# Step 3: Exchange the code from the redirect URL
grocery auth exchange "http://localhost:8000/callback?code=THE_AUTH_CODE"
```

Tokens auto-refresh. You only need to re-auth if the refresh token expires (rare).

### Building Your Catalog

Start with the example catalog:

```bash
cp data/catalog.example.json data/catalog.json
```

The catalog grows organically:
- When you resolve items via Kroger API during cart sync, add confirmed products with `grocery catalog add`
- For bulk import from purchase history, see the [Catalog Refresh](#catalog-refresh) section in the SKILL.md

## How to Use This (for agents)

This section describes the thinking behind the tool — not just the commands, but when and why to use each one.

### The Two Phases

**Phase 1: List Building (passive, throughout the week)**

Your user will say things like "add eggs and bread to my grocery list." Just run `grocery list add "eggs" "bread"`. No resolution needed — the list stores their exact words. It's a staging area, not a cart. Items get sorted by grocery store aisle automatically so the list reads in walking order.

The list is shared — the user's partner, roommate, etc. might also add items directly in Google Tasks. You'll see whatever's there when it's time to sync.

**Phase 2: Cart Sync (active, when ordering)**

When the user says "sync my cart" or "time to order groceries," this is where the intelligence kicks in:

```bash
grocery cart sync --dry-run
```

Review every line of output. You're looking for three things:

1. **✓ Confident matches (catalog, 70%+)** — These are fine. "Ham" → Black Forest Ham, purchased 25 times. No need to confirm.

2. **⚠ API fallbacks** — The item wasn't in the catalog, so it hit Kroger's search API. The first result might be wrong. Always confirm these with the user before syncing. Show them the product image:
   ```
   https://www.kroger.com/product/images/large/front/<UPC>
   ```
   Download it and send it in chat. Visual confirmation is faster than describing packaging.

3. **✗ Unresolved** — Nothing matched. Ask the user what they meant, search manually with `grocery resolve "<query>" --api`, and help them find the right product.

After resolving everything:
```bash
grocery cart sync
```

Then save any newly discovered products to the catalog so they're instant matches next time:
```bash
grocery catalog add --upc "0003077209166" --name "Tide Pods Spring Meadow 76ct"
```

**Naming tip:** Include size and variant in catalog names. "Takis Fuego Small Bag 3.25oz" is much more useful than "Takis Fuego Hot Chili Pepper & Lime Tortilla Chips" when there are multiple sizes.

### Handling Ambiguity

When the user says "add cheese" and there are 12 types of cheese in the catalog, don't silently pick one. Run `grocery resolve "cheese"` and show them the top matches with purchase counts. The most-bought one is usually right, but ask.

When the user asks for a specific product attribute ("the purple Tide Pods," "the small Takis bag"), use `grocery resolve "<query>" --api` and pull product images to confirm visually.

When the user wants the cheapest option, the Kroger API returns pricing in the product data. Search and compare.

### Important Constraints

- **Kroger's cart API is add-only.** No GET to view the cart, no DELETE to remove items. The user checks their cart in the Kroger app.
- **Adding the same UPC twice increments quantity.** Only sync once per session to avoid duplicates.
- **Pickup is free over $35.** Mention this if relevant.
- **The user schedules pickup in the app.** The API doesn't support time slot selection.

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
| `grocery auth` | Show auth steps |
| `grocery auth url` | Print OAuth authorization URL |
| `grocery auth exchange <code>` | Exchange auth code/redirect URL for tokens |

## Architecture

```
grocery-cli/
├── grocery.py         # Entry point wrapper
├── grocery/
│   ├── cli.py         # Argparse CLI
│   ├── tasklist.py    # Google Tasks wrapper (gog CLI)
│   ├── catalog.py     # Product catalog + fuzzy search (thefuzz)
│   ├── kroger.py      # Kroger OAuth + cart/product API
│   └── config.py      # Env var config + aisle-sort logic
├── data/
│   └── catalog.json   # Your product catalog (gitignored)
├── skills/
│   └── SKILL.md       # Agent skill definition
└── .env               # Your credentials (gitignored)
```

### Resolution Pipeline

```
User says "ham"
       ↓
Catalog fuzzy search (thefuzz.token_set_ratio)
       ↓
Score ≥ 70%? → Use catalog match (has UPC + purchase history)
       ↓ no
Kroger Product API search
       ↓
Results found? → Show to user for confirmation
       ↓ no
Flag as unresolved → Ask user what they meant
```

### Aisle Sort Order

Items are inserted into the list in store-walk order across 12 categories:

1. Produce  2. Bakery/Deli  3. Dairy/Eggs  4. Meat/Seafood  5. Frozen  6. Snacks  7. Condiments  8. Canned/Dry Goods  9. Baking/Candy  10. Beverages  11. Household  12. Personal Care

Each item is keyword-matched to a category and inserted at the correct position using Google Tasks' `--previous` parameter. Unknown items go to the end.

## License

MIT
