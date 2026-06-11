"""Daily snapshot collector for Bunjang.

Two modes:
  sweep (default) — walk entire categories via f_category_id, page by page.
                    Maximum coverage: every active listing in the category,
                    including models not yet in the dictionary. Model
                    assignment happens later in the pipeline.
  query           — one search query per catalog model (legacy, narrower).

Run once per day (cron):
    python collector.py            # sweep mode
    python collector.py query      # query mode

Writes snapshots/YYYY-MM-DD.jsonl.

NOTE: unofficial endpoint. Keep to 1 run/day, no aggressive retries; stop if
the platform objects. Review legal considerations before commercial use.
"""

from __future__ import annotations
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent
SNAP_DIR = BASE / "snapshots"
API = "https://api.bunjang.co.kr/api/1/find_v2.json"
PAGE_SIZE = 100
SWEEP_PAGE_CAP = 120         # default hard stop per category (120 x 100 = 12k listings)
# per-category page caps — large/active categories get more pages.
# tune here to trade off coverage vs. run time & snapshot size.
SWEEP_PAGE_CAP_BY_CAT = {
    "gpu": 150,       # ~14k active listings
    "console": 150,   # ~19k active listings
    "tablet": 80,
    "camera": 60,
    "golf": 40,
}
QUERY_PAGES_PER_MODEL = 3
DELAY_SEC = 1.2             # polite delay between requests (lowered for full sweep)
USER_AGENT = "Mozilla/5.0 (sise-mvp; contact: kcm0127@gmail.com)"


def fetch(params: dict) -> dict:
    qs = urllib.parse.urlencode({**params, "n": PAGE_SIZE, "order": "date",
                                 "stat_device": "w", "version": 4})
    req = urllib.request.Request(f"{API}?{qs}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def slim(item: dict, model_id: str, category_key: str) -> dict:
    return {
        "pid": item["pid"],
        "model_id": model_id,            # "" in sweep mode -> pipeline resolves
        "category_key": category_key,
        "name": item.get("name", ""),
        "price": int(item.get("price") or 0),
        "status": str(item.get("status", "")),
        "category_id": str(item.get("category_id", "")),
        "num_faved": int(item.get("num_faved") or 0),
        "update_time": int(item.get("update_time") or 0),
        "used": item.get("used"),
        "proshop": bool(item.get("proshop")),
        "url": f"https://m.bunjang.co.kr/products/{item['pid']}",
    }


def sweep(catalog: dict, out) -> int:
    count = 0
    for cat_key, cat in catalog["categories"].items():
        cap = SWEEP_PAGE_CAP_BY_CAT.get(cat_key, SWEEP_PAGE_CAP)
        for cid in cat.get("sweep_ids", []):
            for page in range(cap):
                try:
                    data = fetch({"q": "", "f_category_id": cid, "page": page,
                                  "req_ref": "category"})
                except Exception as e:
                    print(f"[warn] sweep {cat_key}/{cid} p{page}: {e} — stopping category")
                    break
                items = data.get("list") or []
                if not items:
                    break
                for item in items:
                    out.write(json.dumps(slim(item, "", cat_key), ensure_ascii=False) + "\n")
                    count += 1
                if page == 0:
                    total = data.get("num_found", 0)
                    print(f"  {cat_key}/{cid}: {total:,} listings "
                          f"(~{min(-(-total // PAGE_SIZE), cap)} pages)")
                time.sleep(DELAY_SEC)
    return count


def query_mode(catalog: dict, out) -> int:
    count, seen = 0, set()
    for cat_key, cat in catalog["categories"].items():
        for model in cat["models"]:
            for page in range(QUERY_PAGES_PER_MODEL):
                try:
                    data = fetch({"q": model["query"], "page": page})
                except Exception as e:
                    print(f"[warn] {model['id']} p{page}: {e} — skipping")
                    break
                items = data.get("list") or []
                if not items:
                    break
                for item in items:
                    key = f"{model['id']}:{item['pid']}"
                    if key not in seen:
                        seen.add(key)
                        out.write(json.dumps(slim(item, model["id"], cat_key),
                                             ensure_ascii=False) + "\n")
                        count += 1
                time.sleep(DELAY_SEC)
    return count


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "sweep"
    catalog = json.loads((BASE / "catalog.json").read_text(encoding="utf-8"))
    SNAP_DIR.mkdir(exist_ok=True)
    out_path = SNAP_DIR / f"{date.today().isoformat()}.jsonl"
    # write to a temp file first, then atomically replace — a run that is
    # interrupted midway never leaves a half-written / corrupt snapshot
    tmp_path = out_path.with_suffix(".jsonl.tmp")
    with tmp_path.open("w", encoding="utf-8") as out:
        count = sweep(catalog, out) if mode == "sweep" else query_mode(catalog, out)
    import os
    os.replace(tmp_path, out_path)
    print(f"snapshot written: {out_path} ({count:,} listings, mode={mode})")

    # retention: keep only the most recent KEEP_DAYS snapshots so the repo
    # doesn't grow without bound (stats only needs the last couple of days)
    KEEP_DAYS = 7
    snaps = sorted(SNAP_DIR.glob("20*.jsonl"))
    for old in snaps[:-KEEP_DAYS]:
        old.unlink()
        print(f"pruned old snapshot: {old.name}")


if __name__ == "__main__":
    main()
