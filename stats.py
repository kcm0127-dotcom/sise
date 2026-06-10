"""Sale inference + per-model price statistics.

Sale inference (snapshot diff):
  A cleaned listing present in snapshot D-1 but absent in snapshot D is
  treated as a sale proxy at its last observed price. Listings flagged
  is_set / head_only are tracked separately and excluded from headline stats.

Estimation chain (best available evidence first):
  1. basis="sold"        — model has >= MIN_SOLD_SAMPLE inferred sales:
                           estimate = median(sold prices)
  2. basis="ratio"       — model lacks sales but its CATEGORY has enough:
                           learn discount = median(category sold) / median(category asking)
                           estimate = model asking median x discount
  3. basis="asking_low"  — no sales anywhere yet (cold start):
                           estimate = midpoint of Q1..median of asking prices
                           (sales clear from the cheap end of the book, so the
                           lower half of asking is closer to clearing prices
                           than the raw median)
  Raw asking median is always reported alongside for transparency.

Usage:
    python stats.py            # uses all snapshots in snapshots/, writes stats.json
"""

from __future__ import annotations
import json
import statistics
from pathlib import Path

from pipeline import load_catalog, load_snapshot, clean, kept

BASE = Path(__file__).parent
MIN_SOLD_SAMPLE = 5


def infer_sales(prev: list[dict], curr: list[dict], sold_date: str) -> list[dict]:
    """Cleaned D-1 listings missing from D's raw pid set -> sale proxies."""
    curr_pids = {r["pid"] for r in curr}
    sales = []
    for r in prev:
        if r["pid"] not in curr_pids:
            sales.append({
                "pid": r["pid"], "model_id": r["model_id"], "name": r["name"],
                "price": r["price"], "sold_date": sold_date,
                "is_set": r.get("is_set", False), "head_only": r.get("head_only", False),
                "num_faved": r.get("num_faved", 0),
            })
    return sales


def price_stats(prices: list[int]) -> dict | None:
    if not prices:
        return None
    qs = statistics.quantiles(prices, n=4) if len(prices) >= 2 else [prices[0]] * 3
    return {
        "n": len(prices),
        "median": int(statistics.median(prices)),
        "q1": int(qs[0]),
        "q3": int(qs[2]),
        "min": min(prices),
        "max": max(prices),
    }


def build(snapshot_dir: Path | None = None) -> dict:
    catalog = load_catalog()
    snap_dir = snapshot_dir or BASE / "snapshots"
    days = sorted(snap_dir.glob("*.jsonl"))
    if not days:
        raise SystemExit("no snapshots found")

    cleaned_by_day = {p.stem: kept(clean(load_snapshot(p), catalog)) for p in days}

    all_sales: list[dict] = []
    day_names = [p.stem for p in days]
    for prev_day, curr_day in zip(day_names, day_names[1:]):
        # diff against RAW current pids: a listing dropped by cleaning rules
        # still exists on the platform and must not count as sold
        raw_curr = load_snapshot(snap_dir / f"{curr_day}.jsonl")
        all_sales += infer_sales(cleaned_by_day[prev_day], raw_curr, curr_day)

    latest_day = day_names[-1]
    active = cleaned_by_day[latest_day]

    def plain_prices(rows: list[dict], model_id: str) -> list[int]:
        return [r["price"] for r in rows
                if r["model_id"] == model_id
                and not r.get("is_set") and not r.get("head_only")]

    # learn per-category clearing discount: median(sold) / median(asking)
    cat_discount: dict[str, float] = {}
    for cat_key in {m["category_key"] for m in catalog["_models"].values()}:
        mids = [mid for mid, m in catalog["_models"].items() if m["category_key"] == cat_key]
        sold_c = [p for mid in mids for p in plain_prices(all_sales, mid)]
        ask_c = [p for mid in mids for p in plain_prices(active, mid)]
        if len(sold_c) >= MIN_SOLD_SAMPLE and len(ask_c) >= MIN_SOLD_SAMPLE:
            ratio = statistics.median(sold_c) / statistics.median(ask_c)
            cat_discount[cat_key] = round(min(ratio, 1.0), 3)

    result = {"as_of": latest_day, "category_discount": cat_discount, "models": {}}
    for model_id, model in catalog["_models"].items():
        sold_prices = plain_prices(all_sales, model_id)
        active_rows = [r for r in active if r["model_id"] == model_id]
        active_prices = plain_prices(active, model_id)
        ask_st = price_stats(active_prices)
        cat_key = model["category_key"]

        if len(sold_prices) >= MIN_SOLD_SAMPLE:
            basis, st = "sold", price_stats(sold_prices)
            estimate = st["median"]
        elif ask_st and cat_key in cat_discount:
            basis, st = "ratio", ask_st
            estimate = int(ask_st["median"] * cat_discount[cat_key])
        elif ask_st:
            basis, st = "asking_low", ask_st
            estimate = (st["q1"] + st["median"]) // 2
        else:
            basis, st, estimate = "none", None, None

        series = []
        for day in day_names:
            day_prices = plain_prices(cleaned_by_day[day], model_id)
            if day_prices:
                series.append({"date": day, "median": int(statistics.median(day_prices)),
                               "n": len(day_prices)})

        result["models"][model_id] = {
            "label": model["label"],
            "group": model.get("group", ""),
            "category": cat_key,
            "series": series,
            "basis": basis,
            "estimate": estimate,
            "asking_median": ask_st["median"] if ask_st else None,
            "stats": st,
            "active_count": len(active_rows),
            "sold": [s for s in all_sales if s["model_id"] == model_id],
            "active_sample": sorted(active_rows, key=lambda r: -r["update_time"])[:20],
        }
    return result


if __name__ == "__main__":
    result = build()
    out = BASE / "stats.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"as_of={result['as_of']} -> {out}")
    if result["category_discount"]:
        print("category discount:", result["category_discount"])
    for mid, m in result["models"].items():
        st = m["stats"]
        line = (f"{m['label']:<24} basis={m['basis']:<10} active={m['active_count']:>3} "
                f"sold={len(m['sold'])}")
        if m["estimate"]:
            line += f"  estimate={m['estimate']:,} (호가중앙값 {m['asking_median']:,}, n={st['n']})"
        print(line)
        for s in m["sold"]:
            print(f"    SOLD {s['sold_date']} {s['price']:>9,}  {s['name'][:40]}")
