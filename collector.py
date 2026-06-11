"""Daily snapshot collector for Bunjang.

Modes:
  hybrid (default) — sweep + per-model query top-up, deduped by pid.
                     Sweep gives broad coverage of recent listings; the query
                     pass guarantees every catalog model is observed daily
                     (up to QUERY_PAGES_PER_MODEL x PAGE_SIZE newest per
                     model), which keeps sale inference reliable for models
                     whose listings fall outside the sweep window.
  sweep / query    — run only one of the two passes.
  chunk            — resumable: processes jobs for up to TIME_BUDGET seconds,
                     saves state, exits. Re-run until it prints DONE.
                     (for environments that cap process run time)

Run once per day (cron):
    python collector.py            # hybrid, single process
    python collector.py chunk      # repeat until DONE

NOTE: unofficial endpoint, polite use — the API rejects page >= 100 and
n > 200. Keep to 1 full run/day; review legal considerations before
commercial use.
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent
SNAP_DIR = BASE / "snapshots"
API = "https://api.bunjang.co.kr/api/1/find_v2.json"
PAGE_SIZE = 200              # API maximum (400 with n > 200)
MAX_PAGE = 99                # API hard limit: page >= 100 -> HTTP 400
SWEEP_PAGE_CAP = 40          # default hard stop per category (pages of 200)
# per-category page caps (pages of PAGE_SIZE=200 items)
SWEEP_PAGE_CAP_BY_CAT = {
    "gpu": 70,        # ~14k active
    "console": 60,
    "tablet": 26,
    "camera": 46,     # ~9k active — full coverage
    "golf": 40,       # huge category, mostly non-drivers — query pass covers models
    "phone": 75,
    "laptop": 60,
    "audio": 50,
    "watch": 30,
}
QUERY_PAGES_PER_MODEL = 2
DELAY_SEC = 0.4              # polite delay between requests
TIME_BUDGET = 33             # seconds per chunk-mode invocation
USER_AGENT = "Mozilla/5.0 (sise-mvp; contact: kcm0127@gmail.com)"

STATE_PATH = SNAP_DIR / ".collect_state.json"


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


def build_jobs(catalog: dict, mode: str) -> list[dict]:
    """Job list: one entry per (sweep category id) or (query model)."""
    jobs = []
    if mode in ("sweep", "hybrid", "chunk"):
        for cat_key, cat in catalog["categories"].items():
            cap = min(SWEEP_PAGE_CAP_BY_CAT.get(cat_key, SWEEP_PAGE_CAP), MAX_PAGE + 1)
            for cid in cat.get("sweep_ids", []):
                jobs.append({"kind": "sweep", "cat": cat_key, "cid": cid,
                             "page": 0, "cap": cap})
    if mode in ("query", "hybrid", "chunk"):
        for cat_key, cat in catalog["categories"].items():
            for model in cat["models"]:
                jobs.append({"kind": "query", "cat": cat_key, "mid": model["id"],
                             "q": model["query"], "page": 0,
                             "cap": min(QUERY_PAGES_PER_MODEL, MAX_PAGE + 1)})
    return jobs


def run_job_page(job: dict, out, seen: set) -> bool:
    """Fetch one page of a job. Returns True if the job has more pages."""
    page = job["page"]
    try:
        if job["kind"] == "sweep":
            data = fetch({"q": "", "f_category_id": job["cid"], "page": page,
                          "req_ref": "category"})
        else:
            data = fetch({"q": job["q"], "page": page})
    except Exception as e:
        print(f"[warn] {job['kind']} {job.get('cid') or job.get('mid')} p{page}: {e}"
              f" — stopping job", flush=True)
        return False
    items = data.get("list") or []
    if not items:
        return False
    model_id = job.get("mid", "") if job["kind"] == "query" else ""
    for item in items:
        if item["pid"] in seen:
            continue
        seen.add(item["pid"])
        out.write(json.dumps(slim(item, model_id, job["cat"]), ensure_ascii=False) + "\n")
    if page == 0 and job["kind"] == "sweep":
        total = data.get("num_found", 0)
        print(f"  {job['cat']}/{job['cid']}: {total:,} listings "
              f"(cap {job['cap']} pages x {PAGE_SIZE})", flush=True)
    job["page"] += 1
    return job["page"] < job["cap"]


def load_seen(tmp_path: Path) -> set:
    seen = set()
    if tmp_path.exists():
        with tmp_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        seen.add(json.loads(line)["pid"])
                    except Exception:
                        pass
    return seen


def finalize(tmp_path: Path, out_path: Path, count: int) -> None:
    os.replace(tmp_path, out_path)
    if STATE_PATH.exists():
        STATE_PATH.unlink()
    print(f"snapshot written: {out_path} ({count:,} listings)")
    # retention: keep only the most recent KEEP_DAYS snapshots
    KEEP_DAYS = 7
    snaps = sorted(SNAP_DIR.glob("20*.jsonl"))
    for old in snaps[:-KEEP_DAYS]:
        old.unlink()
        print(f"pruned old snapshot: {old.name}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "hybrid"
    catalog = json.loads((BASE / "catalog.json").read_text(encoding="utf-8"))
    SNAP_DIR.mkdir(exist_ok=True)
    today = date.today().isoformat()
    out_path = SNAP_DIR / f"{today}.jsonl"
    tmp_path = out_path.with_suffix(".jsonl.tmp")

    if mode == "chunk":
        # resumable: load or build job state, work for TIME_BUDGET, save, exit
        if STATE_PATH.exists():
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if state.get("date") != today:
                state = None
        else:
            state = None
        if state is None:
            state = {"date": today, "jobs": build_jobs(catalog, "chunk")}
            if tmp_path.exists():
                tmp_path.unlink()
        seen = load_seen(tmp_path)
        start = time.time()
        with tmp_path.open("a", encoding="utf-8") as out:
            while state["jobs"] and time.time() - start < TIME_BUDGET:
                job = state["jobs"][0]
                if not run_job_page(job, out, seen):
                    state["jobs"].pop(0)
                time.sleep(DELAY_SEC)
        if state["jobs"]:
            STATE_PATH.write_text(json.dumps(state), encoding="utf-8")
            print(f"CONTINUE jobs_left={len(state['jobs'])} collected={len(seen):,}")
        else:
            finalize(tmp_path, out_path, len(seen))
            print("DONE")
        return

    # single-process modes
    if tmp_path.exists():
        tmp_path.unlink()
    seen: set = set()
    jobs = build_jobs(catalog, mode)
    with tmp_path.open("w", encoding="utf-8") as out:
        for job in jobs:
            while run_job_page(job, out, seen):
                time.sleep(DELAY_SEC)
            time.sleep(DELAY_SEC)
    finalize(tmp_path, out_path, len(seen))


if __name__ == "__main__":
    main()
