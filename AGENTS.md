# AGENTS.md — Setup Guide for AI Agents

This file is for you, the AI agent. It explains how to install and configure `grocery-cli` as a skill so you can manage your human's grocery list and Kroger cart.

Once set up, read `skills/SKILL.md` for the operational playbook — how to actually use the tool day-to-day.

## Install

### OpenClaw

```bash
# From your OpenClaw workspace (e.g., ~/clawd/)
git clone https://github.com/sleechie/grocery-cli.git projects/grocery-cli

# Symlink the skill so OpenClaw discovers it
ln -s $(pwd)/projects/grocery-cli/skills $(pwd)/skills/grocery-list

# Install Python dependencies
pip install -r projects/grocery-cli/requirements.txt

# Make the CLI available in your PATH
ln -s $(pwd)/projects/grocery-cli/grocery.py ~/bin/grocery
chmod +x projects/grocery-cli/grocery.py
```

OpenClaw loads skills from `<workspace>/skills/` at session start. The `SKILL.md` tells you when and how to use each command. It will be included in your context automatically when the user mentions groceries, shopping, or cart syncing.

### Claude Code

```bash
# For this project only
mkdir -p .claude/skills
git clone https://github.com/sleechie/grocery-cli.git .claude/skills/grocery-list

# For all projects (personal skill)
git clone https://github.com/sleechie/grocery-cli.git ~/.claude/skills/grocery-list

# Install dependencies
pip install -r <path-to-grocery-list>/requirements.txt
```

Claude Code discovers skills from `.claude/skills/` directories automatically. Invoke with `/grocery-list` or let it load when relevant.

### Other Agent Frameworks

The skill follows the [AgentSkills](https://agentskills.io) open standard. Drop the `skills/SKILL.md` into whatever skill directory your framework uses, install the Python dependencies, and make sure the `grocery` command is in your PATH.

## Configure

### 1. Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with real values:

```env
# Google Tasks
# Run: gog tasks list --json
# Find your task list ID and the ID of the parent "GROCERY LIST" task
GROCERY_TASK_LIST_ID=your-task-list-id
GROCERY_PARENT_TASK_ID=your-parent-task-id

# Kroger API
# Register an app at https://developer.kroger.com
# Scopes needed: product.compact, cart.basic:write
KROGER_CLIENT_ID=your-client-id
KROGER_CLIENT_SECRET=your-client-secret
KROGER_REDIRECT_URI=http://localhost:8000/callback

# Store
# Find your store at https://www.kroger.com/stores/search
# Store ID format: divisionNumber + storeNumber (e.g., 70100123)
KROGER_STORE_ID=70100123
KROGER_DIVISION=701

# Paths
CATALOG_PATH=./data/catalog.json
TOKEN_DIR=.
```

### 2. Google Tasks

Your human needs the [`gog` CLI](https://github.com/steipete/gogcli) installed and authenticated with their Google account.

They need a parent task in Google Tasks called "GROCERY LIST" (or whatever they want). All grocery items are sub-tasks under this parent. Get the IDs:

```bash
gog tasks list "<task-list-id>" --json
```

Look for the task with the grocery list title and grab its `id` — that's your `GROCERY_PARENT_TASK_ID`.

### 3. Product Catalog

Start with the example:

```bash
cp data/catalog.example.json data/catalog.json
```

The catalog starts small and grows as you use it. Every time you resolve a new product via the Kroger API and the user confirms it, add it:

```bash
grocery catalog add --upc "<UPC>" --name "Product Name With Size"
```

Over time, the catalog becomes a personalized database of everything your human buys, with purchase frequency data that makes fuzzy matching increasingly accurate.

### 4. Kroger Auth

The auth flow is non-interactive so you can drive it entirely:

```bash
# Generate the OAuth URL
grocery auth url

# Send the URL to your human — they click it, authorize, get redirected to localhost
# The page won't load (no server there) — that's fine
# They copy the full URL from their browser and send it back to you

# Exchange for tokens
grocery auth exchange "http://localhost:8000/callback?code=THE_CODE"
```

Tokens are saved to `TOKEN_DIR/.kroger_token_user.json`. Access tokens expire every 30 minutes but refresh automatically. You should rarely need to re-auth.

### 5. Verify

Run through these to confirm everything works:

```bash
grocery list                    # Should show the Google Tasks list
grocery search "bananas"        # Should fuzzy match against catalog
grocery catalog -n 5            # Should show top 5 items
grocery cart sync --dry-run     # Should resolve items and show matches
```

If `cart sync --dry-run` resolves items and shows confidence scores, you're good to go.

## What's Next

Read `skills/SKILL.md` for:
- The two-phase workflow (list building vs cart sync)
- Cart sync playbook (dry run → handle ambiguity → save products → sync)
- Confidence tiers and when to confirm vs auto-resolve
- Product image URLs for visual confirmation
- Important API constraints

That's your operational reference. This file is just setup.
