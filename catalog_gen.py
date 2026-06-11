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
    # NVIDIA 20 / 16 / 10
    ("rtx-2080-ti", "RTX 2080 Ti", "RTX 2080 Ti", r"2080\s*ti", (20, 60)),
    ("rtx-2080-super", "RTX 2080 SUPER", "RTX 2080 SUPER", r"2080\s*(super|슈퍼)", (15, 45)),
    ("rtx-2080", "RTX 2080", "RTX 2080", r"2080(?!\s*(ti|super|슈퍼))", (10, 38)),
    ("rtx-2070-super", "RTX 2070 SUPER", "RTX 2070 SUPER", r"2070\s*(super|슈퍼)", (12, 40)),
    ("rtx-2070", "RTX 2070", "RTX 2070", r"2070(?!\s*(super|슈퍼))", (9, 33)),
    ("rtx-2060-super", "RTX 2060 SUPER", "RTX 2060 SUPER", r"2060\s*(super|슈퍼)", (10, 35)),
    ("rtx-2060", "RTX 2060", "RTX 2060", r"2060(?!\s*(super|슈퍼))", (7, 28)),
    ("gtx-1660-super", "GTX 1660 SUPER", "GTX 1660 SUPER", r"1660\s*(super|슈퍼)", (6, 25)),
    ("gtx-1660-ti", "GTX 1660 Ti", "GTX 1660 Ti", r"1660\s*ti", (6, 25)),
    ("gtx-1660", "GTX 1660", "GTX 1660", r"1660(?!\s*(ti|super|슈퍼))", (5, 20)),
    ("gtx-1650", "GTX 1650", "GTX 1650", r"1650(?!\s*(ti|super|슈퍼))", (4, 18)),
    ("gtx-1080-ti", "GTX 1080 Ti", "GTX 1080 Ti", r"1080\s*ti", (8, 30)),
    ("gtx-1080", "GTX 1080", "GTX 1080", r"1080(?!\s*ti)", (6, 24)),
    ("gtx-1070", "GTX 1070", "GTX 1070", r"1070(?!\s*ti)", (5, 20)),
    # AMD
    ("rx-9070-xt", "RX 9070 XT", "RX 9070 XT", r"9070\s*xt", (60, 160)),
    ("rx-9070", "RX 9070", "RX 9070", r"9070(?!\s*xt)", (50, 130)),
    ("rx-7900-xtx", "RX 7900 XTX", "RX 7900 XTX", r"7900\s*xtx", (70, 200)),
    ("rx-7900-xt", "RX 7900 XT", "RX 7900 XT", r"7900\s*xt(?!x)", (55, 160)),
    ("rx-7800-xt", "RX 7800 XT", "RX 7800 XT", r"7800\s*xt", (35, 100)),
    ("rx-7700-xt", "RX 7700 XT", "RX 7700 XT", r"7700\s*xt", (28, 80)),
    ("rx-7600", "RX 7600", "RX 7600", r"7600(?!\s*xt)", (18, 55)),
    ("rx-6800-xt", "RX 6800 XT", "RX 6800 XT", r"6800\s*xt", (25, 70)),
    ("rx-6700-xt", "RX 6700 XT", "RX 6700 XT", r"6700\s*xt", (18, 55)),
    ("rx-6600", "RX 6600", "RX 6600", r"6600(?!\s*xt)", (10, 40)),
    ("rx-580", "RX 580", "RX 580", r"rx\s*580", (3, 12)),
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
    ("sony-a7r3", "소니 A7R3", "소니 A7R3", r"a7\s*r3|a7\s*r\s*iii\b", (90, 200)),
    ("sony-a9", "소니 A9", "소니 A9", r"\ba9\b(?!\s*(2|ii|3|iii))", (90, 220)),
    ("sony-a6700", "소니 A6700", "소니 A6700", r"a6700", (110, 220)),
    ("sony-a6600", "소니 A6600", "소니 A6600", r"a6600", (60, 140)),
    ("sony-a6400", "소니 A6400", "소니 A6400", r"a6400", (50, 120)),
    ("sony-a6000", "소니 A6000", "소니 A6000", r"a6000", (15, 60)),
    ("sony-zv-e10", "소니 ZV-E10", "소니 ZV-E10", r"zv\s*-?\s*e10(?!\s*(2|ii|m2))", (40, 100)),
    ("sony-zv-e10m2", "소니 ZV-E10 II", "소니 ZV-E10 II", r"zv\s*-?\s*e10\s*(2|ii|m2)", (80, 160)),
    ("sony-zv1", "소니 ZV-1", "소니 ZV1", r"zv\s*-?\s*1(?!0)", (30, 80)),
    # Canon
    ("canon-r5m2", "캐논 R5 Mark II", "캐논 R5 마크2", r"r5\s*(mark\s*)?(2|ii)\b|r5\s*마크\s*2", (350, 650)),
    ("canon-r5", "캐논 R5", "캐논 R5", r"eos\s*r5(?!\s*(c|mark|2|ii|마크))|캐논\s*r5(?!\s*(c|mark|2|ii|마크))", (180, 380)),
    ("canon-r6m2", "캐논 R6 Mark II", "캐논 R6 마크2", r"r6\s*(mark\s*)?(2|ii)\b|r6\s*마크\s*2", (200, 380)),
    ("canon-r6", "캐논 R6", "캐논 R6", r"eos\s*r6(?!\s*(mark|2|ii|마크))|캐논\s*r6(?!\s*(mark|2|ii|마크))", (130, 280)),
    ("canon-r7", "캐논 R7", "캐논 R7", r"eos\s*r7(?!\d)|캐논\s*r7(?!\d)", (90, 190)),
    ("canon-r8", "캐논 R8", "캐논 R8", r"eos\s*r8|캐논\s*r8", (110, 240)),
    ("canon-r100", "캐논 R100", "캐논 R100", r"eos\s*r100|캐논\s*r100", (30, 80)),
    ("canon-r10", "캐논 R10", "캐논 R10", r"eos\s*r10(?!0)|캐논\s*r10(?!0)", (60, 140)),
    ("canon-r50", "캐논 R50", "캐논 R50", r"eos\s*r50|캐논\s*r50", (50, 120)),
    ("canon-rp", "캐논 RP", "캐논 RP", r"eos\s*rp|캐논\s*rp", (55, 140)),
    ("canon-200d2", "캐논 200D II", "캐논 200D", r"200d", (30, 90)),
    ("canon-90d", "캐논 90D", "캐논 90D", r"90d", (70, 170)),
    ("canon-5d4", "캐논 5D Mark IV", "캐논 5D 마크4", r"5d\s*(mark\s*)?(4|iv)\b|오두막\s*4", (70, 160)),
    ("canon-6d2", "캐논 6D Mark II", "캐논 6D 마크2", r"6d\s*(mark\s*)?(2|ii)\b|육두막", (50, 110)),
    ("canon-g7x3", "캐논 G7X Mark III", "캐논 G7X 마크3", r"g7\s*x.{0,8}(3|iii)\b|g7x\s*마크\s*3", (60, 130)),
    # Nikon
    ("nikon-z8", "니콘 Z8", "니콘 Z8", r"\bz8\b", (280, 520)),
    ("nikon-z7ii", "니콘 Z7 II", "니콘 Z7 II", r"z7\s*(2|ii)\b", (130, 260)),
    ("nikon-z7", "니콘 Z7", "니콘 Z7", r"\bz7\b(?!\s*(2|ii))", (90, 200)),
    ("nikon-z6iii", "니콘 Z6 III", "니콘 Z6 III", r"z6\s*(3|iii)\b", (220, 400)),
    ("nikon-z6ii", "니콘 Z6 II", "니콘 Z6 II", r"z6\s*(2|ii)\b", (100, 220)),
    ("nikon-z6", "니콘 Z6", "니콘 Z6", r"\bz6\b(?!\s*(2|3|ii|iii))", (60, 150)),
    ("nikon-z5", "니콘 Z5", "니콘 Z5", r"\bz5\b", (60, 140)),
    ("nikon-zf", "니콘 Zf", "니콘 Zf", r"\bzf\b(?!c)", (180, 360)),
    ("nikon-zfc", "니콘 Zfc", "니콘 Zfc", r"zfc|z\s*fc\b", (60, 150)),
    ("nikon-z30", "니콘 Z30", "니콘 Z30", r"z30", (50, 110)),
    ("nikon-d850", "니콘 D850", "니콘 D850", r"d850", (120, 270)),
    # Fuji / Ricoh
    ("fuji-xt5", "후지 X-T5", "후지 X-T5", r"x\s*-?\s*t5", (140, 300)),
    ("fuji-xt4", "후지 X-T4", "후지 X-T4", r"x\s*-?\s*t4", (90, 200)),
    ("fuji-xt30", "후지 X-T30", "후지 X-T30", r"x\s*-?\s*t30", (50, 110)),
    ("fuji-xt3", "후지 X-T3", "후지 X-T3", r"x\s*-?\s*t3(?!0)", (60, 140)),
    ("fuji-x100vi", "후지 X100VI", "후지 X100VI", r"x100\s*vi\b|x100\s*6", (180, 380)),
    ("fuji-x100v", "후지 X100V", "후지 X100V", r"x100\s*v\b(?!i)", (120, 280)),
    ("fuji-xs20", "후지 X-S20", "후지 X-S20", r"x\s*-?\s*s20", (110, 220)),
    ("fuji-xe4", "후지 X-E4", "후지 X-E4", r"x\s*-?\s*e4", (70, 150)),
    ("fuji-xh2", "후지 X-H2", "후지 X-H2", r"x\s*-?\s*h2(?!s)", (140, 280)),
    ("ricoh-gr3x", "리코 GR3x", "리코 GR3x", r"gr\s*3\s*x|gr\s*iii\s*x", (80, 180)),
    ("ricoh-gr3", "리코 GR3", "리코 GR3", r"gr\s*3(?!\s*x)|gr\s*iii(?!\s*x)", (70, 170)),
    # Panasonic
    ("panasonic-s5ii", "파나소닉 S5 II", "파나소닉 S5 II", r"s5\s*(2|ii)\b|s5\s*m2", (120, 240)),
    ("panasonic-gh6", "파나소닉 GH6", "파나소닉 GH6", r"gh6", (90, 190)),
    ("panasonic-gh5", "파나소닉 GH5", "파나소닉 GH5", r"gh5(?!s)", (50, 120)),
]

# ---------------------------------------------------------------- Console
CONSOLE_EXCLUDE = ["조이콘", "컨트롤러", "듀얼센스", "프로콘", "칩", "타이틀", "케이스",
                   "거치대", "충전", "독만", "스킨", "게임보이", "3ds", "\\bds\\b"]
CONSOLES = [
    ("nintendo-switch2", "닌텐도 스위치 2", "닌텐도 스위치2", r"스위치\s*2|switch\s*2", (40, 100)),
    ("nintendo-switch-oled", "닌텐도 스위치 OLED", "스위치 OLED", r"스위치\s*(oled|올레드)|(oled|올레드)\s*스위치", (20, 50)),
    ("nintendo-switch-lite", "닌텐도 스위치 라이트", "스위치 라이트", r"(스위치|switch)\s*(라이트|lite)", (8, 25)),
    ("nintendo-switch", "닌텐도 스위치", "닌텐도 스위치 본체", r"(스위치|switch)(?!\s*2)", (12, 40)),
    ("ps5-pro", "플레이스테이션 5 Pro", "PS5 PRO", r"(ps5|플스5|플레이스테이션\s*5)\s*(pro|프로)", (60, 120)),
    ("ps5", "플레이스테이션 5", "PS5", r"ps5|플스5|플레이스테이션\s*5", (30, 90)),
    ("ps-portal", "플레이스테이션 포탈", "플스 포탈", r"포탈|portal", (15, 40)),
    ("xbox-series-x", "Xbox Series X", "엑스박스 시리즈X", r"(시리즈|series)\s*x", (25, 75)),
    ("xbox-series-s", "Xbox Series S", "엑스박스 시리즈S", r"(시리즈|series)\s*s\b", (15, 45)),
    ("steam-deck", "스팀덱", "스팀덱", r"스팀\s*덱|steam\s*deck", (25, 95)),
    ("rog-ally", "ASUS ROG Ally", "로그 앨라이", r"rog\s*(ally|앨라이|얼라이)", (40, 95)),
    ("ps4-pro", "플레이스테이션 4 Pro", "PS4 PRO", r"(ps4|플스4)\s*(pro|프로)", (12, 40)),
    ("ps4", "플레이스테이션 4", "PS4", r"(ps4|플스4|플레이스테이션\s*4)(?!\s*(pro|프로))", (8, 30)),
]

# ---------------------------------------------------------------- Tablet
TABLET_EXCLUDE = ["케이스", "키보드", "펜슬", "필름", "거치대", "파우치", "어댑터", "충전기"]
TABLETS = [
    ("ipad-pro-m4", "아이패드 프로 M4", "아이패드 프로 M4", r"(프로|pro).{0,8}m4|m4.{0,8}(프로|pro)", (90, 250)),
    ("ipad-pro-m2", "아이패드 프로 M2", "아이패드 프로 M2", r"(프로|pro).{0,8}m2|m2.{0,8}(프로|pro)", (50, 160)),
    ("ipad-pro-m1", "아이패드 프로 M1", "아이패드 프로 M1", r"(프로|pro).{0,8}m1|m1.{0,8}(프로|pro)", (40, 130)),
    ("ipad-air-m3", "아이패드 에어 M3", "아이패드 에어 M3", r"(에어|air).{0,8}m3|m3.{0,8}(에어|air)", (60, 130)),
    ("ipad-air-m2", "아이패드 에어 M2", "아이패드 에어 M2", r"(에어|air).{0,8}m2|m2.{0,8}(에어|air)", (50, 110)),
    ("ipad-air5", "아이패드 에어 5", "아이패드 에어5", r"(에어|air)\s*5", (33, 75)),
    ("ipad-air4", "아이패드 에어 4", "아이패드 에어4", r"(에어|air)\s*4", (25, 60)),
    ("ipad-mini7", "아이패드 미니 7", "아이패드 미니7", r"미니\s*7|mini\s*7", (48, 95)),
    ("ipad-mini6", "아이패드 미니 6", "아이패드 미니6", r"미니\s*6|mini\s*6", (33, 75)),
    ("ipad-mini5", "아이패드 미니 5", "아이패드 미니5", r"미니\s*5|mini\s*5", (22, 55)),
    ("ipad-11", "아이패드 11세대", "아이패드 11세대", r"11\s*세대", (33, 75)),
    ("ipad-10", "아이패드 10세대", "아이패드 10세대", r"10\s*세대", (28, 65)),
    ("ipad-9", "아이패드 9세대", "아이패드 9세대", r"9\s*세대", (18, 48)),
    ("galaxy-tab-s10", "갤럭시 탭 S10", "갤럭시탭 S10", r"탭\s*s\s*10|tab\s*s10", (55, 150)),
    ("galaxy-tab-s9", "갤럭시 탭 S9", "갤럭시탭 S9", r"탭\s*s\s*9|tab\s*s9", (38, 115)),
    ("galaxy-tab-s8", "갤럭시 탭 S8", "갤럭시탭 S8", r"탭\s*s\s*8|tab\s*s8", (28, 90)),
    ("galaxy-tab-s7", "갤럭시 탭 S7", "갤럭시탭 S7", r"탭\s*s\s*7|tab\s*s7", (20, 70)),
    ("surface-pro9", "서피스 프로 9", "서피스 프로9", r"(서피스|surface)\s*(프로|pro)\s*9", (45, 110)),
    ("surface-pro8", "서피스 프로 8", "서피스 프로8", r"(서피스|surface)\s*(프로|pro)\s*8", (30, 80)),
]

# ---------------------------------------------------------------- Phone
PHONE_EXCLUDE = ["케이스", "필름", "수리", "액정만", "부품", "매입", "삽니다", "구합니다",
                 "강화유리", "스트랩", "충전기", "거치대", "공기계\\s*매입"]
PHONE_SET = ["풀박", "세트", "\\+", "일괄"]
PHONES = [
    # iPhone — 프로맥스/프로/일반 음 disambiguation via lookaheads
    ("iphone-16-pro-max", "아이폰 16 프로맥스", "아이폰 16 프로맥스", r"(아이폰|iphone)\s*16\s*(프로|pro)\s*(맥스|max)", (90, 220)),
    ("iphone-16-pro", "아이폰 16 프로", "아이폰 16 프로", r"(아이폰|iphone)\s*16\s*(프로|pro)(?!\s*(맥스|max))", (70, 170)),
    ("iphone-16e", "아이폰 16e", "아이폰 16e", r"(아이폰|iphone)\s*16\s*e\b", (40, 95)),
    ("iphone-16", "아이폰 16", "아이폰 16", r"(아이폰|iphone)\s*16(?!\s*(프로|pro|플러스|plus|e))", (50, 130)),
    ("iphone-15-pro-max", "아이폰 15 프로맥스", "아이폰 15 프로맥스", r"(아이폰|iphone)\s*15\s*(프로|pro)\s*(맥스|max)", (70, 170)),
    ("iphone-15-pro", "아이폰 15 프로", "아이폰 15 프로", r"(아이폰|iphone)\s*15\s*(프로|pro)(?!\s*(맥스|max))", (55, 140)),
    ("iphone-15-plus", "아이폰 15 플러스", "아이폰 15 플러스", r"(아이폰|iphone)\s*15\s*(플러스|plus)", (45, 110)),
    ("iphone-15", "아이폰 15", "아이폰 15", r"(아이폰|iphone)\s*15(?!\s*(프로|pro|플러스|plus))", (40, 100)),
    ("iphone-14-pro-max", "아이폰 14 프로맥스", "아이폰 14 프로맥스", r"(아이폰|iphone)\s*14\s*(프로|pro)\s*(맥스|max)", (45, 115)),
    ("iphone-14-pro", "아이폰 14 프로", "아이폰 14 프로", r"(아이폰|iphone)\s*14\s*(프로|pro)(?!\s*(맥스|max))", (38, 100)),
    ("iphone-14", "아이폰 14", "아이폰 14", r"(아이폰|iphone)\s*14(?!\s*(프로|pro|플러스|plus))", (25, 75)),
    ("iphone-13-pro-max", "아이폰 13 프로맥스", "아이폰 13 프로맥스", r"(아이폰|iphone)\s*13\s*(프로|pro)\s*(맥스|max)", (33, 90)),
    ("iphone-13-pro", "아이폰 13 프로", "아이폰 13 프로", r"(아이폰|iphone)\s*13\s*(프로|pro)(?!\s*(맥스|max))", (28, 80)),
    ("iphone-13", "아이폰 13", "아이폰 13", r"(아이폰|iphone)\s*13(?!\s*(프로|pro|미니|mini|플러스|plus))", (20, 62)),
    ("iphone-13-mini", "아이폰 13 미니", "아이폰 13 미니", r"(아이폰|iphone)\s*13\s*(미니|mini)", (18, 55)),
    ("iphone-12-pro", "아이폰 12 프로", "아이폰 12 프로", r"(아이폰|iphone)\s*12\s*(프로|pro)(?!\s*(맥스|max))", (16, 55)),
    ("iphone-12-mini", "아이폰 12 미니", "아이폰 12 미니", r"(아이폰|iphone)\s*12\s*(미니|mini)", (10, 38)),
    ("iphone-12", "아이폰 12", "아이폰 12", r"(아이폰|iphone)\s*12(?!\s*(프로|pro|미니|mini|플러스|plus))", (12, 45)),
    ("iphone-11-pro", "아이폰 11 프로", "아이폰 11 프로", r"(아이폰|iphone)\s*11\s*(프로|pro)", (12, 42)),
    ("iphone-11", "아이폰 11", "아이폰 11", r"(아이폰|iphone)\s*11(?!\s*(프로|pro))", (10, 35)),
    ("iphone-se3", "아이폰 SE3", "아이폰 SE3", r"(아이폰|iphone)\s*se\s*3|se\s*3\s*세대", (12, 42)),
    ("iphone-se2", "아이폰 SE2", "아이폰 SE2", r"(아이폰|iphone)\s*se\s*2\b|se\s*2\s*세대", (8, 30)),
    # Galaxy
    ("galaxy-s25-ultra", "갤럭시 S25 울트라", "갤럭시 S25 울트라", r"s\s*25\s*(울트라|ultra)", (70, 165)),
    ("galaxy-s25", "갤럭시 S25", "갤럭시 S25", r"갤럭시\s*s\s*25(?!\s*(울트라|ultra|플러스|plus|\+|fe|엣지|edge))", (40, 110)),
    ("galaxy-s24-ultra", "갤럭시 S24 울트라", "갤럭시 S24 울트라", r"s\s*24\s*(울트라|ultra)", (50, 125)),
    ("galaxy-s23-ultra", "갤럭시 S23 울트라", "갤럭시 S23 울트라", r"s\s*23\s*(울트라|ultra)", (35, 95)),
    ("galaxy-s22-ultra", "갤럭시 S22 울트라", "갤럭시 S22 울트라", r"s\s*22\s*(울트라|ultra)", (20, 65)),
    ("galaxy-s24-fe", "갤럭시 S24 FE", "갤럭시 S24 FE", r"s\s*24\s*fe", (20, 60)),
    ("galaxy-s24", "갤럭시 S24", "갤럭시 S24", r"갤럭시\s*s\s*24(?!\s*(울트라|ultra|플러스|plus|\+|fe))", (25, 78)),
    ("galaxy-s23-fe", "갤럭시 S23 FE", "갤럭시 S23 FE", r"s\s*23\s*fe", (15, 45)),
    ("galaxy-s23", "갤럭시 S23", "갤럭시 S23", r"갤럭시\s*s\s*23(?!\s*(울트라|ultra|플러스|plus|\+|fe))", (18, 60)),
    ("galaxy-zflip6", "갤럭시 Z플립6", "갤럭시 Z플립6", r"(플립|flip)\s*6", (28, 90)),
    ("galaxy-zflip5", "갤럭시 Z플립5", "갤럭시 Z플립5", r"(플립|flip)\s*5", (20, 68)),
    ("galaxy-zflip4", "갤럭시 Z플립4", "갤럭시 Z플립4", r"(플립|flip)\s*4", (12, 45)),
    ("galaxy-zfold6", "갤럭시 Z폴드6", "갤럭시 Z폴드6", r"(폴드|fold)\s*6", (55, 155)),
    ("galaxy-zfold5", "갤럭시 Z폴드5", "갤럭시 Z폴드5", r"(폴드|fold)\s*5", (38, 115)),
    ("galaxy-zfold4", "갤럭시 Z폴드4", "갤럭시 Z폴드4", r"(폴드|fold)\s*4", (25, 80)),
    ("galaxy-note20-ultra", "갤럭시 노트20 울트라", "갤럭시 노트20 울트라", r"(노트|note)\s*20\s*(울트라|ultra)", (15, 50)),
]

# ---------------------------------------------------------------- Laptop
LAPTOP_EXCLUDE = ["케이스", "파우치", "거치대", "충전기", "어댑터", "매입", "삽니다",
                  "구합니다", "부품", "키스킨", "보호필름", "스탠드"]
LAPTOP_SET = ["\\+", "세트", "일괄"]
LAPTOPS = [
    ("macbook-air-m4", "맥북 에어 M4", "맥북 에어 M4", r"(맥북|macbook)\s*(에어|air).{0,12}m4|m4.{0,12}(에어|air)", (100, 200)),
    ("macbook-air-m3", "맥북 에어 M3", "맥북 에어 M3", r"(맥북|macbook)\s*(에어|air).{0,12}m3|m3.{0,12}(에어|air)", (75, 165)),
    ("macbook-air-m2", "맥북 에어 M2", "맥북 에어 M2", r"(맥북|macbook)\s*(에어|air).{0,12}m2|m2.{0,12}(에어|air)", (55, 130)),
    ("macbook-air-m1", "맥북 에어 M1", "맥북 에어 M1", r"(맥북|macbook)\s*(에어|air).{0,12}m1|m1.{0,12}(에어|air)", (35, 90)),
    ("macbook-pro-m4", "맥북 프로 M4", "맥북 프로 M4", r"(맥북|macbook)\s*(프로|pro).{0,14}m4|m4(?:\s*(pro|max|프로|맥스))?.{0,12}(맥북|macbook)\s*(프로|pro)", (140, 450)),
    ("macbook-pro-m3", "맥북 프로 M3", "맥북 프로 M3", r"(맥북|macbook)\s*(프로|pro).{0,14}m3", (110, 380)),
    ("macbook-pro-m2", "맥북 프로 M2", "맥북 프로 M2", r"(맥북|macbook)\s*(프로|pro).{0,14}m2", (85, 320)),
    ("macbook-pro-m1", "맥북 프로 M1", "맥북 프로 M1", r"(맥북|macbook)\s*(프로|pro).{0,14}m1", (60, 250)),
    ("galaxy-book5-pro", "갤럭시북5 프로", "갤럭시북5 프로", r"(갤럭시\s*북|갤북)\s*5\s*(프로|pro)", (80, 180)),
    ("galaxy-book4-pro", "갤럭시북4 프로", "갤럭시북4 프로", r"(갤럭시\s*북|갤북)\s*4\s*(프로|pro)", (60, 150)),
    ("galaxy-book3-pro", "갤럭시북3 프로", "갤럭시북3 프로", r"(갤럭시\s*북|갤북)\s*3\s*(프로|pro)", (45, 115)),
    ("lg-gram-16", "LG 그램 16", "LG 그램 16", r"그램\s*16|gram\s*16", (35, 160)),
    ("lg-gram-17", "LG 그램 17", "LG 그램 17", r"그램\s*17|gram\s*17", (35, 170)),
    ("lg-gram-15", "LG 그램 15", "LG 그램 15", r"그램\s*15|gram\s*15", (25, 120)),
    ("lg-gram-14", "LG 그램 14", "LG 그램 14", r"그램\s*14|gram\s*14", (20, 100)),
    ("thinkpad-x1carbon", "레노버 씽크패드 X1 카본", "씽크패드 X1 카본", r"x1\s*(카본|carbon)", (25, 120)),
    ("lenovo-legion5", "레노버 리전 5", "레노버 리전5", r"(리전|legion)\s*5", (40, 130)),
    ("asus-zephyrus-g14", "ASUS 제피러스 G14", "제피러스 G14", r"(제피러스|zephyrus)\s*g14", (60, 190)),
    ("dell-xps13", "델 XPS 13", "델 XPS 13", r"xps\s*13", (30, 110)),
]

# ---------------------------------------------------------------- Audio (earbuds/headphones)
AUDIO_EXCLUDE = ["케이스만", "이어팁", "유닛", "한쪽", "오른쪽", "왼쪽", "편측", "충전기",
                 "케이블", "폼팁", "커버", "스킨", "매입", "삽니다"]
AUDIO_SET = ["\\+", "세트", "일괄"]
AUDIOS = [
    ("airpods-pro2", "에어팟 프로 2", "에어팟 프로 2세대", r"에어팟\s*프로\s*2|airpods\s*pro\s*2", (13, 33)),
    ("airpods-pro1", "에어팟 프로 1", "에어팟 프로 1세대", r"(에어팟\s*프로|airpods\s*pro)\s*(1|1세대)(?!\d)", (7, 22)),
    ("airpods-4", "에어팟 4", "에어팟 4세대", r"에어팟\s*4|airpods\s*4", (10, 28)),
    ("airpods-3", "에어팟 3", "에어팟 3세대", r"에어팟\s*3|airpods\s*3", (8, 22)),
    ("airpods-2", "에어팟 2", "에어팟 2세대", r"(에어팟|airpods)\s*2(?!\d)", (4, 15)),
    ("airpods-max", "에어팟 맥스", "에어팟 맥스", r"에어팟\s*맥스|airpods\s*max", (30, 90)),
    ("buds3-pro", "갤럭시 버즈3 프로", "버즈3 프로", r"버즈\s*3\s*(프로|pro)", (9, 28)),
    ("buds3", "갤럭시 버즈3", "갤럭시 버즈3", r"버즈\s*3(?!\s*(프로|pro))", (5, 16)),
    ("buds2-pro", "갤럭시 버즈2 프로", "버즈2 프로", r"버즈\s*2\s*(프로|pro)", (5, 18)),
    ("buds2", "갤럭시 버즈2", "갤럭시 버즈2", r"버즈\s*2(?!\s*(프로|pro))", (3, 10)),
    ("sony-wf1000xm5", "소니 WF-1000XM5", "소니 WF-1000XM5", r"wf\s*-?\s*1000\s*xm\s*5|wf.{0,6}xm5", (12, 32)),
    ("sony-wf1000xm4", "소니 WF-1000XM4", "소니 WF-1000XM4", r"wf\s*-?\s*1000\s*xm\s*4|wf.{0,6}xm4", (7, 20)),
    ("sony-wh1000xm5", "소니 WH-1000XM5", "소니 WH-1000XM5", r"1000\s*xm\s*5|xm5", (18, 48)),
    ("sony-wh1000xm4", "소니 WH-1000XM4", "소니 WH-1000XM4", r"1000\s*xm\s*4|xm4", (12, 35)),
    ("bose-qc-ultra", "보스 QC 울트라", "보스 QC 울트라", r"(qc|콰이어트컴포트)\s*(울트라|ultra)", (20, 52)),
    ("bose-qc45", "보스 QC45", "보스 QC45", r"qc\s*45", (13, 32)),
    ("marshall-major4", "마샬 메이저 4", "마샬 메이저4", r"(마샬|marshall).{0,8}(메이저|major)\s*4", (4, 14)),
    ("sennheiser-momentum4", "젠하이저 모멘텀 4", "젠하이저 모멘텀4", r"(모멘텀|momentum)\s*4", (13, 30)),
    ("sony-inzone-h9", "소니 인존 H9", "소니 인존 H9", r"(인존|inzone)\s*h?\s*9", (12, 25)),
    ("gpro-x-headset", "로지텍 G PRO X 헤드셋", "로지텍 지프로 헤드셋", r"(g\s*pro|지프로)\s*x?.{0,8}헤드셋", (4, 12)),
    ("razer-blackshark-v2", "레이저 블랙샤크 V2", "레이저 블랙샤크 V2", r"블랙샤크\s*v?\s*2", (4, 13)),
    ("steelseries-nova7", "스틸시리즈 아크티스 노바 7", "아크티스 노바 7", r"(아크티스|arctis|스틸시리즈|steelseries).{0,10}(노바|nova)\s*7", (8, 18)),
    ("hyperx-cloud2", "하이퍼엑스 클라우드 2", "하이퍼엑스 클라우드2", r"(하이퍼\s*엑스|hyperx).{0,10}(클라우드|cloud)\s*(2|ii)(?!i)", (3, 9)),
]

# ---------------------------------------------------------------- Smartwatch
WATCH_EXCLUDE = ["스트랩", "밴드", "케이스", "충전기", "필름", "커버", "매입", "삽니다", "거치대"]
WATCH_SET = ["\\+", "세트", "일괄"]
WATCHES = [
    ("apple-watch-ultra2", "애플워치 울트라 2", "애플워치 울트라2", r"(애플\s*워치|애플워치|apple\s*watch).{0,8}(울트라|ultra)\s*2", (45, 110)),
    ("apple-watch-ultra1", "애플워치 울트라 1", "애플워치 울트라1", r"(애플\s*워치|애플워치|apple\s*watch).{0,8}(울트라|ultra)(?!\s*2)", (30, 80)),
    ("apple-watch-10", "애플워치 10", "애플워치 10", r"(애플\s*워치|애플워치|apple\s*watch)\s*(시리즈\s*)?10", (28, 70)),
    ("apple-watch-9", "애플워치 9", "애플워치 9", r"(애플\s*워치|애플워치|apple\s*watch)\s*(시리즈\s*)?9", (20, 55)),
    ("apple-watch-8", "애플워치 8", "애플워치 8", r"(애플\s*워치|애플워치|apple\s*watch)\s*(시리즈\s*)?8", (14, 45)),
    ("apple-watch-7", "애플워치 7", "애플워치 7", r"(애플\s*워치|애플워치|apple\s*watch)\s*(시리즈\s*)?7", (10, 38)),
    ("apple-watch-6", "애플워치 6", "애플워치 6", r"(애플\s*워치|애플워치|apple\s*watch)\s*(시리즈\s*)?6", (8, 30)),
    ("apple-watch-se2", "애플워치 SE2", "애플워치 SE2", r"(애플\s*워치|애플워치|apple\s*watch)\s*se\s*2", (9, 32)),
    ("galaxy-watch-ultra", "갤럭시 워치 울트라", "갤럭시 워치 울트라", r"(갤럭시\s*워치|갤워치)\s*(울트라|ultra)", (22, 60)),
    ("galaxy-watch7", "갤럭시 워치 7", "갤럭시 워치7", r"(갤럭시\s*워치|갤워치)\s*7", (10, 35)),
    ("galaxy-watch6", "갤럭시 워치 6", "갤럭시 워치6", r"(갤럭시\s*워치|갤워치)\s*6", (7, 28)),
    ("galaxy-watch5-pro", "갤럭시 워치 5 프로", "갤럭시 워치5 프로", r"(갤럭시\s*워치|갤워치)\s*5\s*(프로|pro)", (8, 28)),
    ("galaxy-watch5", "갤럭시 워치 5", "갤럭시 워치5", r"(갤럭시\s*워치|갤워치)\s*5(?!\s*(프로|pro))", (5, 22)),
    ("garmin-forerunner965", "가민 포러너 965", "가민 포러너 965", r"(포러너|forerunner)\s*965", (25, 60)),
    ("garmin-forerunner255", "가민 포러너 255", "가민 포러너 255", r"(포러너|forerunner)\s*255", (12, 35)),
    ("garmin-fenix7", "가민 피닉스 7", "가민 피닉스7", r"(피닉스|페닉스|fenix)\s*7", (25, 70)),
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
    ("ping-g410-driver", "핑 G410 드라이버", "G410 드라이버", r"g410", (10, 40)),
    ("cw-elyte-driver", "캘러웨이 ELYTE 드라이버", "캘러웨이 엘라이트 드라이버", r"elyte|엘라이트", (45, 120)),
    ("cw-epic-driver", "캘러웨이 에픽 드라이버", "캘러웨이 에픽 드라이버", r"(에픽|epic)\s*(스피드|speed|맥스|max)", (8, 40)),
    ("cobra-darkspeed-driver", "코브라 다크스피드 드라이버", "코브라 다크스피드", r"다크\s*스피드|darkspeed", (28, 80)),
    ("xxio-13-driver", "젝시오 13 드라이버", "젝시오 13 드라이버", r"젝시오\s*13|xxio\s*13", (45, 125)),
    ("xxio-12-driver", "젝시오 12 드라이버", "젝시오 12 드라이버", r"젝시오\s*12|xxio\s*12", (28, 95)),
    ("xxio-11-driver", "젝시오 11 드라이버", "젝시오 11 드라이버", r"젝시오\s*11|xxio\s*11", (18, 70)),
]


# ---------------------------------------------------------------- Appliance
APPLIANCE_EXCLUDE = ["헤드만", "배터리", "필터", "거치대", "부품", "수리", "호환", "어댑터"]
APPLIANCES = [
    ("dyson-v15", "다이슨 V15", "다이슨 V15", r"v15", (25, 75)),
    ("dyson-v12", "다이슨 V12", "다이슨 V12", r"v12", (20, 60)),
    ("dyson-v11", "다이슨 V11", "다이슨 V11", r"v11", (15, 50)),
    ("dyson-v10", "다이슨 V10", "다이슨 V10", r"v10", (10, 40)),
    ("dyson-v8", "다이슨 V8", "다이슨 V8", r"\bv8\b", (7, 30)),
    ("dyson-airwrap", "다이슨 에어랩", "다이슨 에어랩", r"에어랩|airwrap", (20, 60)),
    ("dyson-supersonic", "다이슨 슈퍼소닉", "다이슨 슈퍼소닉", r"슈퍼소닉|supersonic", (10, 35)),
    ("roborock-s8", "로보락 S8", "로보락 S8", r"로보락\s*s8|roborock\s*s8", (30, 120)),
    ("roborock-s7", "로보락 S7", "로보락 S7", r"로보락\s*s7|roborock\s*s7", (15, 70)),
    ("roborock-qrevo", "로보락 Q레보", "로보락 Q레보", r"큐레보|q\s*레보|q\s*revo", (25, 90)),
    ("lg-styler", "LG 스타일러", "LG 스타일러", r"스타일러", (20, 120)),
    ("bespoke-jet", "삼성 비스포크 제트", "비스포크 제트", r"비스포크\s*제트|bespoke\s*jet", (15, 70)),
    ("balmuda-toaster", "발뮤다 토스터", "발뮤다 토스터", r"발뮤다.{0,8}(토스터|toaster)", (5, 20)),
]

# ---------------------------------------------------------------- Monitor
MONITOR_EXCLUDE = ["모니터암", "거치대", "받침대", "스탠드만", "케이블", "박스만"]
MONITORS = [
    ("odyssey-g9", "삼성 오디세이 G9", "오디세이 G9", r"오디세이\s*g9|odyssey\s*g9|네오\s*g9", (40, 130)),
    ("odyssey-g7", "삼성 오디세이 G7", "오디세이 G7", r"오디세이\s*g7|odyssey\s*g7", (20, 60)),
    ("odyssey-g5", "삼성 오디세이 G5", "오디세이 G5", r"오디세이\s*g5|odyssey\s*g5", (10, 38)),
    ("odyssey-g8-oled", "삼성 오디세이 OLED G8", "오디세이 G8", r"오디세이\s*(oled\s*)?g8|odyssey\s*(oled\s*)?g8", (55, 140)),
    ("lg-27gp850", "LG 27GP850", "LG 27GP850", r"27gp850", (15, 45)),
    ("lg-27gn850", "LG 27GN850", "LG 27GN850", r"27gn850", (12, 38)),
    ("studio-display", "애플 스튜디오 디스플레이", "스튜디오 디스플레이", r"스튜디오\s*디스플레이|studio\s*display", (80, 190)),
]

# ---------------------------------------------------------------- CPU
CPU_EXCLUDE = ["본체", "컴퓨터", "노트북", "데스크탑", "조립"]
CPU_SET = ["보드", "세트", "\\+", "메인보드"]
CPUS = [
    ("r9-7950x3d", "라이젠 9 7950X3D", "7950X3D", r"7950\s*x3d", (35, 80)),
    ("r7-9800x3d", "라이젠 7 9800X3D", "9800X3D", r"9800\s*x3d", (40, 85)),
    ("r7-7800x3d", "라이젠 7 7800X3D", "7800X3D", r"7800\s*x3d", (25, 60)),
    ("r7-5800x3d", "라이젠 7 5800X3D", "5800X3D", r"5800\s*x3d", (18, 45)),
    ("r7-5700x3d", "라이젠 7 5700X3D", "5700X3D", r"5700\s*x3d", (15, 38)),
    ("r5-7600", "라이젠 5 7600", "라이젠 7600", r"라이젠.{0,6}7600|7600x?\b", (8, 28)),
    ("r5-5600", "라이젠 5 5600", "라이젠 5600", r"라이젠.{0,6}5600|5600x?\b", (5, 18)),
    ("i5-12400f", "인텔 i5-12400F", "인텔 12400F", r"12400f?", (6, 18)),
    ("i5-13600k", "인텔 i5-13600K", "인텔 13600K", r"13600kf?", (15, 40)),
    ("i5-14600k", "인텔 i5-14600K", "인텔 14600K", r"14600kf?", (18, 45)),
    ("i7-13700k", "인텔 i7-13700K", "인텔 13700K", r"13700kf?", (22, 55)),
    ("i9-14900k", "인텔 i9-14900K", "인텔 14900K", r"14900kf?", (35, 75)),
]

# ---------------------------------------------------------------- Peripheral (keyboard/mouse)
PERIPHERAL_EXCLUDE = ["키캡만", "스위치만", "케이블", "장패드", "마우스패드", "손목"]
PERIPHERALS = [
    ("gpro-superlight", "로지텍 G PRO X 슈퍼라이트", "지프로 슈퍼라이트", r"슈퍼라이트|superlight", (5, 18)),
    ("mx-master3s", "로지텍 MX Master 3S", "MX Master 3S", r"mx\s*master|마스터\s*3", (5, 15)),
    ("mx-keys", "로지텍 MX Keys", "로지텍 MX Keys", r"mx\s*keys|mx\s*키즈", (5, 15)),
    ("logitech-g502", "로지텍 G502", "로지텍 G502", r"g502", (3, 12)),
    ("logitech-g304", "로지텍 G304", "로지텍 G304", r"g304", (1, 6)),
    ("razer-viper", "레이저 바이퍼", "레이저 바이퍼", r"바이퍼|viper", (5, 22)),
    ("hhkb", "HHKB 해피해킹", "해피해킹 키보드", r"hhkb|해피해킹", (15, 45)),
    ("realforce", "리얼포스 키보드", "리얼포스 키보드", r"리얼포스|realforce", (10, 45)),
    ("leopold", "레오폴드 키보드", "레오폴드 키보드", r"레오폴드|leopold", (5, 20)),
    ("apple-magic-keyboard", "애플 매직 키보드", "매직 키보드", r"매직\s*키보드|magic\s*keyboard", (5, 22)),
    ("apple-magic-mouse", "애플 매직 마우스", "매직 마우스", r"매직\s*마우스|magic\s*mouse", (3, 12)),
]

# ---------------------------------------------------------------- Golf iron / putter·wedge
IRON_EXCLUDE = ["드라이버", "우드", "유틸", "퍼터", "웨지", "풀세트", "풀 세트", "캐디백", "단품"]
IRONS = [
    ("tt-t100-iron", "타이틀리스트 T100 아이언", "타이틀리스트 T100 아이언", r"t100", (40, 130)),
    ("tt-t200-iron", "타이틀리스트 T200 아이언", "타이틀리스트 T200 아이언", r"t200", (35, 120)),
    ("ping-g430-iron", "핑 G430 아이언", "핑 G430 아이언", r"g430", (50, 140)),
    ("ping-g425-iron", "핑 G425 아이언", "핑 G425 아이언", r"g425", (35, 110)),
    ("mizuno-jpx923-iron", "미즈노 JPX923 아이언", "미즈노 JPX923 아이언", r"jpx\s*923", (40, 120)),
    ("xxio-13-iron", "젝시오 13 아이언", "젝시오 13 아이언", r"젝시오\s*13|xxio\s*13", (45, 130)),
    ("xxio-12-iron", "젝시오 12 아이언", "젝시오 12 아이언", r"젝시오\s*12|xxio\s*12", (35, 110)),
    ("tm-p790-iron", "테일러메이드 P790 아이언", "P790 아이언", r"p\s*-?790", (40, 120)),
    ("cw-apex-iron", "캘러웨이 에이펙스 아이언", "에이펙스 아이언", r"에이펙스|apex", (35, 110)),
    ("tt-t150-iron", "타이틀리스트 T150 아이언", "타이틀리스트 T150 아이언", r"t150", (50, 140)),
    ("ping-i230-iron", "핑 i230 아이언", "핑 i230 아이언", r"i230", (45, 120)),
]
PUTTER_EXCLUDE = ["드라이버", "우드", "유틸", "아이언", "풀세트", "풀 세트", "캐디백", "커버만", "그립만"]
PUTTERS = [
    ("scotty-newport2", "스카티카메론 뉴포트 2", "스카티카메론 뉴포트2", r"뉴포트\s*2|newport\s*2", (30, 90)),
    ("scotty-phantom", "스카티카메론 팬텀", "스카티카메론 팬텀", r"팬텀|phantom", (30, 95)),
    ("odyssey-whitehot", "오디세이 화이트핫 퍼터", "오디세이 화이트핫 퍼터", r"화이트\s*핫|white\s*hot", (10, 40)),
    ("odyssey-ai-one", "오디세이 AI-ONE 퍼터", "오디세이 AI ONE 퍼터", r"ai\s*-?\s*one", (20, 60)),
    ("odyssey-2ball", "오디세이 투볼 퍼터", "오디세이 투볼 퍼터", r"투\s*볼|2\s*-?\s*ball", (8, 35)),
    ("ping-anser-putter", "핑 앤서 퍼터", "핑 앤서 퍼터", r"앤서|anser", (15, 50)),
    ("tm-spider-putter", "테일러메이드 스파이더 퍼터", "스파이더 퍼터", r"스파이더|spider", (10, 40)),
    ("vokey-sm10", "보키 SM10 웨지", "보키 SM10 웨지", r"sm\s*10", (10, 30)),
    ("vokey-sm9", "보키 SM9 웨지", "보키 SM9 웨지", r"sm\s*9", (8, 25)),
    ("vokey-sm8", "보키 SM8 웨지", "보키 SM8 웨지", r"sm\s*8", (6, 20)),
]

# ---------------------------------------------------------------- Camera lens
LENS_EXCLUDE = ["필터", "캡만", "후드만", "어댑터", "바디", "케이스", "파우치"]
LENSES = [
    ("sony-2470gm2", "소니 FE 24-70 GM2", "소니 2470GM2", r"24-?70.{0,6}gm\s*(2|ii)|2470\s*gm\s*2", (130, 250)),
    ("sony-2470gm", "소니 FE 24-70 GM", "소니 2470GM", r"24-?70.{0,6}gm(?!\s*(2|ii))|2470\s*gm(?!\s*2)", (80, 170)),
    ("sony-70200gm2", "소니 FE 70-200 GM2", "소니 70200GM2", r"70-?200.{0,8}gm\s*(2|ii)", (160, 290)),
    ("sigma-2470-art", "시그마 24-70 아트", "시그마 24-70 아트", r"시그마.{0,10}24-?70|24-?70.{0,10}(아트|art)", (50, 130)),
    ("sony-85f18", "소니 FE 85mm F1.8", "소니 85.8 렌즈", r"sel85f18|85.{0,4}f?1\.8", (30, 70)),
    ("canon-rf2470", "캐논 RF 24-70", "캐논 RF 24-70", r"rf\s*24-?70", (130, 250)),
    ("canon-rf70200", "캐논 RF 70-200", "캐논 RF 70-200", r"rf\s*70-?200", (130, 280)),
    ("canon-rf50", "캐논 RF 50mm F1.8", "캐논 RF 50mm", r"rf\s*50", (15, 35)),
    ("tamron-2875", "탐론 28-75 G2", "탐론 28-75", r"28-?75", (40, 100)),
    ("tamron-70180", "탐론 70-180", "탐론 70-180", r"70-?180", (40, 95)),
    ("sony-35gm", "소니 FE 35mm GM", "소니 35GM", r"35.{0,4}gm|sel35f14gm", (80, 160)),
    ("sigma-56f14", "시그마 56mm F1.4", "시그마 56.4", r"시그마.{0,10}56|56mm.{0,6}1\.4", (15, 40)),
]

# ---------------------------------------------------------------- Film camera
FILMCAM_EXCLUDE = ["필름만", "현상", "케이스", "스트랩", "필터"]
FILMCAMS = [
    ("contax-t2", "콘탁스 T2", "콘탁스 T2", r"콘탁스\s*t2|contax\s*t2", (80, 200)),
    ("contax-t3", "콘탁스 T3", "콘탁스 T3", r"콘탁스\s*t3|contax\s*t3", (150, 330)),
    ("canon-ae1", "캐논 AE-1", "캐논 AE-1", r"ae-?1", (15, 60)),
    ("nikon-fm2", "니콘 FM2", "니콘 FM2", r"fm2", (25, 80)),
    ("olympus-mju2", "올림푸스 뮤2", "올림푸스 뮤2", r"뮤\s*2|mju\s*-?\s*(2|ii)", (25, 80)),
    ("rollei35", "롤라이 35", "롤라이 35", r"롤라이\s*35|rollei\s*35", (25, 90)),
    ("yashica-t4", "야시카 T4", "야시카 T4", r"야시카\s*t4|yashica\s*t4", (40, 120)),
    ("minolta-x700", "미놀타 X-700", "미놀타 X700", r"x\s*-?\s*700", (10, 40)),
    ("pentax-17", "펜탁스 17", "펜탁스 17", r"펜탁스\s*17|pentax\s*17", (40, 85)),
    ("nikon-f3-film", "니콘 F3", "니콘 F3", r"니콘\s*f3|nikon\s*f3", (25, 90)),
]

# ---------------------------------------------------------------- Action cam / gimbal
ACTIONCAM_EXCLUDE = ["케이스", "마운트", "거치대", "배터리", "필터", "스트랩"]
ACTIONCAMS = [
    ("osmo-pocket3", "DJI 오즈모 포켓3", "오즈모 포켓3", r"포켓\s*3|pocket\s*3", (35, 80)),
    ("dji-pocket2", "DJI 포켓2", "DJI 포켓2", r"포켓\s*2|pocket\s*2", (15, 40)),
    ("gopro-13", "고프로 히어로 13", "고프로 13", r"(고프로|gopro|히어로|hero)\s*13", (30, 65)),
    ("gopro-12", "고프로 히어로 12", "고프로 12", r"(고프로|gopro|히어로|hero)\s*12", (22, 50)),
    ("gopro-11", "고프로 히어로 11", "고프로 11", r"(고프로|gopro|히어로|hero)\s*11", (15, 40)),
    ("insta360-x5", "인스타360 X5", "인스타360 X5", r"(인스타|insta).{0,6}x5", (35, 75)),
    ("insta360-x4", "인스타360 X4", "인스타360 X4", r"(인스타|insta).{0,6}x4", (25, 60)),
    ("insta360-go3", "인스타360 GO 3", "인스타360 GO3", r"(인스타|insta).{0,8}go\s*3", (15, 40)),
    ("insta360-ace-pro", "인스타360 에이스 프로", "인스타360 에이스 프로", r"(에이스|ace)\s*(프로|pro)", (20, 50)),
    ("dji-action5", "DJI 오즈모 액션5", "오즈모 액션5", r"액션\s*5|action\s*5", (28, 60)),
    ("dji-action4", "DJI 오즈모 액션4", "오즈모 액션4", r"액션\s*4|action\s*4", (20, 50)),
]

# ---------------------------------------------------------------- Camping
CAMPING_EXCLUDE = ["커버만", "파우치만", "부품"]
CAMPINGS = [
    ("helinox-chairone", "헬리녹스 체어원", "헬리녹스 체어원", r"체어\s*원|chair\s*one", (5, 18)),
    ("helinox-tactical", "헬리녹스 택티컬 체어", "헬리녹스 택티컬 체어", r"택티컬.{0,10}(체어|chair)|(체어|chair).{0,5}택티컬", (8, 25)),
    ("helinox-cotone", "헬리녹스 코트원", "헬리녹스 코트원", r"코트\s*원|cot\s*one", (15, 45)),
    ("helinox-tableone", "헬리녹스 테이블원", "헬리녹스 테이블원", r"테이블\s*원|table\s*one", (4, 15)),
    ("snowpeak-igt", "스노우피크 IGT", "스노우피크 IGT", r"igt", (10, 60)),
    ("snowpeak-amenity", "스노우피크 어메니티돔", "스노우피크 어메니티돔", r"어메니티\s*돔?|amenity", (15, 45)),
    ("nordisk-asgard", "노르디스크 아스가르드", "노르디스크 아스가르드", r"아스가르드|asgard", (30, 100)),
    ("coleman-infinity", "콜맨 인피니티 체어", "콜맨 인피니티 체어", r"인피니티\s*체어|infinity\s*chair", (3, 12)),
]

# ---------------------------------------------------------------- Bike (folding)
BIKE_EXCLUDE = ["부품", "핸들", "안장", "바퀴만", "가방", "캐리어"]
BIKES = [
    ("brompton-tline", "브롬톤 T라인", "브롬톤 T라인", r"t\s*-?라인|t\s*line", (250, 550)),
    ("brompton-cline", "브롬톤 C라인", "브롬톤 C라인", r"c\s*-?라인|c\s*line", (90, 250)),
    ("brompton-pline", "브롬톤 P라인", "브롬톤 P라인", r"p\s*-?라인|p\s*line", (150, 350)),
    ("brompton-aline", "브롬톤 A라인", "브롬톤 A라인", r"a\s*-?라인|a\s*line", (60, 130)),
    ("dahon", "다혼 폴딩 자전거", "다혼 자전거", r"다혼|dahon", (10, 80)),
    ("strida", "스트라이다", "스트라이다", r"스트라이다|strida", (15, 60)),
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
                "joongna_category": "163",
                "label": "그래픽카드",
                "bunjang_category_prefix": "600200005",
                "sweep_ids": ["600200005"],
                "models": expand(GPUS, {"exclude": GPU_EXCLUDE},
                                 lambda s, l: _gpu_group(s)),
            },
            "camera": {
                "joongna_category": "9",
                "label": "카메라",
                "bunjang_category_prefix": "600300",
                "sweep_ids": ["600300001"],
                "models": expand(CAMS, {"exclude": CAM_EXCLUDE, "set_keywords": CAM_SET},
                                 lambda s, l: _brand_group(l)),
            },
            "golf": {
                "joongna_category": "1260",
                "label": "골프채",
                "bunjang_category_prefix": "700600",
                "sweep_ids": ["700600300"],
                "models": expand(DRIVERS, {"exclude": GOLF_EXCLUDE,
                                           "head_only_keywords": GOLF_HEAD,
                                           "variant_fields": GOLF_VARIANTS},
                                 lambda s, l: _brand_group(l)),
            },
            "console": {
                "joongna_category": "12",
                "label": "게임기",
                "bunjang_category_prefix": "600600",
                "sweep_ids": ["600600001"],
                "models": expand(CONSOLES, {"exclude": CONSOLE_EXCLUDE,
                                            "set_keywords": ["풀박", "게임", "\\+", "세트"]},
                                 lambda s, l: _brand_group(l)),
            },
            "tablet": {
                "joongna_category": "140",
                "label": "태블릿",
                "bunjang_category_prefix": "600710",
                "sweep_ids": ["600710300"],
                "models": expand(TABLETS, {"exclude": TABLET_EXCLUDE,
                                           "set_keywords": ["풀박", "\\+", "세트", "포함"]},
                                 lambda s, l: _brand_group(l)),
            },
            "phone": {
                "joongna_category": "139",
                "label": "스마트폰",
                "bunjang_category_prefix": "600700",
                "sweep_ids": ["600700001"],
                "models": expand(PHONES, {"exclude": PHONE_EXCLUDE, "set_keywords": PHONE_SET},
                                 lambda s, l: _brand_group(l)),
            },
            "laptop": {
                "joongna_category": "158",
                "label": "노트북",
                "bunjang_category_prefix": "600100",
                "sweep_ids": ["600100001"],
                "models": expand(LAPTOPS, {"exclude": LAPTOP_EXCLUDE, "set_keywords": LAPTOP_SET},
                                 lambda s, l: _brand_group(l)),
            },
            "audio": {
                "joongna_category": "1171",
                "label": "이어폰·헤드폰",
                "bunjang_category_prefix": "600500",
                "sweep_ids": ["600500010"],
                "models": expand(AUDIOS, {"exclude": AUDIO_EXCLUDE, "set_keywords": AUDIO_SET},
                                 lambda s, l: _brand_group(l)),
            },
            "watch": {
                "joongna_category": "141",
                "label": "스마트워치",
                "bunjang_category_prefix": "600720",
                "sweep_ids": ["600720100"],
                "models": expand(WATCHES, {"exclude": WATCH_EXCLUDE, "set_keywords": WATCH_SET},
                                 lambda s, l: _brand_group(l)),
            },
            "appliance": {
                "joongna_category": "7",
                "label": "생활가전",
                "bunjang_category_prefix": "610500",
                "sweep_ids": ["610500005"],
                "models": expand(APPLIANCES, {"exclude": APPLIANCE_EXCLUDE,
                                              "set_keywords": ["\\+", "세트", "일괄"]},
                                 lambda s, l: _brand_group(l)),
            },
            "monitor": {
                "joongna_category": "160",
                "label": "모니터",
                "bunjang_category_prefix": "600100",
                "sweep_ids": ["600100007"],
                "models": expand(MONITORS, {"exclude": MONITOR_EXCLUDE,
                                            "set_keywords": ["\\+", "세트", "일괄"]},
                                 lambda s, l: _brand_group(l)),
            },
            "cpu": {
                "joongna_category": "161",
                "label": "CPU",
                "bunjang_category_prefix": "600100",
                "sweep_ids": ["600100006"],
                "models": expand(CPUS, {"exclude": CPU_EXCLUDE, "set_keywords": CPU_SET},
                                 lambda s, l: _brand_group(l)),
            },
            "peripheral": {
                "joongna_category": "166",
                "label": "키보드·마우스",
                "bunjang_category_prefix": "600100",
                "sweep_ids": ["600100010", "600100011"],
                "models": expand(PERIPHERALS, {"exclude": PERIPHERAL_EXCLUDE,
                                               "set_keywords": ["\\+", "세트", "일괄"]},
                                 lambda s, l: _brand_group(l)),
            },
            "golfiron": {
                "joongna_category": "1262",
                "label": "골프 아이언",
                "bunjang_category_prefix": "700600",
                "sweep_ids": [],   # golf sweep already covers 700600300
                "models": expand(IRONS, {"exclude": IRON_EXCLUDE,
                                         "head_only_keywords": GOLF_HEAD},
                                 lambda s, l: _brand_group(l)),
            },
            "golfputter": {
                "joongna_category": "1263",
                "label": "퍼터·웨지",
                "bunjang_category_prefix": "700600",
                "sweep_ids": [],
                "models": expand(PUTTERS, {"exclude": PUTTER_EXCLUDE,
                                           "head_only_keywords": GOLF_HEAD},
                                 lambda s, l: _brand_group(l)),
            },
            "lens": {
                "joongna_category": "177",
                "label": "카메라 렌즈",
                "bunjang_category_prefix": "600300",
                "sweep_ids": ["600300004"],
                "models": expand(LENSES, {"exclude": LENS_EXCLUDE,
                                          "set_keywords": ["\\+", "세트", "일괄"]},
                                 lambda s, l: _brand_group(l)),
            },
            "filmcam": {
                "joongna_category": "174",
                "label": "필름카메라",
                "bunjang_category_prefix": "600300",
                "sweep_ids": ["600300003"],
                "models": expand(FILMCAMS, {"exclude": FILMCAM_EXCLUDE,
                                            "set_keywords": ["\\+", "세트", "일괄"]},
                                 lambda s, l: _brand_group(l)),
            },
            "actioncam": {
                "joongna_category": "175",
                "label": "액션캠·짐벌",
                "bunjang_category_prefix": "600300",
                "sweep_ids": ["600300007"],
                "models": expand(ACTIONCAMS, {"exclude": ACTIONCAM_EXCLUDE,
                                              "set_keywords": ["\\+", "세트", "일괄"]},
                                 lambda s, l: _brand_group(l)),
            },
            "camping": {
                "joongna_category": "241",
                "label": "캠핑",
                "bunjang_category_prefix": "700200",
                "sweep_ids": ["700200102"],
                "models": expand(CAMPINGS, {"exclude": CAMPING_EXCLUDE,
                                            "set_keywords": ["\\+", "세트", "일괄", "2개"]},
                                 lambda s, l: _brand_group(l)),
            },
            "bike": {
                "joongna_category": "229",
                "label": "자전거",
                "bunjang_category_prefix": "700350",
                "sweep_ids": ["700350400"],
                "models": expand(BIKES, {"exclude": BIKE_EXCLUDE,
                                         "set_keywords": ["\\+", "세트", "일괄"]},
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
