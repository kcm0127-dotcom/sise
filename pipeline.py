"""Cleaning pipeline: raw snapshot records -> trusted listings.

Each record passes through, in order:
  1. dummy price filter
  2. category prefix filter (drops laptops / full PCs / wrong boards)
  3. exclude-keyword filter
  4. include-pattern match (must positively match the model)
  5. price range sanity check
  6. flagging: is_set (bundles), head_only (golf)

Usage:
    from pipeline import load_catalog, load_snapshot, clean
    listings = clean(load_snapshot("snapshots/2026-06-11.jsonl"), load_catalog())
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).parent


def load_catalog(path: Path | None = None) -> dict:
    catalog = json.loads((path or BASE / "catalog.json").read_text(encoding="utf-8"))
    models = {}
    for cat_key, cat in catalog["categories"].items():
        for m in cat["models"]:
            m["category_key"] = cat_key
            m["category_prefix"] = cat["bunjang_category_prefix"]
            models[m["id"]] = m
    catalog["_models"] = models
    return catalog


def load_snapshot(path: str | Path) -> list[dict]:
    lines = Path(path).read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(l) for l in lines if l.strip()]


def _any_match(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _check(r: dict, model: dict, dummy: set) -> str | None:
    """Return drop reason against one model's rules, or None if it passes."""
    name, price = r.get("name", ""), r.get("price", 0)
    if price in dummy:
        return "dummy_price"
    if not str(r.get("category_id", "")).startswith(model["category_prefix"]):
        return "wrong_category"
    if _any_match(model.get("exclude", []), name):
        return "excluded_keyword"
    if not _any_match(model.get("include", []), name):
        return "no_model_match"
    if not (model["price_range"][0] <= price <= model["price_range"][1]):
        return "price_out_of_range"
    return None


def clean(records: list[dict], catalog: dict) -> list[dict]:
    dummy = set(catalog["dummy_prices"])
    by_cat: dict[str, list[dict]] = {}
    for m in catalog["_models"].values():
        by_cat.setdefault(m["category_key"], []).append(m)

    out = []
    for r in records:
        # sweep-mode records carry no model tag — resolve against the
        # whole category's model dictionary
        if not r.get("model_id"):
            model, reason = None, "no_model_match"
            for cand in by_cat.get(r.get("category_key", ""), []):
                if _check(r, cand, dummy) is None:
                    model, reason = cand, None
                    r["model_id"] = cand["id"]
                    break
            if model is None:
                r["drop_reason"] = reason
                out.append(r)
                continue
        else:
            model = catalog["_models"].get(r["model_id"])
            if model is None:
                continue
            reason = _check(r, model, dummy)

        # cross-model rescue: a "RTX 4070" search also returns Ti/SUPER
        # listings — reassign them to the sibling model they belong to
        # instead of dropping
        if reason == "no_model_match":
            for sib_id, sib in catalog["_models"].items():
                if sib_id != r["model_id"] and sib["category_key"] == model["category_key"] \
                        and _check(r, sib, dummy) is None:
                    r["model_id"], model, reason = sib_id, sib, None
                    r["reassigned"] = True
                    break

        r["drop_reason"] = reason
        if reason is None:
            name = r.get("name", "")
            r["is_set"] = _any_match(model.get("set_keywords", []), name)
            r["head_only"] = _any_match(model.get("head_only_keywords", []), name)
        out.append(r)
    return out


def kept(listings: list[dict]) -> list[dict]:
    return [r for r in listings if r["drop_reason"] is None]


if __name__ == "__main__":
    import sys
    catalog = load_catalog()
    path = sys.argv[1] if len(sys.argv) > 1 else BASE / "snapshots" / "2026-06-11.jsonl"
    listings = clean(load_snapshot(path), catalog)
    ok = kept(listings)
    print(f"total={len(listings)} kept={len(ok)}")
    from collections import Counter
    print("drop reasons:", dict(Counter(r["drop_reason"] for r in listings if r["drop_reason"])))
    for r in ok:
        flags = "".join([" [세트]" if r.get("is_set") else "", " [헤드만]" if r.get("head_only") else ""])
        print(f"  {r['model_id']:<18} {r['price']:>9,}  {r['name'][:42]}{flags}")
