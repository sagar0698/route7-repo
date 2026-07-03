#!/usr/bin/env python3
"""
Route 7 — daily price recorder.

Reads data/watchlist.json, fetches the current price for each card from the
Pokemon TCG API, and appends a timestamped snapshot to that card's history file
in data/history/. The committed JSON files ARE the time-series database — no
server or DB to run. GitHub Actions runs this once a day and commits the result.

Design notes:
- Pokemon TCG API needs no key (rate limits are lower without one, which is fine
  for a small watchlist). Set POKEMONTCG_API_KEY as a repo secret to raise limits.
- eBay is stubbed (see fetch_ebay_price). Fill it in once your eBay developer
  account is approved; nothing else needs to change.
- Idempotent per day: running twice in one day overwrites that day's entry rather
  than duplicating it, so a manual re-run won't corrupt the series.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ---- paths ----
ROOT = Path(__file__).resolve().parent.parent
WATCHLIST = ROOT / "data" / "watchlist.json"
HISTORY_DIR = ROOT / "data" / "history"
LATEST = ROOT / "data" / "latest.json"     # convenience: newest snapshot for all cards

# ---- config ----
API_BASE = "https://api.pokemontcg.io/v2/cards"
API_KEY = os.environ.get("POKEMONTCG_API_KEY", "").strip()
REQUEST_DELAY = 0.4          # be polite to the free API
TIMEOUT = 30


def http_get_json(url: str) -> dict:
    """GET a URL and parse JSON, with the API key header if present."""
    req = urllib.request.Request(url)
    if API_KEY:
        req.add_header("X-Api-Key", API_KEY)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_tcg_price(card: dict) -> dict | None:
    """
    Pull the real TCGplayer price tiers from a card object.
    Returns {variant, market, low, mid, high, directLow, updatedAt} or None.
    Mirrors the frontend's realPrice() logic so the numbers line up.
    """
    tp = card.get("tcgplayer") or {}
    prices = tp.get("prices") or {}
    if not prices:
        return None
    order = ["holofoil", "reverseHolofoil", "normal",
             "1stEditionHolofoil", "unlimitedHolofoil", "1stEditionNormal"]
    key = next((k for k in order if k in prices), None) or next(iter(prices), None)
    if not key:
        return None
    p = prices[key]
    label = {
        "holofoil": "Holofoil", "reverseHolofoil": "Reverse holo", "normal": "Normal",
        "1stEditionHolofoil": "1st ed. holo", "unlimitedHolofoil": "Unlimited holo",
        "1stEditionNormal": "1st ed.",
    }.get(key, key)
    return {
        "variant": label,
        "market": p.get("market"),
        "low": p.get("low"),
        "mid": p.get("mid"),
        "high": p.get("high"),
        "directLow": p.get("directLow"),
        "tcgUpdatedAt": tp.get("updatedAt"),
    }


def fetch_ebay_price(card: dict) -> dict | None:
    """
    STUB — fill in once your eBay developer account is approved.

    Plan: call eBay's Browse API (buy/browse/v1/item_summary/search) with the
    card name + set + number, filter to Buy-It-Now, sort by price, and return the
    lowest listing. eBay's free tier allows thousands of calls/day — far more than
    a small watchlist needs. Return shape suggestion:
        {"lowest": 123.45, "currency": "USD", "listingUrl": "...", "count": 17}
    For now we return None so the recorder runs today with zero approvals.
    """
    return None


def fetch_card(card_id: str) -> dict | None:
    """Fetch a single card by its Pokemon TCG API id."""
    url = f"{API_BASE}/{card_id}"
    try:
        data = http_get_json(url)
        return data.get("data")
    except urllib.error.HTTPError as e:
        print(f"  ! HTTP {e.code} for {card_id}", file=sys.stderr)
    except Exception as e:  # noqa: BLE001 - log and continue on any single-card failure
        print(f"  ! error for {card_id}: {e}", file=sys.stderr)
    return None


def load_history(card_id: str) -> list:
    f = HISTORY_DIR / f"{card_id}.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            print(f"  ! corrupt history for {card_id}, starting fresh", file=sys.stderr)
    return []


def save_history(card_id: str, entries: list) -> None:
    f = HISTORY_DIR / f"{card_id}.json"
    f.write_text(json.dumps(entries, indent=2))


def main() -> int:
    if not WATCHLIST.exists():
        print(f"No watchlist at {WATCHLIST}", file=sys.stderr)
        return 1

    watchlist = json.loads(WATCHLIST.read_text())
    cards = watchlist.get("cards", [])
    if not cards:
        print("Watchlist is empty — add card ids to data/watchlist.json", file=sys.stderr)
        return 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stamp = datetime.now(timezone.utc).isoformat()
    print(f"Recording prices for {len(cards)} cards on {today}")

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    latest_snapshot = {}

    for entry in cards:
        card_id = entry.get("id") if isinstance(entry, dict) else entry
        if not card_id:
            continue
        print(f"- {card_id}")
        card = fetch_card(card_id)
        time.sleep(REQUEST_DELAY)
        if not card:
            continue

        tcg = extract_tcg_price(card)
        ebay = fetch_ebay_price(card)

        snapshot = {
            "date": today,
            "recordedAt": stamp,
            "name": card.get("name"),
            "set": (card.get("set") or {}).get("name"),
            "number": card.get("number"),
            "image": (card.get("images") or {}).get("small"),
            "tcgplayer": tcg,
            "ebay": ebay,
        }

        history = load_history(card_id)
        # idempotent: replace today's entry if this is a re-run
        history = [h for h in history if h.get("date") != today]
        history.append(snapshot)
        history.sort(key=lambda h: h.get("date", ""))
        save_history(card_id, history)

        latest_snapshot[card_id] = snapshot

    LATEST.write_text(json.dumps(latest_snapshot, indent=2))
    print(f"Done. Wrote {len(latest_snapshot)} snapshots + updated latest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
