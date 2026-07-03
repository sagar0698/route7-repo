/*
 * Route 7 — price history reader (frontend drop-in)
 * ---------------------------------------------------
 * Once the daily GitHub Action has committed a few days of data, these helpers
 * let the site read REAL history from the static JSON files and draw a trend.
 *
 * No backend, no fetch to any API — just reads the committed files served by
 * GitHub Pages from the same repo. Because the data is static, this is instant
 * and free.
 *
 * How to wire it in:
 *   1. Deploy this repo to GitHub Pages (site + data/ folder together).
 *   2. Set HISTORY_BASE below to your data path (default works if index.html
 *      sits at repo root and data/ is alongside it).
 *   3. Call loadHistory("swsh12-186") to get the array of snapshots, then feed
 *      it to sparklinePath() or your chart of choice.
 *
 * The card ids come from the same Pokemon TCG API the live search already uses,
 * so a card open in the modal already knows its id.
 */

const HISTORY_BASE = "./data/history";   // adjust if your data lives elsewhere
const LATEST_URL   = "./data/latest.json";

// Fetch one card's full price history (array of dated snapshots), or [] if none yet.
async function loadHistory(cardId) {
  try {
    const res = await fetch(`${HISTORY_BASE}/${cardId}.json`, { cache: "no-cache" });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

// Fetch the newest snapshot for every watched card at once (for a dashboard grid).
async function loadLatest() {
  try {
    const res = await fetch(LATEST_URL, { cache: "no-cache" });
    if (!res.ok) return {};
    return await res.json();
  } catch {
    return {};
  }
}

// Reduce a history array to {date, market} points using the TCGplayer market price.
function toSeries(history, field = "market") {
  return history
    .filter(h => h.tcgplayer && h.tcgplayer[field] != null)
    .map(h => ({ date: h.date, value: h.tcgplayer[field] }));
}

// Compute % change between the first and last points in a series.
function pctChange(series) {
  if (series.length < 2) return null;
  const first = series[0].value, last = series[series.length - 1].value;
  if (!first) return null;
  return ((last - first) / first) * 100;
}

// Build an SVG path string for a simple sparkline. Returns {path, area, min, max}.
// Usage: set an <svg viewBox="0 0 W H"> and drop <path d="{path}"> inside.
function sparklinePath(series, w = 600, h = 120, pad = 6) {
  if (series.length < 2) return null;
  const vals = series.map(p => p.value);
  const min = Math.min(...vals), max = Math.max(...vals), rng = (max - min) || 1;
  const X = i => pad + (i / (series.length - 1)) * (w - 2 * pad);
  const Y = v => h - pad - ((v - min) / rng) * (h - 2 * pad);
  let d = `M${X(0)},${Y(vals[0])}`;
  vals.forEach((v, i) => { if (i) d += ` L${X(i).toFixed(1)},${Y(v).toFixed(1)}`; });
  const area = `${d} L${X(vals.length - 1)},${h} L${X(0)},${h} Z`;
  return { path: d, area, min, max, rising: vals[vals.length - 1] >= vals[0] };
}

/* Example: render a card's trend into an element with id "trend"
 *
 *   const hist = await loadHistory("swsh12-186");
 *   const series = toSeries(hist);
 *   const change = pctChange(series);          // e.g. -4.2  (down 4.2%)
 *   const spark = sparklinePath(series);
 *   if (spark) {
 *     document.getElementById("trend").innerHTML =
 *       `<svg viewBox="0 0 600 120" style="width:100%;height:120px">
 *          <path d="${spark.area}" fill="rgba(74,222,128,.15)"/>
 *          <path d="${spark.path}" fill="none" stroke="${spark.rising ? '#4ade80' : '#fb7185'}" stroke-width="2"/>
 *        </svg>
 *        <div>${change == null ? 'building history…' : (change >= 0 ? '▲ ' : '▼ ') + Math.abs(change).toFixed(1) + '% since tracking began'}</div>`;
 *   }
 */

// Exposed for use by the main site (attach to window so a non-module script can call them)
window.Route7History = { loadHistory, loadLatest, toSeries, pctChange, sparklinePath };
