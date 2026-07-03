# Route 7 — Pokémon card market tracker

A zero-cost Pokémon card price tracker. The site shows live TCGplayer prices and
links to every shop, and a daily job quietly records prices so it can chart how
cards move over time — all for **$0/month**, no server, no database.

## How it works (and why it's free)

There is no backend. A scheduled GitHub Action runs a small Python script once a
day, fetches the current price for each card on your watchlist, and commits the
results as JSON files right into this repo. GitHub Pages serves the site and
those JSON files together. The browser just reads static files — instant, and
free forever.

```
GitHub Actions cron (daily)
        │  fetches prices
        ▼
  Card price APIs  ──►  data/history/*.json  ──►  GitHub Pages  ──►  Browser
   (Pokémon TCG,          (committed to repo,       (static host)     (reads files)
    eBay later)            = your time series)
```

Git itself is the database: every day's commit adds one snapshot per card, so
your price history builds up from the day you start — and lives in your commit
log too.

## Setup (about 5 minutes)

1. **Create a GitHub repo** and push these files to it.
2. **Enable Pages**: repo Settings → Pages → Source: *Deploy from a branch* →
   `main` / root. Your site goes live at `https://<you>.github.io/<repo>/`.
3. **Enable the daily job**: it's already defined in
   `.github/workflows/record-prices.yml`. Under the repo's Actions tab, enable
   workflows if prompted. It runs daily at 09:15 UTC, and you can trigger it
   manually from the Actions tab ("Run workflow") to get your first data point
   immediately.
4. **Edit your watchlist**: open `data/watchlist.json` and add the cards you and
   your friends care about. Each needs a Pokémon TCG API card `id` (e.g.
   `swsh12-186`). Find ids by searching a card in the app, or at
   [api.pokemontcg.io](https://api.pokemontcg.io).

That's it. After the first run, `data/history/` fills with one file per card.
After a week you have a 7-day trend; after a year, a yearly one.

## What's real vs. what's a placeholder

**Real, live, free:**
- TCGplayer market/low/mid/high prices (Pokémon TCG API — no key required).
- Set release dates and card metadata.
- The daily price history, once the job has run a few times.
- All shop links (eBay, Cardmarket, PriceCharting, local, gorilla_tcg).

**Stubbed for later (needs a free approval):**
- **eBay live prices.** `scripts/record_prices.py → fetch_ebay_price()` is a stub
  that returns `None` today, so everything runs with zero approvals. When your
  [eBay developer account](https://developer.ebay.com) is approved, fill that
  function in (plan is in its docstring), add `EBAY_APP_ID` / `EBAY_CERT_ID` as
  repo secrets, and eBay prices start flowing into the same daily history — no
  other change needed.

**Not possible without paid data (deliberately not faked):**
- Backfilled history from before you started recording. History only accumulates
  forward. If you ever want years of past data at once, a paid aggregator
  (PriceCharting etc.) can provide it — but that's optional and costs money, so
  it's left out of the free build.

## Files

- `scripts/record_prices.py` — the daily recorder. Reads the watchlist, fetches
  prices, appends timestamped history. Idempotent (a same-day re-run updates
  today's entry rather than duplicating it).
- `.github/workflows/record-prices.yml` — the cron schedule + auto-commit.
- `data/watchlist.json` — the cards you track. Edit this.
- `data/history/*.json` — per-card price history (generated).
- `data/latest.json` — newest snapshot for every card (generated).
- `scripts/history-reader.js` — drop-in frontend helpers to read the history
  files and draw a real trend line in the site.
- `index.html` — the Route 7 site itself (add your latest build here).

## Optional: raise the API rate limit

The Pokémon TCG API works with no key at lower limits — fine for a small
watchlist. For a free key with higher limits, register at
[pokemontcg.io](https://pokemontcg.io), then add it as a repo secret named
`POKEMONTCG_API_KEY`. The workflow already passes it through.

## Cost summary

| Piece | Cost |
|---|---|
| GitHub Pages hosting | Free |
| GitHub Actions (daily job) | Free (public repo: unlimited; private: 2,000 min/mo, you use ~15) |
| Pokémon TCG API | Free |
| eBay API (when added) | Free tier |
| **Total** | **$0/month** |

Not financial advice — the buy signals and heuristics are illustrative.
