---
name: grocery-list
description: Manage the user's grocery list via Google Tasks. Use when asked to add, remove, check off, view, or clear grocery/shopping items, sync to Kroger cart, or search for products.
---

# Grocery List

The `grocery` CLI manages a grocery list (Google Tasks), product catalog (purchase history with fuzzy matching), and Kroger cart sync. You operate it on behalf of your user — they never run these commands directly.

## The Two Phases

### Phase 1: List Building (passive, throughout the week)

Your user says things like "add eggs and bread to my grocery list." Run `grocery list add "eggs" "bread"`. No product resolution needed — the list stores their exact words as a human-readable staging area. Items get sorted by grocery store aisle automatically.

The list is shared — the user's partner, roommate, etc. might also add items directly in Google Tasks. You'll see whatever's there when it's time to sync.

### Phase 2: Cart Sync (active, when ordering)

When the user says "sync my cart" or "time to order groceries," this is where the intelligence kicks in. Follow the Cart Sync Playbook below.

## Commands

### List Management

```bash
grocery list                              # Show current list (active items only)
grocery list add "bananas" "ham" "eggs"   # Add one or more items (aisle-sorted)
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
grocery catalog add --upc "<UPC>" --name "Product Name"  # Add/update catalog entry
```

### Product Resolution

```bash
grocery resolve "ham"           # Show top 5 catalog matches with scores
grocery resolve "ham" --api     # Also search Kroger product API
```

### Kroger Cart

```bash
grocery cart sync             # Push all active list items → Kroger cart
grocery cart sync --dry-run   # Preview what WOULD sync without pushing
grocery cart add "bananas"    # Add item directly to Kroger cart (skip list)
```

### Authentication

```bash
grocery auth                  # Show auth steps
grocery auth url              # Print OAuth authorization URL
grocery auth exchange <code>  # Exchange auth code or redirect URL for tokens
```

**Auth flow (non-interactive):**
1. Run `grocery auth url` → get the OAuth URL
2. Send URL to your user — they open it, authorize, get redirected to localhost
3. User pastes back the redirect URL (it will fail to load — that's expected)
4. Run `grocery auth exchange "<redirect_url>"` → tokens saved

Tokens auto-refresh. Re-auth only needed if the refresh token expires (rare).

## Cart Sync Playbook

When the user says "sync my cart" or "load my cart," follow this exact sequence:

### Step 1: Dry Run
```bash
grocery cart sync --dry-run
```
Review every item in the output. You're looking for three things:

**✓ Confident matches (catalog, 70%+)** — These are fine. "Ham" → Black Forest Ham, purchased 25 times. No need to confirm.

**⚠ API fallbacks** — The item wasn't in the catalog, so it hit Kroger's search API. The first result might be wrong. Always confirm these with the user before syncing.

**✗ Unresolved** — Nothing matched. Ask the user what they meant.

### Step 2: Handle Ambiguity

For any ambiguous, uncertain, or API-sourced item:

1. Run `grocery resolve "<item>" --api` to see all options with scores
2. Pull product images for visual confirmation:
   ```bash
   curl -sL "https://www.kroger.com/product/images/large/front/<UPC>" -o /tmp/product.jpg
   ```
   Send the image to your user. Visual confirmation is faster than describing packaging.
3. Ask the user which one they want
4. If they want price comparison, the Kroger API returns pricing — search with `grocery resolve` and compare

### Step 3: Save New Products

After the user confirms an API-sourced product, save it to the catalog:
```bash
grocery catalog add --upc "<UPC>" --name "Descriptive Name With Size"
```

**Naming convention:** Always include size and variant info so you can distinguish between options:
- ✓ "Takis Fuego Small Bag 3.25oz" (distinguishes from the 9.9oz)
- ✓ "Tide Pods Spring Meadow 76ct" (distinguishes scent and count)
- ✗ "Takis Fuego Hot Chili Pepper & Lime Tortilla Chips" (which size??)

### Step 4: Sync for Real
```bash
grocery cart sync
```

### Step 5: Remind About Pickup
- **$35+ = free pickup**, under $35 = $4.95 fee
- User schedules pickup time in the Kroger/City Market app (API doesn't support this)
- Cart is add-only — no way to view cart contents via API, user checks in the app

## Confidence Tiers

Fuzzy matching uses `thefuzz.token_set_ratio`:

| Score | What to do |
|-------|------------|
| **70+, clear winner** | Use it confidently — no confirmation needed |
| **70+, multiple close matches** | Show the user the top 2-3 and ask which one |
| **50–69** | Low confidence — show the match and ask to confirm |
| **Below 50** | No match — fall through to Kroger API or flag as unresolved |

Tiebreaker: when scores are equal, higher `purchaseCount` wins (prefer frequently bought items).

## Handling Common Scenarios

**User says a generic item ("cheese", "chips"):**
Don't silently pick one. Run `grocery resolve "cheese"` and show the top matches with purchase counts. The most-bought one is usually right, but ask.

**User describes an attribute ("the purple Tide Pods", "the small Takis bag"):**
Use `grocery resolve "<query>" --api` and pull product images to confirm visually.

**User wants the cheapest option:**
Search with `grocery resolve "<query>" --api` — the Kroger API returns pricing in the product data. Compare and recommend.

**User adds to list vs. adds to cart:**
"Add ham to my grocery list" → `grocery list add "ham"` (staging area, no resolution)
"Add ham to my cart" → `grocery cart add "ham"` (resolves and pushes immediately)

## Product Images

Kroger API returns images for every product — front, back, top, bottom, left, right.

```
https://www.kroger.com/product/images/{size}/{perspective}/{UPC}
```
- Sizes: `thumbnail`, `small`, `medium`, `large`, `xlarge`
- Perspectives: `front`, `back`, `left`, `right`, `top`, `bottom`

Use these whenever there's any ambiguity. Download with curl and send to the user in chat.

## Important Constraints

- **Cart API is add-only.** No GET to view, no DELETE to remove. User manages cart in the app.
- **Adding the same UPC twice increments quantity.** Only sync once per session to avoid duplicates.
- **Aisle sorting:** 12 categories — Produce → Bakery/Deli → Dairy/Eggs → Meat/Seafood → Frozen → Snacks → Condiments → Canned/Dry Goods → Baking/Candy → Beverages → Household → Personal Care
- **Google Tasks quirk:** Some tasks may have no `title` field — the CLI handles this gracefully.

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
