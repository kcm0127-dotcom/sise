"""Generate catalog.json — the full model dictionary.

Models are defined as compact data rows; this script expands them into
match rules (include regex / exclude keywords / price sanity range).
Edit the lists below and re-run:

    python catalog_gen.py

Price ranges are generous outlier fences (만원 단위 입력), not market values.
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).parent
M = 10_000  # 만원

# ---------------------------------------------------------------- GPU
# (slug, label, query, include regex, price range 만원)
# Variant disambiguation: negative lookaheads keep "4070" from matching
# "4070 Ti / SUPER" etc. Suffix patterns never match across an intervening
# suffix ("4070 super" does not match "4070 ti super").
GPU_EXCLUDE = ["노트북", "laptop", "본체", "컴퓨터", "데스크탑", "완본체", "조립", "채굴기"]
GPUS = [
    # NVIDIA 50
    ("rtx-5090", "RTX 5090", "RTX 5090", r"5090", (250, 700)),
    ("rtx-5080", "RTX 5080", "RTX 5080", r"5080", (100, 300)),
    ("rtx-5070-ti", "RTX 5070 Ti", "RTX 5070 Ti", r"5070\s*ti", (70, 200)),
    ("rtx-5070", "RTX 5070", "RTX 5070", r"5070(?!\s*ti)", (45, 140)),
    ("rtx-5060-ti", "RTX 5060 Ti", "RTX 5060 Ti", r"5060\s*ti", (35, 100)),
    ("rtx-5060", "RTX 5060", "RTX 5060", r"5060(?!\s*ti)", (25, 80)),
    # NVIDIA 40
    ("rtx-4090", "RTX 4090", "RTX 4090", r"4090", (120, 400)),
    ("rtx-4080-super", "RTX 4080 SUPER", "RTX 4080 SUPER", r"4080\s*(super|슈퍼)", (65, 200)),
    ("rtx-4080", "RTX 4080", "RTX 4080", r"4080(?!\s*(super|슈퍼))", (55, 180)),
    ("rtx-4070-ti-super", "RTX 4070 Ti SUPER", "RTX 4070 Ti SUPER", r"4070\s*ti\s*(super|슈퍼)", (50, 150)),
    ("rtx-4070-ti", "RTX 4070 Ti", "RTX 4070 Ti", r"4070\s*ti(?!\s*(super|슈퍼))", (40, 130)),
    ("rtx-4070-super", "RTX 4070 SUPER", "RTX 4070 SUPER", r"4070\s*(super|슈퍼)", (40, 130)),
    ("rtx-4070", "RTX 4070", "RTX 4070", r"4070(?!\s*(ti|super|슈퍼))", (30, 120)),
    ("rtx-4060-ti", "RTX 4060 Ti", "RTX 4060 Ti", r"4060\s*ti", (28, 75)),
    ("rtx-4060", "RTX 4060", "RTX 4060", r"4060(?!\s*ti)", (22, 60)),
    # NVIDIA 30
    ("rtx-3090-ti", "RTX 3090 Ti", "RTX 3090 Ti", r"3090\s*ti", (55, 160)),
    ("rtx-3090", "RTX 3090", "RTX 3090", r"3090(?!\s*ti)", (45, 130)),
    ("rtx-3080-ti", "RTX 3080 Ti", "RTX 3080 Ti", r"3080\s*ti", (32, 95)),
    ("rtx-3080", "RTX 3080", "RTX 3080", r"3080(?!\s*ti)", (25, 80)),
    ("rtx-3070-ti", "RTX 3070 Ti", "RTX 3070 Ti", r"3070\s*ti", (22, 65)),
    ("rtx-3070", "RTX 3070", "RTX 3070", r"3070(?!\s*ti)", (18, 60)),
    ("rtx-3060-ti", "RTX 3060 Ti", "RTX 3060 Ti", r"3060\s*ti", (15, 55)),
    ("rtx-3060", "RTX 3060", "RTX 3060", r"3060(?!\s*ti)", (12, 50)),
    ("rtx-3050", "RTX 3050", "RTX 3050", r"3050", (10, 35)),
    # NVIDIA 20 / 16
    ("rtx-2080-ti", "RTX 2080 Ti", "RTX 2080 Ti", r"2080\s*ti", (20, 60)),
    ("rtx-2080-super", "RTX 2080 SUPER", "RTX 2080 SUPER", r"2080\s*(super|슈퍼)", (15, 45)),
    ("rtx-2070-super", "RTX 2070 SUPER", "RTX 2070 SUPER", r"2070\s*(super|슈퍼)", (12, 40)),
    ("rtx-2060-super", "RTX 2060 SUPER", "RTX 2060 SUPER", r"2060\s*(super|슈퍼)", (10, 35)),
    ("gtx-1660-super", "GTX 1660 SUPER", "GTX 1660 SUPER", r"1660\s*(super|슈퍼)", (6, 25)),
    ("gtx-1660-ti", "GTX 1660 Ti", "GTX 1660 Ti", r"1660\s*ti", (6, 25)),
    # AMD
    ("rx-9070-xt", "RX 9070 XT", "RX 9070 XT", r"9070\s*xt", (60, 160)),
    ("rx-9070", "RX 9070", "RX 9070", r"9070(?!\s*xt)", (50, 130)),
    ("rx-7900-xtx", "RX 7900 XTX", "RX 7900 XTX", r"7900\s*xtx", (70, 200)),
    ("rx-7900-xt", "RX 7900 XT", "RX 7900 XT", r"7900\s*xt(?!x)", (55, 160)),
    ("rx-7800-xt", "RX 7800 XT", "RX 7800 XT", r"7800\s*xt", (35, 100)),
    ("rx-7700-xt", "RX 7700 XT", "RX 7700 XT", r"7700\s*xt", (28, 80)),
    ("rx-7600", "RX 7600", "RX 7600", r"7600(?!\s*xt)", (18, 55)),
    ("rx-6700-xt", "RX 6700 XT", "RX 6700 XT", r"6700\s*xt", (18, 55)),
    ("rx-6600", "RX 6600", "RX 6600", r"6600(?!\s*xt)", (10, 40)),
]

# ---------------------------------------------------------------- Camera
CAM_EXCLUDE = ["배터리", "충전기", "케이지", "스트랩", "필터", "가방", "파우치",
               "핫슈", "액정", "보호", "그립만", "케이스", "마운트", "어댑터"]
CAM_SET = ["풀셋", "세트", "렌즈", "포함", "\\+"]
CAMS = [
    # Sony
    ("sony-a7m5", "소니 A7M5", "소니 A7M5", r"a7\s*m5|a7\s*v\b", (250, 500)),
    ("sony-a7m4", "소니 A7M4", "소니 A7M4", r"a7\s*m4|a7\s*iv\b", (120, 300)),
    ("sony-a7m3", "소니 A7M3", "소니 A7M3", r"a7\s*m3|a7\s*iii\b", (80, 190)),
    ("sony-a7c2", "소니 A7C2", "소니 A7C2", r"a7\s*c\s*(2|ii)", (160, 300)),
    ("sony-a7c", "소니 A7C", "소니 A7C", r"a7\s*c(?!\s*(2|ii|r))", (90, 190)),
    ("sony-a7r5", "소니 A7R5", "소니 A7R5", r"a7\s*r5|a7\s*r\s*v\b", (250, 480)),
    ("sony-a7r4", "소니 A7R4", "소니 A7R4", r"a7\s*r4|a7\s*r\s*iv\b", (150, 300)),
    ("sony-a6700", "소니 A6700", "소니 A6700", r"a6700", (110, 220)),
    ("sony-a6400", "소니 A6400", "소니 A6400", r"a6400", (50, 120)),
    ("sony-a6000", "소니 A6000", "소니 A6000", r"a6000", (15, 60)),
    ("sony-zv-e10", "소니 ZV-E10", "소니 ZV-E10", r"zv\s*-?\s*e10(?!\s*(2|ii|m2))", (40, 100)),
    ("sony-zv-e10m2", "소니 ZV-E10 II", "소니 ZV-E10 II", r"zv\s*-?\s*e10\s*(2|ii|m2)", (80, 160)),
    # Canon
    ("canon-r5m2", "캐논 R5 Mark II", "캐논 R5 마크2", r"r5\s*(mark\s*)?(2|ii)\b|r5\s*마크\s*2", (350, 650)),
    ("canon-r5", "캐논 R5", "캐논 R5", r"eos\s*r5(?!\s*(c|mark|2|ii|마크))|캐논\s*r5(?!\s*(c|mark|2|ii|마크))", (180, 380)),
    ("canon-r6m2", "캐논 R6 Mark II", "캐논 R6 마크2", r"r6\s*(mark\s*)?(2|ii)\b|r6\s*마크\s*2", (200, 380)),
    ("canon-r6", "캐논 R6", "캐논 R6", r"eos\s*r6(?!\s*(mark|2|ii|마크))|캐논\s*r6(?!\s*(mark|2|ii|마크))", (130, 280)),
    ("canon-r8", "캐논 R8", "캐논 R8", r"eos\s*r8|캐논\s*r8", (110, 240)),
    ("canon-r10", "캐논 R10", "캐논 R10", r"eos\s*r10|캐논\s*r10", (60, 140)),
    ("canon-r50", "캐논 R50", "캐논 R50", r"eos\s*r50|캐논\s*r50", (50, 120)),
    ("canon-rp", "캐논 RP", "캐논 RP", r"eos\s*rp|캐논\s*rp", (55, 140)),
    ("canon-200d2", "캐논 200D II", "캐논 200D", r"200d", (30, 90)),
    ("canon-90d", "캐논 90D", "캐논 90D", r"90d", (70, 170)),
    # Nikon
    ("nikon-z8", "니콘 Z8", "니콘 Z8", r"\bz8\b", (280, 520)),
    ("nikon-z6iii", "니콘 Z6 III", "니콘 Z6 III", r"z6\s*(3|iii)\b", (220, 400)),
    ("nikon-z6ii", "니콘 Z6 II", "니콘 Z6 II", r"z6\s*(2|ii)\b", (100, 220)),
    ("nikon-z6", "니콘 Z6", "니콘 Z6", r"\bz6\b(?!\s*(2|3|ii|iii))", (60, 150)),
    ("nikon-z5", "니콘 Z5", "니콘 Z5", r"\bz5\b", (60, 140)),
    ("nikon-zf", "니콘 Zf", "니콘 Zf", r"\bzf\b(?!c)", (180, 360)),
    ("nikon-zfc", "니콘 Zfc", "니콘 Zfc", r"zfc|z\s*fc\b", (60, 150)),
    ("nikon-d850", "니콘 D850", "니콘 D850", r"d850", (120, 270)),
    # Fuji / Ricoh
    ("fuji-xt5", "후지 X-T5", "후지 X-T5", r"x\s*-?\s*t5", (140, 300)),
    ("fuji-xt4", "후지 X-T4", "후지 X-T4", r"x\s*-?\s*t4", (90, 200)),
    ("fuji-x100vi", "후지 X100VI", "후지 X100VI", r"x100\s*vi\b|x100\s*6", (180, 380)),
    ("fuji-x100v", "후지 X100V", "후지 X100V", r"x100\s*v\b(?!i)", (120, 280)),
    ("fuji-xs20", "후지 X-S20", "후지 X-S20", r"x\s*-?\s*s20", (110, 220)),
    ("ricoh-gr3x", "리코 GR3x", "리코 GR3x", r"gr\s*3\s*x|gr\s*iii\s*x", (80, 180)),
    ("ricoh-gr3", "리코 GR3", "리코 GR3", r"gr\s*3(?!\s*x)|gr\s*iii(?!\s*x)", (70, 170)),
]

# ---------------------------------------------------------------- Golf driver
GOLF_EXCLUDE = ["우드", "아이언", "유틸", "웨지", "퍼터", "풀세트", "풀 세트", "캐디백"]
GOLF_HEAD = ["헤드만", "드라이버 헤드", "헤드\\s*\\("]
GOLF_VARIANTS = {"loft": ["8도", "9도", "9\\.0", "10\\.5", "10도", "12도"],
                 "flex": ["\\bR\\b", "\\bS\\b", "\\bSR\\b", "\\bX\\b", "5X", "6X", "여성", "여자", "레이디"]}
DRIVERS = [
    ("tm-qi35-driver", "테일러메이드 Qi35 드라이버", "Qi35 드라이버", r"qi\s*35", (50, 120)),
    ("tm-qi10-driver", "테일러메이드 Qi10 드라이버", "Qi10 드라이버", r"qi\s*10", (30, 85)),
    ("stealth2-driver", "테일러메이드 스텔스2 드라이버", "스텔스2 드라이버", r"스텔스\s*2", (10, 70)),
    ("tm-stealth-driver", "테일러메이드 스텔스 드라이버", "스텔스 드라이버", r"스텔스(?!\s*2)", (10, 50)),
    ("tm-sim2-driver", "테일러메이드 SIM2 드라이버", "SIM2 드라이버", r"sim\s*2|심2", (10, 45)),
    ("cw-ai-smoke-driver", "캘러웨이 Ai 스모크 드라이버", "AI 스모크 드라이버", r"ai\s*스모크|ai\s*smoke", (30, 95)),
    ("cw-paradym-driver", "캘러웨이 패러다임 드라이버", "패러다임 드라이버", r"패러다임|paradym", (22, 75)),
    ("cw-rogue-st-driver", "캘러웨이 로그 ST 드라이버", "로그 ST 드라이버", r"로그\s*st|rogue\s*st", (13, 55)),
    ("tt-gt3-driver", "타이틀리스트 GT3 드라이버", "타이틀리스트 GT3", r"\bgt\s*3\b", (50, 125)),
    ("tt-gt2-driver", "타이틀리스트 GT2 드라이버", "타이틀리스트 GT2", r"\bgt\s*2\b", (48, 115)),
    ("tt-tsr3-driver", "타이틀리스트 TSR3 드라이버", "TSR3 드라이버", r"tsr\s*3", (28, 90)),
    ("tt-tsr2-driver", "타이틀리스트 TSR2 드라이버", "TSR2 드라이버", r"tsr\s*2", (26, 85)),
    ("tt-tsi3-driver", "타이틀리스트 TSi3 드라이버", "TSi3 드라이버", r"tsi\s*3", (14, 60)),
    ("tt-tsi2-driver", "타이틀리스트 TSi2 드라이버", "TSi2 드라이버", r"tsi\s*2", (13, 55)),
    ("ping-g440-driver", "핑 G440 드라이버", "G440 드라이버", r"g440", (50, 115)),
    ("ping-g430-driver", "핑 G430 드라이버", "G430 드라이버", r"g430", (28, 85)),
    ("ping-g425-driver", "핑 G425 드라이버", "G425 드라이버", r"g425", (17, 60)),
    ("xxio-13-driver", "젝시오 13 드라이버", "젝시오 13 드라이버", r"젝시오\s*13|xxio\s*13", (45, 125)),
    ("xxio-12-driver", "젝시오 12 드라이버", "젝시오 12 드라이버", r"젝시오\s*12|xxio\s*12", (28, 95)),
]


def _gpu_group(slug: str) -> str:
    if slug.startswith("rx-"):
        return "라데온 RX"
    if slug.startswith("rtx-50"):
        return "RTX 50 시리즈"
    if slug.startswith("rtx-40"):
        return "RTX 40 시리즈"
    if slug.startswith("rtx-30"):
        return "RTX 30 시리즈"
    return "RTX 20 · GTX 16"


def _brand_group(label: str) -> str:
    return label.split()[0]  # 소니/캐논/니콘/후지/리코, 테일러메이드/캘러웨이/...


def build() -> dict:
    def expand(rows, extra, group_fn):
        models = []
        for pat in [p for v in extra.values() if isinstance(v, list) for p in v if isinstance(p, str)]:
            re.compile(pat)  # fail fast on bad regex in shared lists
        for slug, label, query, inc, (lo, hi) in rows:
            re.compile(inc)  # fail fast on bad regex
            m = {"id": slug, "label": label, "query": query,
                 "group": group_fn(slug, label),
                 "include": [inc], "price_range": [lo * M, hi * M], **extra}
            models.append(m)
        return models

    return {
        "categories": {
            "gpu": {
                "label": "그래픽카드",
                "bunjang_category_prefix": "600200005",
                "sweep_ids": ["600200005"],
                "models": expand(GPUS, {"exclude": GPU_EXCLUDE},
                                 lambda s, l: _gpu_group(s)),
            },
            "camera": {
                "label": "카메라",
                "bunjang_category_prefix": "600300",
                "sweep_ids": ["600300001"],
                "models": expand(CAMS, {"exclude": CAM_EXCLUDE, "set_keywords": CAM_SET},
                                 lambda s, l: _brand_group(l)),
            },
            "golf": {
                "label": "골프채",
                "bunjang_category_prefix": "700600",
                "sweep_ids": ["700600300"],
                "models": expand(DRIVERS, {"exclude": GOLF_EXCLUDE,
                                           "head_only_keywords": GOLF_HEAD,
                                           "variant_fields": GOLF_VARIANTS},
                                 lambda s, l: _brand_group(l)),
            },
        },
        "dummy_prices": [0, 1, 1111, 11111, 111111, 999, 9999, 99999, 1234, 12345],
    }


if __name__ == "__main__":
    catalog = build()
    n = sum(len(c["models"]) for c in catalog["categories"].values())
    (BASE / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    per = {k: len(c["models"]) for k, c in catalog["categories"].items()}
    print(f"catalog.json written — {n} models {per}")
