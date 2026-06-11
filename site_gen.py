"""Generate a multi-page static site from stats.json.

Pages:
  index.html          home — search box, category cards, recently detected sales
  cat-{key}.html      category price table
  m-{model_id}.html   model detail — estimate, detected sales, active listings

    python site_gen.py
"""

from __future__ import annotations
import json
from pathlib import Path

BASE = Path(__file__).parent

# ---- deployment settings ----
BASE_URL = "https://palinga.xyz"  # Cloudflare Pages 주소 (커스텀 도메인 연결 시 교체)
ADSENSE_CLIENT = "ca-pub-6840959424010586"  # 퍼즐마루와 동일 퍼블리셔
SITE_NAME = "팔린가"

CATEGORY_LABELS = {"gpu": "그래픽카드", "camera": "카메라", "golf": "골프채",
                   "console": "게임기", "tablet": "태블릿"}
BASIS_LABELS = {
    "sold": ("실거래 기준", "badge-sold"),
    "ratio": ("보정 호가 · 할인율 학습", "badge-adj"),
    "asking_low": ("보정 호가 · 하단 추정", "badge-adj"),
}

CSS = """
  :root { --ink:#1a1a1a; --muted:#777; --line:#e5e2da; --bg:#faf9f5; --accent:#0c5d56; }
  * { box-sizing:border-box; margin:0; }
  body { font-family:'Apple SD Gothic Neo','Noto Sans KR',sans-serif; background:var(--bg); color:var(--ink); line-height:1.6; }
  .wrap { max-width:880px; margin:0 auto; padding:24px 20px 80px; }
  header.site { display:flex; align-items:baseline; gap:14px; padding-bottom:14px; border-bottom:2px solid var(--ink); margin-bottom:18px; }
  header.site a.logo { font-size:22px; font-weight:700; color:var(--ink); text-decoration:none; }
  header.site .tag { font-size:13px; color:var(--muted); }
  .crumb { font-size:13px; color:var(--muted); margin-bottom:18px; }
  .crumb a { color:var(--accent); text-decoration:none; }
  table { width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); border-radius:10px; overflow:hidden; }
  th,td { padding:10px 14px; text-align:left; font-size:14px; border-bottom:1px solid var(--line); }
  th { background:#f3f1ea; font-weight:600; color:#555; }
  tr:last-child td { border-bottom:none; }
  td a { color:var(--ink); text-decoration:none; font-weight:600; }
  td a:hover { color:var(--accent); }
  .num { text-align:right; font-variant-numeric:tabular-nums; }
  .badge { display:inline-block; font-size:11px; padding:1px 8px; border-radius:10px; margin-left:6px; vertical-align:1px; white-space:nowrap; }
  .badge-sold { background:#e8f0ef; color:var(--accent); }
  .badge-adj { background:#f5ecd9; color:#8a6310; }
  h1 { font-size:24px; margin-bottom:4px; } h2 { font-size:18px; margin:28px 0 10px; }
  .sub { color:var(--muted); font-size:14px; margin-bottom:22px; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:14px; margin-bottom:8px; }
  .card { background:#fff; border:1px solid var(--line); border-radius:12px; padding:18px; text-decoration:none; color:var(--ink); }
  .card:hover { border-color:var(--accent); }
  .card b { font-size:17px; } .card .meta { font-size:13px; color:var(--muted); }
  .search { position:relative; margin-bottom:26px; }
  .search input { width:100%; padding:12px 16px; font-size:16px; border:1.5px solid var(--line); border-radius:10px; background:#fff; }
  .search input:focus { outline:none; border-color:var(--accent); }
  .hits { position:absolute; left:0; right:0; top:100%; background:#fff; border:1px solid var(--line); border-radius:0 0 10px 10px; z-index:5; display:none; }
  .hits a { display:block; padding:10px 16px; color:var(--ink); text-decoration:none; font-size:14px; border-bottom:1px solid var(--line); }
  .hits a:hover { background:#f3f1ea; }
  .price-big { font-size:30px; font-weight:700; color:var(--accent); }
  .range { font-size:13px; color:var(--muted); }
  .note { margin-top:48px; font-size:12px; color:var(--muted); border-top:1px solid var(--line); padding-top:14px; }
"""

SHELL = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — 팔린가</title>
<meta name="description" content="{desc}">
<meta name="google-site-verification" content="c8ryxpEL18CTs-KrbwPDrGwoCODWrrW_unRzl1wVslA">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{title} — 팔린가">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
{adsense}<style>{css}</style>
</head>
<body>
<div class="wrap">
  <header class="site"><a class="logo" href="index.html">팔린가</a><span class="tag">중고 실거래가 · {as_of} 기준</span></header>
  {body}
  <p class="note">시세는 중앙값·사분위 기준. "보정 호가"는 거래 표본 부족 시 호가를 체결 할인율(학습값) 또는
  분포 하단으로 보정한 추정치이며, 거래 표본이 쌓이면 자동으로 실거래 기준으로 전환됩니다.
  세트·부분 매물은 통계에서 제외. 거래완료는 스냅샷 추적 추정값으로 실제 체결가와 다를 수 있습니다.
  ↗ 링크는 번개장터 원본 매물로 연결됩니다 — 직접 확인해보세요 (판매완료·삭제된 매물은 열리지 않을 수 있습니다).</p>
  <p class="note" style="border-top:none;padding-top:0">
    <a href="about.html" style="color:inherit">서비스 소개</a> ·
    <a href="privacy.html" style="color:inherit">개인정보처리방침</a> ·
    <a href="terms.html" style="color:inherit">이용약관</a> ·
    <a href="guides.html" style="color:inherit">중고 거래 가이드</a> ·
    문의 kcm0127@gmail.com</p>
</div>
{script}
</body>
</html>
"""

ADSENSE_SNIPPET = ('<script async src="https://pagead2.googlesyndication.com/pagead/js/'
                   'adsbygoogle.js?client={client}" crossorigin="anonymous"></script>\n')

ABOUT_BODY = """
  <div class="crumb"><a href="index.html">홈</a> › 서비스 소개</div>
  <h1>팔린가는 이런 서비스입니다</h1>
  <p class="sub">호가가 아닌, 실제로 팔린 가격을 보여주는 중고 시세 서비스</p>
  <p style="font-size:15px;max-width:640px">중고 거래에서 가장 어려운 질문은 "이 물건의 적정가가 얼마인가"입니다.
  중고 플랫폼에서 보이는 가격은 판매자가 부른 호가일 뿐, 실제 체결 가격과는 차이가 있습니다.
  팔린가는 중고 매물을 매일 관찰해 거래가 완료된 것으로 추정되는 매물의 마지막 가격을 수집하고,
  모델별 중앙값과 정상 거래 범위로 정리해 보여줍니다.</p>
  <h2>시세 산정 방식</h2>
  <p style="font-size:15px;max-width:640px">실거래 추정 표본이 충분한 모델은 실거래 중앙값을,
  표본이 부족한 모델은 호가에 체결 할인율을 적용한 보정값을 표시하며, 산정 근거를 배지로 구분해
  투명하게 공개합니다. 모든 매물에는 원본 링크가 있어 데이터를 직접 검증할 수 있습니다.</p>
  <h2>데이터 출처와 한계</h2>
  <p style="font-size:15px;max-width:640px">데이터는 공개된 중고 매물 정보를 집계한 것이며,
  원문은 저장·재게시하지 않고 통계값만 제공합니다. 거래완료는 매물 상태 변화로 추정한 값이라
  실제 체결가와 다를 수 있으며, 시세는 참고용 정보로 거래의 책임은 거래 당사자에게 있습니다.</p>"""

PRIVACY_BODY = """
  <div class="crumb"><a href="index.html">홈</a> › 개인정보처리방침</div>
  <h1>개인정보처리방침</h1>
  <p class="sub">시행일: 2026-06-11</p>
  <p style="font-size:15px;max-width:640px">팔린가(이하 "사이트")는 회원가입 없이 이용하는 정보 서비스로,
  이용자의 개인정보를 직접 수집·저장하지 않습니다.</p>
  <h2>1. 수집하는 정보</h2>
  <p style="font-size:15px;max-width:640px">사이트는 이름, 이메일, 연락처 등 개인 식별 정보를 수집하지 않습니다.
  서비스 개선을 위해 익명화된 방문 통계가 수집될 수 있습니다.</p>
  <h2>2. 광고와 쿠키</h2>
  <p style="font-size:15px;max-width:640px">사이트는 Google 애드센스 광고를 게재할 수 있습니다.
  Google을 포함한 제3자 광고 사업자는 쿠키를 사용해 이용자의 이전 방문 기록에 기반한 광고를 제공할 수 있습니다.
  이용자는 <a href="https://www.google.com/settings/ads">Google 광고 설정</a>에서 맞춤 광고를 비활성화할 수 있으며,
  <a href="https://www.aboutads.info">www.aboutads.info</a>에서 제3자 광고 쿠키 사용을 거부할 수 있습니다.</p>
  <h2>3. 매물 데이터</h2>
  <p style="font-size:15px;max-width:640px">사이트에 표시되는 매물 정보는 공개된 중고 거래 플랫폼의 정보를
  통계 목적으로 집계한 것이며, 판매자의 개인정보(연락처, 정확한 위치 등)는 수집·표시하지 않습니다.</p>
  <h2>4. 문의</h2>
  <p style="font-size:15px;max-width:640px">개인정보 관련 문의: kcm0127@gmail.com</p>"""

TERMS_BODY = """
  <div class="crumb"><a href="index.html">홈</a> › 이용약관</div>
  <h1>이용약관</h1>
  <p class="sub">시행일: 2026-06-11</p>
  <p style="font-size:15px;max-width:640px">본 약관은 팔린가(이하 "사이트")가 제공하는 중고 시세 정보 서비스의
  이용 조건을 규정합니다. 사이트를 이용함으로써 이용자는 본 약관에 동의한 것으로 봅니다.</p>
  <h2>1. 서비스의 성격</h2>
  <p style="font-size:15px;max-width:640px">사이트가 제공하는 모든 시세는 공개된 중고 매물 정보를 통계적으로
  추정한 <b>참고용 정보</b>입니다. 실제 거래 가격을 보장하지 않으며, 거래의 판단과 책임은 전적으로 이용자에게
  있습니다.</p>
  <h2>2. 데이터의 한계</h2>
  <p style="font-size:15px;max-width:640px">거래완료 여부는 매물 상태 변화로 추정하므로 실제 체결가와 다를 수
  있고, 표본이 적은 모델은 정확도가 낮을 수 있습니다. 사이트는 정보의 정확성·완전성을 보증하지 않습니다.</p>
  <h2>3. 면책</h2>
  <p style="font-size:15px;max-width:640px">이용자가 사이트 정보를 근거로 한 거래에서 발생한 손해에 대해
  사이트는 책임을 지지 않습니다. 외부 링크(중고 거래 플랫폼 등)의 내용과 거래에 대해서도 책임지지 않습니다.</p>
  <h2>4. 문의</h2>
  <p style="font-size:15px;max-width:640px">kcm0127@gmail.com</p>"""

_P = 'style="font-size:15px;max-width:660px;line-height:1.8"'
GUIDES = [
  {"slug": "guide-used-price", "title": "중고 시세, 호가와 실거래가는 왜 다를까",
   "desc": "중고 거래에서 호가와 실제 체결가가 차이 나는 이유와 적정가 찾는 법",
   "body": f"""
  <p {_P}>중고 거래를 처음 할 때 가장 헷갈리는 것이 \"이 물건 얼마가 적정가지?\"라는 질문입니다.
  중고 플랫폼에서 보이는 가격은 대부분 판매자가 부른 <b>호가</b>입니다. 호가는 판매자의 희망 사항일 뿐,
  실제로 그 가격에 팔렸다는 보장이 없습니다. 인기 없는 매물은 몇 주째 같은 가격에 올라와 있기도 하고,
  반대로 시세보다 싼 매물은 올라온 지 몇 분 만에 거래완료로 바뀝니다.</p>
  <p {_P}>그래서 진짜 시세를 알려면 \"팔린 가격\"을 봐야 합니다. 하지만 대부분의 플랫폼은 거래완료된
  매물의 가격을 따로 모아 보여주지 않습니다. 팔린가는 매일 활성 매물을 관찰해, 사라진(거래된 것으로 추정되는)
  매물의 마지막 가격을 모아 모델별 실거래 추정 시세를 계산합니다.</p>
  <p {_P}>적정가를 판단할 때는 평균보다 <b>중앙값</b>을 보는 것이 좋습니다. 평균은 터무니없이 비싼 매물
  한두 개에 크게 흔들리지만, 중앙값은 \"딱 가운데 가격\"이라 체감 시세에 가깝습니다. 또한 정상 거래
  범위(상·하위 25%를 제외한 구간)를 함께 보면, 내가 보려는 매물이 비싼 편인지 싼 편인지 한눈에 들어옵니다.</p>""" },
  {"slug": "guide-buy-checklist", "title": "중고 거래 안전 체크리스트",
   "desc": "중고 직거래·택배거래 사기 예방과 상태 확인 체크리스트",
   "body": f"""
  <p {_P}>중고 거래에서 가장 중요한 것은 시세보다 <b>사기 예방</b>입니다. 시세보다 유난히 싼 매물은
  의심부터 하는 것이 안전합니다. 판매자에게 추가 사진을 실시간으로 요청했을 때 거부하거나, 보내온 사진이
  인터넷에서 검색되는 사진이라면 거래를 중단하세요.</p>
  <p {_P}>택배 거래라면 안전결제(에스크로)를 이용하는 것이 원칙입니다. 판매자가 안전결제를 거부하고
  계좌이체만 고집한다면 위험 신호입니다. 직거래라면 사람이 많은 공공장소에서, 낮 시간에 만나는 것이 좋습니다.</p>
  <p {_P}>상태 확인은 카테고리마다 다르지만 공통 원칙이 있습니다. 전원이 들어오는지, 외관 손상이 사진과
  일치하는지, 구성품(박스·충전기·보증서)이 설명대로인지 그 자리에서 확인하세요. 영수증이나 보증서가 있으면
  정품 여부와 남은 보증 기간을 알 수 있어 가격 협상에도 유리합니다.</p>""" },
  {"slug": "guide-gpu", "title": "중고 그래픽카드 구매 가이드",
   "desc": "중고 GPU 채굴 이력 확인, 테스트 방법, 변형 모델 구분법",
   "body": f"""
  <p {_P}>그래픽카드는 중고 거래가 가장 활발한 PC 부품이지만, 상태 편차도 가장 큽니다. 게임용으로 가볍게 쓴
  카드와 채굴장에서 24시간 돌아간 카드는 수명이 다릅니다. 채굴 이력을 완전히 확인하긴 어렵지만, 같은 모델을
  여러 장 파는 판매자, 백플레이트 나사의 개봉 흔적, 유난히 깨끗하게 세척된 기판은 의심 신호입니다.</p>
  <p {_P}>직거래라면 그 자리에서 테스트를 요청하세요. GPU-Z로 모델·바이오스가 정품과 일치하는지, 부하
  테스트로 온도와 팬 소음이 정상인지 10분이면 확인됩니다. 테스트를 거부하면 거르는 것이 맞습니다.</p>
  <p {_P}>변형 모델 구분도 중요합니다. RTX 4070, 4070 SUPER, 4070 Ti, 4070 Ti SUPER는 이름이 비슷하지만
  성능과 시세가 모두 다릅니다. 팔린가는 이 변형들을 별도 모델로 분리해 시세를 집계합니다. 세대 교체기에는
  신품 할인가가 중고가를 추월하기도 하니, 중고가가 신품의 80%를 넘으면 신품도 함께 비교해 보세요.</p>""" },
  {"slug": "guide-camera", "title": "중고 카메라·렌즈 구매 가이드",
   "desc": "중고 카메라 셔터수·센서·렌즈 곰팡이 확인 체크리스트",
   "body": f"""
  <p {_P}>카메라 바디에서 먼저 확인할 것은 셔터수입니다. 자동차 주행거리에 해당하며, 보급기는 약 10만 컷,
  플래그십은 30만 컷 이상이 설계 수명입니다. 판매자에게 최근 촬영 원본(JPG) 한 장을 요청하면 셔터수 확인
  사이트로 조회할 수 있습니다.</p>
  <p {_P}>센서는 조리개를 F16 이상으로 조이고 밝은 벽이나 하늘을 찍어 확인합니다. 같은 위치에 반복되는 점이
  있으면 먼지나 데드픽셀입니다. 먼지는 청소로 해결되지만 데드픽셀은 수리 대상이라 가격에 반영해야 합니다.</p>
  <p {_P}>렌즈는 곰팡이와 먼지가 핵심입니다. 플래시를 켜고 비스듬히 비추면 안쪽의 곰팡이(거미줄 무늬)와 헤이즈가
  보입니다. 초점 링과 줌 링이 부드럽게 돌아가는지, 조리개 날개에 기름이 새지 않았는지도 확인하세요.</p>""" },
  {"slug": "guide-console", "title": "중고 게임기 구매 가이드",
   "desc": "닌텐도 스위치·PS5 중고 구매 시 확인할 것 — 변형 모델, 상태, 구성품",
   "body": f"""
  <p {_P}>게임기는 세대와 변형이 많아 모델 구분이 먼저입니다. 닌텐도 스위치만 해도 초기형, 배터리 개선형,
  OLED, 라이트, 그리고 스위치 2까지 가격대가 크게 다릅니다. 제목만 믿지 말고 본체 모델명(뒷면 각인)으로
  확인하세요.</p>
  <p {_P}>상태 확인은 화면 번인(OLED), 조이콘 쏠림(드리프트), 도크 정상 출력이 핵심입니다. 직거래라면 게임을
  실행해 스틱을 가만히 뒀을 때 캐릭터가 저절로 움직이는지 보면 드리프트를 바로 알 수 있습니다.</p>
  <p {_P}>구성품도 가격에 큰 영향을 줍니다. 정품 어댑터·도크·조이콘이 모두 있는 풀박스와 본체만 있는 매물은
  시세가 다릅니다. 팔린가는 게임 타이틀이 끼워진 세트 매물을 통계에서 분리해, 본체 단품 기준 시세를 보여줍니다.</p>""" },
]



def won(v) -> str:
    return f"{v:,}원" if v is not None else "—"


def badge(basis: str) -> str:
    label, cls = BASIS_LABELS.get(basis, ("표본 없음", "badge-adj"))
    return f'<span class="badge {cls}">{label}</span>'


def model_rows(models: dict, ids: list[str]) -> str:
    rows = []
    for mid in ids:
        m = models[mid]
        if not m["stats"]:
            rows.append(
                f"<tr><td><a href='m-{mid}.html'>{m['label']}</a>"
                f"<span class='badge badge-adj'>수집 대기</span></td>"
                f"<td class='num'>—</td><td class='num'>—</td>"
                f"<td class='num'>0건</td><td class='num'>0건</td></tr>"
            )
            continue
        st = m["stats"]
        rows.append(
            f"<tr><td><a href='m-{mid}.html'>{m['label']}</a>{badge(m['basis'])}</td>"
            f"<td class='num'><b>{won(m['estimate'])}</b></td>"
            f"<td class='num'>{won(st['q1'])} ~ {won(st['q3'])}</td>"
            f"<td class='num'>{m['active_count']}건</td>"
            f"<td class='num'>{len(m['sold'])}건</td></tr>"
        )
    return "\n".join(rows)


TABLE_HEAD = ("<thead><tr><th>모델</th><th class='num'>시세 추정</th>"
              "<th class='num'>정상 범위</th><th class='num'>활성 매물</th>"
              "<th class='num'>거래 감지</th></tr></thead>")


def price_chart(series: list[dict], sold: list[dict]) -> str:
    """Inline SVG: daily asking-median line + sold-price dots."""
    pts = [(s["date"], s["median"]) for s in series]
    sold_pts = [(s["sold_date"], s["price"]) for s in sold
                if not s.get("is_set") and not s.get("head_only")]
    if not pts:
        return ""
    dates = sorted({d for d, _ in pts} | {d for d, _ in sold_pts})
    vals = [v for _, v in pts] + [v for _, v in sold_pts]
    lo, hi = min(vals), max(vals)
    pad = max((hi - lo) * 0.15, hi * 0.03, 1)
    lo, hi = lo - pad, hi + pad
    W, H, ML, MB = 640, 170, 70, 24
    def x(d): return ML + (dates.index(d) * (W - ML - 16) / max(len(dates) - 1, 1))
    def y(v): return 8 + (H - MB - 8) * (1 - (v - lo) / (hi - lo))
    poly = " ".join(f"{x(d):.1f},{y(v):.1f}" for d, v in pts)
    line = (f"<polyline points='{poly}' fill='none' stroke='#0c5d56' stroke-width='2'/>"
            if len(pts) > 1 else "")
    dots = "".join(f"<circle cx='{x(d):.1f}' cy='{y(v):.1f}' r='3.5' fill='#0c5d56'/>"
                   f"<title>{d} 호가 중앙값 {v:,}원</title>" for d, v in pts)
    sold_dots = "".join(f"<circle cx='{x(d):.1f}' cy='{y(v):.1f}' r='4' fill='#c47912'/>"
                        for d, v in sold_pts)
    labels = "".join(f"<text x='{x(d):.1f}' y='{H - 6}' font-size='11' fill='#999' "
                     f"text-anchor='middle'>{d[5:]}</text>" for d in dates)
    ticks = "".join(
        f"<text x='{ML - 8}' y='{y(v):.1f}' font-size='11' fill='#999' text-anchor='end' "
        f"dominant-baseline='middle'>{round(v / 10000):,}만</text>"
        f"<line x1='{ML}' x2='{W - 16}' y1='{y(v):.1f}' y2='{y(v):.1f}' stroke='#eee'/>"
        for v in (lo + pad, (lo + hi) / 2, hi - pad))
    return f"""
  <h2>가격 추이</h2>
  <div style="background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px">
    <svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="가격 추이 차트">
      {ticks}{line}{dots}{sold_dots}{labels}
    </svg>
    <div style="font-size:12px;color:var(--muted)">
      <span style="color:#0c5d56">●</span> 일별 호가 중앙값 &nbsp;
      <span style="color:#c47912">●</span> 감지된 거래
    </div>
  </div>"""


def main() -> None:
    data = json.loads((BASE / "stats.json").read_text(encoding="utf-8"))
    models = data["models"]
    as_of = data["as_of"]
    adsense = ADSENSE_SNIPPET.format(client=ADSENSE_CLIENT) if ADSENSE_CLIENT else ""

    def render(name: str, title: str, desc: str, body: str, script: str = "") -> str:
        return SHELL.format(title=title, desc=desc, css=CSS, as_of=as_of, body=body,
                            script=script, adsense=adsense,
                            canonical=f"{BASE_URL.rstrip('/')}/{name}")

    by_cat: dict[str, list[str]] = {}
    for mid, m in models.items():
        by_cat.setdefault(m["category"], []).append(mid)

    pages: dict[str, str] = {}

    # --- home ---
    cards = "".join(
        f"<a class='card' href='cat-{ck}.html'><b>{CATEGORY_LABELS.get(ck, ck)}</b><br>"
        f"<span class='meta'>{len(ids)}개 모델 · 활성 매물 {sum(models[i]['active_count'] for i in ids)}건</span></a>"
        for ck, ids in by_cat.items()
    )
    recent_sales = sorted(
        (s | {"model_label": models[s['model_id']]['label'], "mid": s['model_id']}
         for m in models.values() for s in m["sold"]),
        key=lambda s: s["sold_date"], reverse=True)[:8]
    sales_rows = "".join(
        f"<tr><td>{s['sold_date']}</td><td><a href='m-{s['mid']}.html'>{s['model_label']}</a></td>"
        f"<td><a href='https://m.bunjang.co.kr/products/{s['pid']}' target='_blank' rel='noopener' "
        f"style='font-weight:400'>{s['name'][:40]} ↗</a></td><td class='num'>{won(s['price'])}</td></tr>"
        for s in recent_sales
    ) or "<tr><td colspan='4' style='color:#999'>아직 감지된 거래가 없습니다</td></tr>"

    search_index = [
        {"label": m["label"], "href": f"m-{mid}.html",
         "cat": CATEGORY_LABELS.get(m["category"], "")}
        for mid, m in models.items()
    ]
    search_script = f"""<script>
const IDX = {json.dumps(search_index, ensure_ascii=False)};
const inp = document.getElementById('q'), hits = document.getElementById('hits');
inp.addEventListener('input', () => {{
  const q = inp.value.trim().toLowerCase();
  if (!q) {{ hits.style.display = 'none'; return; }}
  const found = IDX.filter(m => m.label.toLowerCase().includes(q)).slice(0, 8);
  hits.innerHTML = found.map(m =>
    `<a href="${{m.href}}">${{m.label}} <span style="color:#999;font-size:12px">${{m.cat}}</span></a>`).join('')
    || '<a>검색 결과 없음</a>';
  hits.style.display = 'block';
}});
document.addEventListener('click', e => {{ if (!e.target.closest('.search')) hits.style.display = 'none'; }});
</script>"""

    guide_cards = "".join(
        "<a class='card' href='" + g['slug'] + ".html'><b>" + g['title']
        + "</b><br><span class='meta'>" + g['desc'] + "</span></a>"
        for g in GUIDES)
    home_body = f"""
  <h1>이 물건, 실제로 얼마에 팔렸을까?</h1>
  <p class="sub">호가가 아닌 실거래 추정가로 보는 중고 시세.</p>
  <div class="search"><input id="q" type="search" placeholder="모델명 검색 — 예: 4070, A7M4, 스텔스" autocomplete="off"><div class="hits" id="hits"></div></div>
  <div class="cards">{cards}</div>
  <h2>최근 감지된 거래</h2>
  <table><thead><tr><th>날짜</th><th>모델</th><th>매물명</th><th class="num">최종 관측가</th></tr></thead>
  <tbody>{sales_rows}</tbody></table>
  <h2>중고 거래 가이드</h2>
  <div class="cards">{guide_cards}</div>"""
    pages["index.html"] = render("index.html", "중고 실거래가 시세",
                                 "그래픽카드, 카메라, 골프채 중고 실거래가 시세 — 호가가 아닌 실제로 팔린 가격",
                                 home_body, search_script)
    pages["about.html"] = render("about.html", "서비스 소개",
                                 "팔린가 서비스 소개 — 중고 실거래가 시세 산정 방식과 데이터 출처", ABOUT_BODY)
    pages["privacy.html"] = render("privacy.html", "개인정보처리방침",
                                   "팔린가 개인정보처리방침", PRIVACY_BODY)
    pages["terms.html"] = render("terms.html", "이용약관", "팔린가 이용약관", TERMS_BODY)
    guide_links = "".join(
        "<li style='margin:8px 0'><a href='" + g['slug'] + ".html'>" + g['title']
        + "</a> <span style='color:var(--muted);font-size:13px'>— " + g['desc'] + "</span></li>"
        for g in GUIDES)
    guides_index_body = (
        "<div class='crumb'><a href='index.html'>홈</a> › 중고 거래 가이드</div>"
        "<h1>중고 거래 가이드</h1>"
        "<p class='sub'>시세를 더 잘 활용하는 법과 안전 거래 노하우.</p>"
        "<ul style='list-style:none;padding:0'>" + guide_links + "</ul>")
    pages['guides.html'] = render('guides.html', '중고 거래 가이드',
                                  '중고 시세 활용법과 안전 거래 가이드 모음', guides_index_body)
    for g in GUIDES:
        gb = ("<div class='crumb'><a href='index.html'>홈</a> › <a href='guides.html'>가이드</a> › "
              + g['title'] + "</div><h1>" + g['title'] + "</h1>" + g['body'])
        pages[g['slug'] + '.html'] = render(g['slug'] + '.html', g['title'], g['desc'], gb)

    # --- category pages ---
    for ck, ids in by_cat.items():
        label = CATEGORY_LABELS.get(ck, ck)
        # group by series/brand (preserve catalog order of first appearance);
        # inside a group: models with data first, 수집 대기 at the bottom
        groups: dict[str, list[str]] = {}
        for mid in ids:
            groups.setdefault(models[mid].get("group") or "기타", []).append(mid)
        sections_html = []
        for gname, gids in groups.items():
            gids = sorted(gids, key=lambda i: (models[i]["stats"] is None,
                                               -models[i]["active_count"]))
            sections_html.append(
                f"<h2>{gname}</h2>\n  <table>{TABLE_HEAD}"
                f"<tbody>{model_rows(models, gids)}</tbody></table>")
        body = f"""
  <div class="crumb"><a href="index.html">홈</a> › {label}</div>
  <h1>{label} 시세표</h1>
  <p class="sub">모델을 클릭하면 거래 내역과 활성 매물을 볼 수 있습니다.</p>
  {chr(10).join(sections_html)}"""
        pages[f"cat-{ck}.html"] = render(f"cat-{ck}.html", f"{label} 중고 시세표",
                                         f"{label} 모델별 중고 실거래가 시세표", body)

    # --- model pages ---
    for mid, m in models.items():
        st = m["stats"]
        cat_label = CATEGORY_LABELS.get(m["category"], "")
        if not st:
            body = f"""
  <div class="crumb"><a href="index.html">홈</a> › <a href="cat-{m['category']}.html">{cat_label}</a> › {m['label']}</div>
  <h1>{m['label']} <span class="badge badge-adj">수집 대기</span></h1>
  <p class="sub">아직 수집된 매물이 없습니다. 수집기가 돌기 시작하면 시세가 표시됩니다.</p>"""
            pages[f"m-{mid}.html"] = render(f"m-{mid}.html", f"{m['label']} 중고 시세",
                                            f"{m['label']} 중고 실거래가 — 수집 대기 중", body)
            continue
        def listing_link(rec: dict) -> str:
            url = rec.get("url") or f"https://m.bunjang.co.kr/products/{rec['pid']}"
            return (f"<a href='{url}' target='_blank' rel='noopener' "
                    f"style='font-weight:400'>{rec['name'][:48]} ↗</a>")

        sold_rows = "".join(
            f"<tr><td>{s['sold_date']}</td><td>{listing_link(s)}</td>"
            f"<td class='num'>{won(s['price'])}</td>"
            f"<td>{'세트' if s['is_set'] else ('헤드만' if s['head_only'] else '단품')}</td></tr>"
            for s in m["sold"]
        ) or "<tr><td colspan='4' style='color:#999'>아직 감지된 거래가 없습니다 — 스냅샷이 쌓이면 표시됩니다</td></tr>"
        active_rows = "".join(
            f"<tr><td>{listing_link(r)}</td><td class='num'>{won(r['price'])}</td>"
            f"<td class='num'>{r['num_faved']}</td>"
            f"<td>{'세트' if r.get('is_set') else ('헤드만' if r.get('head_only') else '단품')}</td></tr>"
            for r in m["active_sample"][:12]
        )
        body = f"""
  <div class="crumb"><a href="index.html">홈</a> › <a href="cat-{m['category']}.html">{cat_label}</a> › {m['label']}</div>
  <h1>{m['label']} {badge(m['basis'])}</h1>
  <div style="margin:10px 0 4px"><span class="price-big">{won(m['estimate'])}</span>
    <span class="range">&nbsp; 정상 범위 {won(st['q1'])} ~ {won(st['q3'])} · 표본 {st['n']}건</span></div>
  <p class="sub">호가 중앙값 {won(m['asking_median'])} · 활성 매물 {m['active_count']}건</p>
  {price_chart(m.get('series', []), m['sold'])}
  <h2>감지된 거래</h2>
  <table><thead><tr><th>날짜</th><th>매물명</th><th class="num">최종 관측가</th><th>구성</th></tr></thead>
  <tbody>{sold_rows}</tbody></table>
  <h2>현재 활성 매물</h2>
  <table><thead><tr><th>매물명</th><th class="num">호가</th><th class="num">찜</th><th>구성</th></tr></thead>
  <tbody>{active_rows}</tbody></table>"""
        pages[f"m-{mid}.html"] = render(f"m-{mid}.html", f"{m['label']} 중고 시세",
                                        f"{m['label']} 중고 실거래가 시세 — 추정 {won(m['estimate'])}, "
                                        f"정상 범위 {won(st['q1'])}~{won(st['q3'])}", body)

    for name, html in pages.items():
        (BASE / name).write_text(html, encoding="utf-8")

    # --- robots.txt & sitemap.xml ---
    base = BASE_URL.rstrip("/")
    (BASE / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
    urls = "\n".join(f"  <url><loc>{base}/{n}</loc><lastmod>{as_of}</lastmod></url>"
                     for n in sorted(pages))
    (BASE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n</urlset>\n", encoding="utf-8")
    print(f"generated {len(pages)} pages + robots.txt + sitemap.xml")


if __name__ == "__main__":
    main()
