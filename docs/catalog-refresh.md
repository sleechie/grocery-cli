# Catalog Refresh — Importing Purchase History from Kroger

This guide documents how to bulk-import your Kroger/City Market purchase history into the product catalog. This gives you a pre-populated catalog of every product you've ever bought, with purchase frequency data that makes fuzzy matching highly accurate from day one.

**This is optional.** You can skip this entirely and let your catalog grow organically — every time you confirm a product during cart sync, save it with `grocery catalog add`. The organic approach is simpler but starts from zero.

## Prerequisites

- A logged-in Kroger/City Market account in a browser (with purchase history visible)
- Browser automation capability — you need to execute JavaScript within the logged-in page context
  - [OpenClaw](https://github.com/openclaw/openclaw) with Chrome browser relay
  - Or: Playwright, Puppeteer, or any tool that can run `fetch()` in a logged-in browser session
- **Why browser-only:** Kroger uses Akamai bot protection. All `curl`/`requests`/server-side HTTP calls are blocked. The internal APIs only work when called from within the browser's page context, with the session cookies and headers that the browser middleware injects.

## Important Caveats

- These are **undocumented internal APIs**. They can change or break at any time.
- The endpoints are for Kroger's family of stores (City Market, King Soopers, Fred Meyer, Ralphs, etc.). The base domain changes by banner (e.g., `citymarket.com`, `kingsoopers.com`, `kroger.com`).
- UPCs with an `080` prefix are store-generated random-weight or in-store items (bakery self-serve, deli, etc.). These may map to generic product entries or may not resolve cleanly.
- This process was developed and tested in February 2026. If it stops working, the API endpoints likely changed.

## Step 1: Navigate to Purchase History

Open your store's purchase history page in a logged-in browser session:

```
https://www.citymarket.com/mypurchases
```

Replace `citymarket.com` with your banner's domain if different (`kroger.com`, `kingsoopers.com`, etc.).

## Step 2: Fetch All Orders

The purchase history search API returns orders in pages of 10. Run this in the browser's developer console (or via browser automation):

```javascript
// Fetch all order pages
const allOrders = [];
let pageNo = 1;
let hasMore = true;

while (hasMore) {
  const res = await fetch(`/atlas/v1/post-order/v1/purchase-history-search?pageNo=${pageNo}&pageSize=10`);
  const data = await res.json();
  
  if (data.orders && data.orders.length > 0) {
    allOrders.push(...data.orders);
    console.log(`Page ${pageNo}: ${data.orders.length} orders (total: ${allOrders.length})`);
    pageNo++;
  } else {
    hasMore = false;
  }
}

console.log(`Total orders: ${allOrders.length}`);
```

Each order object contains:
```json
{
  "divisionNumber": "620",
  "storeNumber": "00421",
  "transactionDate": "2026-02-09",
  "terminalNumber": "513",
  "transactionId": "801632",
  "totalAmount": 45.67
}
```

## Step 3: Fetch Order Details (Product Names + UPCs)

For each order, call the detail API to get the individual items:

```javascript
// Process orders in parallel batches to get product details
const batchSize = 5;
const allItems = {};

for (let i = 0; i < allOrders.length; i += batchSize) {
  const batch = allOrders.slice(i, i + batchSize);
  
  const results = await Promise.all(batch.map(order => {
    const body = [{
      divisionNumber: order.divisionNumber,
      storeNumber: order.storeNumber,
      transactionDate: order.transactionDate,
      terminalNumber: order.terminalNumber,
      transactionId: order.transactionId
    }];
    
    return fetch('/atlas/v1/purchase-history/v2/details', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-kroger-channel': 'WEB'
      },
      body: JSON.stringify(body)
    }).then(r => r.json());
  }));
  
  // Extract items from each order
  for (let j = 0; j < results.length; j++) {
    const order = batch[j];
    const details = results[j];
    
    if (details && details[0] && details[0].items) {
      for (const item of details[0].items) {
        const upc = item.upc || item.upcId;
        const name = item.description || item.name || null;
        
        if (!upc) continue;
        
        if (!allItems[upc]) {
          allItems[upc] = {
            upc: upc,
            name: name,
            purchaseCount: 0,
            lastPurchased: null
          };
        }
        
        allItems[upc].purchaseCount++;
        if (name && !allItems[upc].name) {
          allItems[upc].name = name;
        }
        
        const date = order.transactionDate;
        if (!allItems[upc].lastPurchased || date > allItems[upc].lastPurchased) {
          allItems[upc].lastPurchased = date;
        }
      }
    }
  }
  
  console.log(`Processed ${Math.min(i + batchSize, allOrders.length)}/${allOrders.length} orders`);
}

console.log(`Unique products: ${Object.keys(allItems).length}`);
```

## Step 4: Build the Catalog JSON

Convert the collected data into the catalog format:

```javascript
const items = Object.values(allItems)
  .sort((a, b) => b.purchaseCount - a.purchaseCount);

const catalog = {
  generatedAt: new Date().toISOString().split('T')[0],
  storeId: "70100123",  // Replace with your store ID
  storeName: "City Market - Your Store",  // Replace
  totalProducts: items.length,
  resolvedNames: items.filter(i => i.name).length,
  unresolvedUpcs: items.filter(i => !i.name).length,
  dateRange: {
    from: allOrders[allOrders.length - 1].transactionDate,
    to: allOrders[0].transactionDate
  },
  totalOrders: allOrders.length,
  items: items
};

// Copy to clipboard
copy(JSON.stringify(catalog, null, 2));
console.log('Catalog JSON copied to clipboard!');
```

Paste the clipboard contents into `data/catalog.json`.

## Step 5: Resolve Unresolved Names

Some items may have UPCs but no product name (the detail API didn't return a description). You can:

1. **Leave them** — they'll still match by UPC during cart sync
2. **Search manually** — use `grocery resolve --api` or look up the UPC on the Kroger website
3. **Update the catalog** — `grocery catalog add --upc "<UPC>" --name "Product Name"`

## Step 6: Verify

```bash
# Check the catalog loaded correctly
grocery catalog -n 10

# Search for a common item
grocery search "bananas"

# Full catalog stats
grocery catalog --all | tail -1
```

## Refreshing Later

To add new purchases to an existing catalog, repeat Steps 2-4 but only process orders newer than your catalog's `dateRange.to` date. Merge new items and update purchase counts for existing ones.

Alternatively, just let the catalog grow organically from this point — new products get added via `grocery catalog add` as they're confirmed during cart sync.

## Troubleshooting

**"Failed to fetch" or 403 errors:**
Your session may have expired. Refresh the purchase history page and try again. Make sure you're logged in.

**Empty order details:**
Some very old orders may not have detail data available. Skip them.

**UPCs starting with `080`:**
These are store-generated codes for random-weight or in-store items (bakery, deli, produce by weight). They may map to generic entries like "Bakery Fresh Goodness Donut" or "Colorado Bag Fee." They're valid but less useful for cart sync since these items are typically grabbed in-store rather than ordered for pickup.

**Different store than expected:**
If you've shopped at multiple locations, orders will have different `storeNumber` values. The catalog works across stores — UPCs are the same regardless of location.
