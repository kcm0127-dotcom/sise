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

CATEGORY_LABELS = {"gpu": "그래픽카드", "camera": "카메라", "golf": "골프 드라이버",
                   "console": "게임기", "tablet": "태블릿", "phone": "스마트폰",
                   "laptop": "노트북", "audio": "이어폰·헤드폰", "watch": "스마트워치",
                   "appliance": "생활가전", "monitor": "모니터", "cpu": "CPU",
                   "peripheral": "키보드·마우스", "golfiron": "골프 아이언",
                   "golfputter": "퍼터·웨지", "lens": "카메라 렌즈",
                   "filmcam": "필름카메라", "actioncam": "액션캠·짐벌",
                   "camping": "캠핑", "bike": "자전거"}

# 홈 화면 카테고리 카드 묶음 (표시 순서대로)
CATEGORY_GROUPS = [
    ("모바일·웨어러블", ["phone", "tablet", "watch", "audio"]),
    ("PC·게임", ["gpu", "cpu", "laptop", "monitor", "peripheral", "console"]),
    ("카메라·영상", ["camera", "lens", "filmcam", "actioncam"]),
    ("골프", ["golf", "golfiron", "golfputter"]),
    ("생활·취미", ["appliance", "camping", "bike"]),
]
BASIS_LABELS = {
    "sold": ("실거래 기준", "badge-sold"),
    "ratio": ("보정 호가 · 할인율 학습", "badge-adj"),
    "asking_low": ("보정 호가 · 하단 추정", "badge-adj"),
}

CSS = """
  :root { --bg:#f2f4f6; --card:#fff; --ink:#191f28; --sub2:#4e5968; --muted:#8b95a1;
          --line:#e5e8eb; --accent:#ff6f0f; --accent-bg:#fff1e7;
          --orange:#f76808; --orange-bg:#fff3e9; --green:#149a5b; --green-bg:#e7f7ee; }
  * { box-sizing:border-box; margin:0; }
  body { font-family:'Pretendard Variable',Pretendard,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;
         background:var(--bg); color:var(--ink); line-height:1.6; -webkit-font-smoothing:antialiased; }
  .wrap { max-width:960px; margin:0 auto; padding:18px 20px 80px; }
  header.site { position:sticky; top:0; z-index:30; background:rgba(255,255,255,.88);
    backdrop-filter:blur(14px); -webkit-backdrop-filter:blur(14px); border-bottom:1px solid var(--line); }
  header.site .hrow { max-width:960px; margin:0 auto; padding:13px 20px; display:flex; align-items:center; gap:14px; }
  header.site a.logo { font-size:21px; font-weight:800; letter-spacing:-.5px; color:var(--ink); text-decoration:none; }
  header.site a.logo span { color:var(--accent); }
  .asof { font-size:12px; color:var(--muted); font-weight:500; }
  header.site nav { margin-left:auto; display:flex; gap:2px; }
  header.site nav a { font-size:14px; font-weight:600; color:var(--sub2); text-decoration:none;
    padding:7px 11px; border-radius:10px; }
  header.site nav a:hover { background:var(--bg); color:var(--ink); }
  .crumb { font-size:13px; color:var(--muted); margin-bottom:14px; }
  .crumb a { color:var(--muted); text-decoration:none; }
  .crumb a:hover { color:var(--accent); }
  .search { position:relative; margin:6px 0 26px; }
  .search input { width:100%; padding:15px 18px 15px 48px; font-size:16px; border:1.5px solid transparent;
    border-radius:16px; background:var(--card); box-shadow:0 1px 4px rgba(2,32,71,.07);
    transition:border-color .15s, box-shadow .15s; color:var(--ink); }
  .search input::placeholder { color:var(--muted); }
  .search input:focus { outline:none; border-color:var(--accent); box-shadow:0 4px 18px rgba(255,111,15,.18); }
  .search .ico { position:absolute; left:17px; top:50%; transform:translateY(-50%); color:var(--muted); pointer-events:none; }
  .hits { position:absolute; left:0; right:0; top:calc(100% + 8px); background:var(--card);
    border-radius:16px; box-shadow:0 10px 34px rgba(2,32,71,.16); z-index:25; display:none; overflow:hidden; }
  .hits a { display:flex; justify-content:space-between; align-items:center; gap:10px; padding:13px 18px;
    color:var(--ink); text-decoration:none; font-size:15px; font-weight:600; }
  .hits a small { color:var(--muted); font-weight:500; font-size:12px; }
  .hits a:hover { background:var(--accent-bg); }
  h1 { font-size:26px; font-weight:800; letter-spacing:-.02em; line-height:1.3; margin-bottom:6px; }
  h2 { font-size:19px; font-weight:700; letter-spacing:-.01em; margin:34px 0 12px; scroll-margin-top:74px; }
  h2 .cnt { color:var(--muted); font-weight:600; font-size:14px; }
  .chips { display:flex; flex-wrap:wrap; gap:8px; margin:2px 0 6px; }
  .chip { font-size:13px; font-weight:600; color:var(--sub2); background:var(--card); border-radius:999px;
    padding:8px 14px; text-decoration:none; box-shadow:0 1px 3px rgba(2,32,71,.06); }
  .chip:hover { color:var(--accent); background:var(--accent-bg); }
  .chip small { color:var(--muted); font-weight:500; }
  .sub { color:var(--sub2); font-size:15px; margin-bottom:20px; }
  .tbl { background:var(--card); border-radius:16px; box-shadow:0 1px 4px rgba(2,32,71,.07); overflow-x:auto; }
  table { width:100%; border-collapse:collapse; }
  th,td { padding:13px 16px; text-align:left; font-size:14px; border-bottom:1px solid var(--bg); white-space:nowrap; }
  td:first-child, th:first-child { white-space:normal; }
  th { font-size:12px; font-weight:600; color:var(--muted); }
  tr:last-child td { border-bottom:none; }
  tbody tr:hover { background:#f8fafc; }
  td a { color:var(--ink); text-decoration:none; font-weight:700; }
  td a:hover { color:var(--accent); }
  .num { text-align:right; font-variant-numeric:tabular-nums; }
  .badge { display:inline-block; font-size:11px; font-weight:700; padding:3px 9px; border-radius:999px;
    margin-left:6px; vertical-align:2px; white-space:nowrap; }
  .badge-sold { background:var(--green-bg); color:var(--green); }
  .badge-adj { background:var(--orange-bg); color:var(--orange); }
  .badge-wait { background:#eef1f4; color:var(--muted); }
  .cards { display:grid; grid-template-columns:repeat(auto-fill,minmax(210px,1fr)); gap:12px; }
  .card { background:var(--card); border-radius:16px; padding:18px 20px; text-decoration:none; color:var(--ink);
    box-shadow:0 1px 4px rgba(2,32,71,.07); transition:transform .15s, box-shadow .15s; }
  .card:hover { transform:translateY(-2px); box-shadow:0 8px 24px rgba(2,32,71,.13); }
  .card b { font-size:16px; font-weight:700; }
  .card .meta { font-size:13px; color:var(--muted); }
  .hero { padding:8px 0 2px; }
  .hero h1 { font-size:29px; }
  .price-card { background:var(--card); border-radius:20px; padding:22px 24px; margin:14px 0 4px;
    box-shadow:0 1px 4px rgba(2,32,71,.07); }
  .price-label { font-size:13px; color:var(--muted); font-weight:600; margin-bottom:2px; }
  .price-big { font-size:34px; font-weight:800; letter-spacing:-.02em; color:var(--accent); }
  .range { font-size:14px; color:var(--sub2); }
  .chartbox { background:var(--card); border-radius:16px; padding:16px; box-shadow:0 1px 4px rgba(2,32,71,.07); }
  .note { margin-top:48px; font-size:12px; color:var(--muted); border-top:1px solid var(--line); padding-top:14px; }
  @media (max-width:600px) {
    .hide-m { display:none; }
    th,td { padding:11px 12px; font-size:13px; }
    h1 { font-size:22px; } .hero h1 { font-size:24px; }
    .price-big { font-size:28px; }
    .asof { display:none; }
    header.site nav a { padding:6px 8px; font-size:13px; }
  }
"""

SHELL = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" sizes="96x96" href="/favicon-96.png">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<title>{title} — 팔린가</title>
<meta name="description" content="{desc}">
<meta name="google-site-verification" content="c8ryxpEL18CTs-KrbwPDrGwoCODWrrW_unRzl1wVslA">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{title} — 팔린가">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
{adsense}<style>{css}</style>
</head>
<body>
<header class="site"><div class="hrow">
  <a class="logo" href="index.html">팔린<span>가</span></a>
  <span class="asof">중고 실거래 시세 · {as_of} 기준</span>
  <nav><a href="guides.html">가이드</a><a href="faq.html">FAQ</a><a href="about.html">소개</a></nav>
</div></header>
<div class="wrap">
  <div class="search">
    <svg class="ico" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><line x1="20" y1="20" x2="16" y2="16"/></svg>
    <input id="q" type="search" placeholder="모델명 검색 — 예: 4070, 아이폰 15, A7M4" autocomplete="off">
    <div class="hits" id="hits"></div>
  </div>
  {body}
  <p class="note">시세는 중앙값·사분위 기준. "보정 호가"는 거래 표본 부족 시 호가를 체결 할인율(학습값) 또는
  분포 하단으로 보정한 추정치이며, 거래 표본이 쌓이면 자동으로 실거래 기준으로 전환됩니다.
  세트·부분 매물은 통계에서 제외. 거래완료는 스냅샷 추적 추정값으로 실제 체결가와 다를 수 있습니다.
  ↗ 링크는 번개장터·중고나라 원본 매물로 연결됩니다 — 직접 확인해보세요 (판매완료·삭제된 매물은 열리지 않을 수 있습니다).</p>
  <p class="note" style="border-top:none;padding-top:0">
    <a href="about.html" style="color:inherit">서비스 소개</a> ·
    <a href="privacy.html" style="color:inherit">개인정보처리방침</a> ·
    <a href="terms.html" style="color:inherit">이용약관</a> ·
    <a href="guides.html" style="color:inherit">중고 거래 가이드</a> ·
    <a href="faq.html" style="color:inherit">자주 묻는 질문</a> ·
    문의 kcm0127@gmail.com</p>
</div>
{searchjs}
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
  {"slug": "guide-phone", "title": "중고 스마트폰 구매 가이드",
   "desc": "중고 아이폰·갤럭시 구매 시 배터리 성능, 잠금 해제, 분실폰 확인법",
   "body": f"""
  <p {_P}>중고 스마트폰에서 가장 먼저 확인할 것은 <b>분실·도난 여부</b>입니다. 한국정보통신진흥협회의
  단말기자급제 사이트에서 IMEI를 조회하면 분실 신고된 기기인지 확인할 수 있습니다. 판매자에게 IMEI(설정 →
  일반 → 정보)를 미리 요청하고, 조회를 거부하면 거래하지 않는 것이 안전합니다.</p>
  <p {_P}>아이폰이라면 <b>배터리 성능 최대치</b>(설정 → 배터리 → 배터리 성능 상태)를 확인하세요. 87% 이하면
  체감 사용 시간이 짧아지고, 80% 미만은 교체 대상입니다. 배터리 교체 비용(정품 기준 10만원 안팎)을 감안해
  가격을 협상하세요. 또한 '나의 찾기'가 해제되어 있는지(활성화 잠금), 통신사 약정이나 할부금이 남아 있지 않은지
  반드시 그 자리에서 확인해야 합니다.</p>
  <p {_P}>갤럭시는 삼성 멤버스 앱의 진단 기능으로 터치·센서·카메라를 한 번에 점검할 수 있습니다. 침수 라벨,
  카메라 흔들림(OIS 고장), 화면 번인은 수리비가 크게 나오는 항목이라 직거래에서 꼭 확인하세요.
  자급제와 통신사향, 용량(128GB/256GB)에 따라 시세가 다르니 같은 모델이라도 옵션을 맞춰 비교해야 합니다.</p>""" },
  {"slug": "guide-laptop", "title": "중고 노트북·맥북 구매 가이드",
   "desc": "중고 맥북 배터리 사이클, 충격 이력, 사양 확인 체크리스트",
   "body": f"""
  <p {_P}>맥북은 <b>배터리 사이클 수</b>가 주행거리입니다. 시스템 정보 → 전원에서 확인할 수 있으며, 설계 수명은
  1,000회입니다. 300회 이하면 좋은 편, 700회를 넘으면 교체 비용을 가격에 반영하세요. M1 이후 칩은 성능 차이보다
  램(8/16GB)과 SSD 용량이 체감에 더 크게 작용하니, 같은 'M2 에어'라도 옵션을 확인해야 합니다.</p>
  <p {_P}>외관에서는 힌지 유격, 하판 나사 마모(분해 흔적), 키보드 키 빠짐, 트랙패드 클릭감을 확인하세요.
  디스플레이는 흰 화면에서 멍·잔상·백라이트 불균형을 보고, 스피커는 최대 음량에서 찢어지는 소리가 나는지
  확인합니다. 애플 공식 진단(애플 진단: 전원 켜며 D 키)을 그 자리에서 돌려보는 것도 좋습니다.</p>
  <p {_P}>윈도우 노트북은 모델명이 같아도 연식·CPU 세대가 다른 경우가 많습니다. LG 그램은 모델번호 끝자리로
  연식을 구분할 수 있으니 판매자에게 정확한 모델번호를 요청하세요. 수리 이력, 특히 메인보드 수리는 재발 위험이
  있어 감가 요인입니다. 충전기 정품 여부와 보증 잔여 기간도 함께 확인하면 협상에 유리합니다.</p>""" },
  {"slug": "guide-audio", "title": "중고 이어폰·헤드폰 구매 가이드",
   "desc": "중고 에어팟·버즈 정품 확인, 배터리, 위생 체크포인트",
   "body": f"""
  <p {_P}>에어팟은 중고 거래량이 가장 많은 품목이면서 <b>가품이 가장 많은 품목</b>이기도 합니다. 시리얼 번호를
  애플 보증 조회 사이트(checkcoverage.apple.com)에서 조회해 모델명과 보증 정보가 일치하는지 확인하세요.
  케이스와 유닛의 시리얼이 서로 다르면 부품이 섞인 제품일 수 있습니다.</p>
  <p {_P}>무선 이어폰은 배터리가 소모품입니다. 에어팟 프로 기준 새 제품은 한 번 충전에 5~6시간을 쓰지만,
  2~3년 쓴 제품은 절반 이하로 떨어진 경우가 많습니다. 판매자에게 구매 시기와 실사용 시간을 묻고, 직거래라면
  양쪽 유닛이 모두 정상 페어링되는지, 노이즈 캔슬링이 작동하는지 확인하세요.</p>
  <p {_P}>위생도 중요한 포인트입니다. 이어팁은 어차피 교체한다고 생각하고, 스피커 매시에 이물질이 끼었는지
  확인하세요. 한쪽 유닛만 파는 매물(유닛/편측 판매)은 짝을 맞추려는 수요로 가격이 따로 형성되어 있으니,
  완제품 시세와 혼동하지 마세요. 팔린가는 유닛 단품 매물을 통계에서 제외하고 완제품 기준 시세를 보여줍니다.</p>""" },
  {"slug": "guide-sell", "title": "중고로 잘 파는 법 — 가격 책정과 협상",
   "desc": "내 물건 빨리, 제값 받고 파는 가격 책정 전략",
   "body": f"""
  <p {_P}>중고 판매의 핵심은 <b>첫 가격을 잘 정하는 것</b>입니다. 너무 높게 올리면 조회수만 쌓이고 연락이 없으며,
  나중에 가격을 내려도 '오래된 매물'로 보여 더 외면받습니다. 팔린가 같은 실거래 추정 시세에서 정상 범위를 확인하고,
  빨리 팔고 싶다면 중앙값보다 약간 낮게, 시간 여유가 있다면 중앙값 수준에서 시작하는 것이 효율적입니다.</p>
  <p {_P}>매물 설명에는 구매 시기, 사용 빈도, 하자 여부, 구성품을 구체적으로 적으세요. 하자를 숨기면 거래 후
  분쟁으로 돌아옵니다. 사진은 실물을 여러 각도에서, 시리얼이나 구동 화면이 보이게 찍으면 신뢰도가 올라가
  같은 가격이라도 먼저 팔립니다.</p>
  <p {_P}>네고(가격 협상)는 미리 마지노선을 정해두면 휘둘리지 않습니다. "쿨거래 시 O원" 같은 명확한 조건이
  애매한 "네고 가능"보다 빠른 거래로 이어집니다. 시세가 계단식으로 떨어지는 신제품 출시 직후에는 며칠 차이로
  수만 원이 빠지니, 팔 계획이 있다면 신제품 발표 전에 파는 것이 유리합니다.</p>""" },
]

FAQ_ITEMS = [
  ("시세는 어떻게 계산하나요?",
   "중고 매물을 매일 수집해 전날 있던 매물이 사라지면 거래된 것으로 추정하고, 그 마지막 가격을 모아 모델별 "
   "중앙값을 계산합니다. 거래 표본이 부족한 모델은 호가에 학습된 체결 할인율을 적용하거나 호가 분포 하단으로 "
   "보정한 추정치를 표시하며, 산정 근거를 배지로 구분해 공개합니다."),
  ("실거래가와 호가는 뭐가 다른가요?",
   "호가는 판매자가 부른 희망 가격이고, 실거래가는 실제로 거래가 성사된 가격입니다. 보통 실거래가는 호가보다 "
   "낮게 형성됩니다. 팔린가는 거래완료로 추정되는 매물의 가격만 따로 모아 실거래 추정 시세를 제공합니다."),
  ("시세가 '수집 대기'로 표시되는 모델은 뭔가요?",
   "아직 해당 모델의 매물이 충분히 수집되지 않은 상태입니다. 수집은 매일 이루어지므로 보통 며칠 안에 시세가 "
   "표시되기 시작합니다."),
  ("데이터는 얼마나 자주 갱신되나요?",
   "매일 1회 전체 카테고리를 수집해 갱신합니다. 페이지 상단의 기준일이 마지막 갱신 날짜입니다."),
  ("여기 표시된 가격으로 거래할 수 있나요?",
   "팔린가의 시세는 통계적 추정치로, 참고용 정보입니다. 실제 거래 가격은 제품 상태, 구성품, 지역, 시점에 따라 "
   "달라질 수 있습니다. 매물 링크를 통해 원본을 직접 확인하고 판단하세요."),
  ("세트 매물은 시세에 포함되나요?",
   "본체에 렌즈·게임 타이틀·액세서리가 묶인 세트 매물과 골프채 헤드만 파는 매물 등은 단품 시세를 왜곡하므로 "
   "헤드라인 통계에서 제외하고 별도로 표시합니다."),
  ("원하는 모델이 없어요. 추가해줄 수 있나요?",
   "kcm0127@gmail.com 으로 모델명을 보내주시면 검토 후 추가합니다. 거래량이 일정 수준 이상인 모델 위주로 "
   "운영하고 있습니다."),
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
                f"<span class='badge badge-wait'>수집 대기</span></td>"
                f"<td class='num'>—</td><td class='num hide-m'>—</td>"
                f"<td class='num hide-m'>0건</td><td class='num'>0건</td></tr>"
            )
            continue
        st = m["stats"]
        rows.append(
            f"<tr><td><a href='m-{mid}.html'>{m['label']}</a>{badge(m['basis'])}</td>"
            f"<td class='num'><b>{won(m['estimate'])}</b></td>"
            f"<td class='num hide-m'>{won(st['q1'])} ~ {won(st['q3'])}</td>"
            f"<td class='num hide-m'>{m['active_count']}건</td>"
            f"<td class='num'>{len(m['sold'])}건</td></tr>"
        )
    return "\n".join(rows)


TABLE_HEAD = ("<thead><tr><th>모델</th><th class='num'>시세 추정</th>"
              "<th class='num hide-m'>정상 범위</th><th class='num hide-m'>활성 매물</th>"
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
    line = (f"<polyline points='{poly}' fill='none' stroke='#ff6f0f' stroke-width='2.5' "
            f"stroke-linecap='round' stroke-linejoin='round'/>"
            if len(pts) > 1 else "")
    dots = "".join(f"<circle cx='{x(d):.1f}' cy='{y(v):.1f}' r='3.5' fill='#ff6f0f'/>"
                   f"<title>{d} 호가 중앙값 {v:,}원</title>" for d, v in pts)
    sold_dots = "".join(f"<circle cx='{x(d):.1f}' cy='{y(v):.1f}' r='4' fill='#149a5b'/>"
                        for d, v in sold_pts)
    labels = "".join(f"<text x='{x(d):.1f}' y='{H - 6}' font-size='11' fill='#8b95a1' "
                     f"text-anchor='middle'>{d[5:]}</text>" for d in dates)
    ticks = "".join(
        f"<text x='{ML - 8}' y='{y(v):.1f}' font-size='11' fill='#8b95a1' text-anchor='end' "
        f"dominant-baseline='middle'>{round(v / 10000):,}만</text>"
        f"<line x1='{ML}' x2='{W - 16}' y1='{y(v):.1f}' y2='{y(v):.1f}' stroke='#f2f4f6'/>"
        for v in (lo + pad, (lo + hi) / 2, hi - pad))
    return f"""
  <h2>가격 추이</h2>
  <div class="chartbox">
    <svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="가격 추이 차트">
      {ticks}{line}{dots}{sold_dots}{labels}
    </svg>
    <div style="font-size:12px;color:var(--muted)">
      <span style="color:#ff6f0f">●</span> 일별 호가 중앙값 &nbsp;
      <span style="color:#149a5b">●</span> 감지된 거래
    </div>
  </div>"""


def main() -> None:
    data = json.loads((BASE / "stats.json").read_text(encoding="utf-8"))
    models = data["models"]
    as_of = data["as_of"]
    adsense = ADSENSE_SNIPPET.format(client=ADSENSE_CLIENT) if ADSENSE_CLIENT else ""

    # 전역 검색 (모든 페이지 헤더 아래 검색창)
    search_index = [
        {"label": m["label"], "href": f"m-{mid}.html",
         "cat": CATEGORY_LABELS.get(m["category"], "")}
        for mid, m in models.items()
    ]
    searchjs = f"""<script>
const IDX = {json.dumps(search_index, ensure_ascii=False)};
const inp = document.getElementById('q'), hits = document.getElementById('hits');
inp.addEventListener('input', () => {{
  const q = inp.value.trim().toLowerCase();
  if (!q) {{ hits.style.display = 'none'; return; }}
  const found = IDX.filter(m => m.label.toLowerCase().includes(q)).slice(0, 8);
  hits.innerHTML = found.map(m =>
    `<a href="${{m.href}}">${{m.label}} <small>${{m.cat}}</small></a>`).join('')
    || '<a>검색 결과 없음</a>';
  hits.style.display = 'block';
}});
document.addEventListener('click', e => {{ if (!e.target.closest('.search')) hits.style.display = 'none'; }});
</script>"""

    def render(name: str, title: str, desc: str, body: str, script: str = "") -> str:
        return SHELL.format(title=title, desc=desc, css=CSS, as_of=as_of, body=body,
                            script=script, adsense=adsense, searchjs=searchjs,
                            canonical=f"{BASE_URL.rstrip('/')}/{name}")

    by_cat: dict[str, list[str]] = {}
    for mid, m in models.items():
        by_cat.setdefault(m["category"], []).append(mid)

    pages: dict[str, str] = {}

    # --- home ---
    def cat_card(ck: str) -> str:
        ids = by_cat[ck]
        return (f"<a class='card' href='cat-{ck}.html'><b>{CATEGORY_LABELS.get(ck, ck)}</b><br>"
                f"<span class='meta'>{len(ids)}개 모델 · 활성 매물 "
                f"{sum(models[i]['active_count'] for i in ids)}건</span></a>")

    grouped_cks = {ck for _, cks in CATEGORY_GROUPS for ck in cks}
    leftover = [ck for ck in by_cat if ck not in grouped_cks]
    home_groups = CATEGORY_GROUPS + ([("기타", leftover)] if leftover else [])
    cat_sections = []
    for gtitle, cks in home_groups:
        cks = sorted((ck for ck in cks if ck in by_cat),
                     key=lambda ck: -sum(models[i]["active_count"] for i in by_cat[ck]))
        if not cks:
            continue
        cat_sections.append(f"<h2>{gtitle}</h2>\n  <div class='cards'>"
                            f"{''.join(cat_card(ck) for ck in cks)}</div>")
    cards = "\n  ".join(cat_sections)
    recent_sales = sorted(
        (s | {"model_label": models[s['model_id']]['label'], "mid": s['model_id']}
         for m in models.values() for s in m["sold"]),
        key=lambda s: s["sold_date"], reverse=True)[:8]
    sales_rows = "".join(
        f"<tr><td>{s['sold_date']}</td><td><a href='m-{s['mid']}.html'>{s['model_label']}</a></td>"
        f"<td class='hide-m'><a href='https://m.bunjang.co.kr/products/{s['pid']}' target='_blank' rel='noopener' "
        f"style='font-weight:400'>{s['name'][:40]} ↗</a></td><td class='num'>{won(s['price'])}</td></tr>"
        for s in recent_sales
    ) or "<tr><td colspan='4' style='color:#999'>아직 감지된 거래가 없습니다</td></tr>"

    guide_cards = "".join(
        "<a class='card' href='" + g['slug'] + ".html'><b>" + g['title']
        + "</b><br><span class='meta'>" + g['desc'] + "</span></a>"
        for g in GUIDES)
    home_body = f"""
  <div class="hero">
  <h1>이 물건, 실제로 얼마에 팔렸을까?</h1>
  <p class="sub">호가가 아닌 실거래 추정가로 보는 중고 시세.</p>
  </div>
  {cards}
  <h2>최근 감지된 거래</h2>
  <div class="tbl"><table><thead><tr><th>날짜</th><th>모델</th><th class="hide-m">매물명</th><th class="num">최종 관측가</th></tr></thead>
  <tbody>{sales_rows}</tbody></table></div>
  <h2>중고 거래 가이드</h2>
  <div class="cards">{guide_cards}</div>"""
    website_ld = ('<script type="application/ld+json">'
                  + json.dumps({"@context": "https://schema.org", "@type": "WebSite",
                                "name": SITE_NAME, "url": BASE_URL,
                                "description": "호가가 아닌 실거래 추정가로 보는 중고 시세"},
                               ensure_ascii=False) + "</script>")
    pages["index.html"] = render("index.html", "중고 실거래가 시세",
                                 "스마트폰, 노트북, 그래픽카드, 카메라, 게임기, 골프채 중고 실거래가 시세 — "
                                 "호가가 아닌 실제로 팔린 가격",
                                 home_body, website_ld)
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

    # --- FAQ page (with FAQPage structured data) ---
    faq_html = "".join(
        f"<h2>{q}</h2><p style='font-size:15px;max-width:660px;line-height:1.8'>{a}</p>"
        for q, a in FAQ_ITEMS)
    faq_ld = ('<script type="application/ld+json">'
              + json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                            "mainEntity": [{"@type": "Question", "name": q,
                                            "acceptedAnswer": {"@type": "Answer", "text": a}}
                                           for q, a in FAQ_ITEMS]}, ensure_ascii=False)
              + "</script>")
    faq_body = ("<div class='crumb'><a href='index.html'>홈</a> › 자주 묻는 질문</div>"
                "<h1>자주 묻는 질문</h1>"
                "<p class='sub'>팔린가의 시세 산정 방식과 이용에 관한 질문들.</p>" + faq_html)
    pages["faq.html"] = render("faq.html", "자주 묻는 질문",
                               "팔린가 시세 산정 방식, 데이터 갱신 주기 등 자주 묻는 질문", faq_body, faq_ld)

    # --- 404 page (Cloudflare Pages serves 404.html automatically) ---
    nf_body = ("<h1>페이지를 찾을 수 없습니다</h1>"
               "<p class='sub'>주소가 바뀌었거나 삭제된 페이지입니다.</p>"
               "<p style='font-size:15px'><a href='index.html' style='color:var(--accent)'>"
               "홈으로 돌아가기</a> — 모델명 검색으로 원하는 시세를 찾아보세요.</p>")
    pages["404.html"] = render("404.html", "페이지를 찾을 수 없습니다",
                               "요청하신 페이지를 찾을 수 없습니다", nf_body)

    # --- category pages ---
    for ck, ids in by_cat.items():
        label = CATEGORY_LABELS.get(ck, ck)
        # group by series/brand (catalog order of first appearance, "기타"는 맨 뒤);
        # inside a group: models with data first, 수집 대기 at the bottom
        groups: dict[str, list[str]] = {}
        for mid in ids:
            groups.setdefault(models[mid].get("group") or "기타", []).append(mid)
        sorted_groups = sorted(groups.items(), key=lambda kv: kv[0] == "기타")
        chips_html = ""
        if len(sorted_groups) > 1:
            chips_html = "<div class='chips'>" + "".join(
                f"<a class='chip' href='#g{i}'>{gname} <small>{len(gids)}</small></a>"
                for i, (gname, gids) in enumerate(sorted_groups)) + "</div>"
        sections_html = []
        for i, (gname, gids) in enumerate(sorted_groups):
            gids = sorted(gids, key=lambda i: (models[i]["stats"] is None,
                                               -models[i]["active_count"]))
            sections_html.append(
                f"<h2 id='g{i}'>{gname} <span class='cnt'>{len(gids)}</span></h2>\n"
                f"  <div class='tbl'><table>{TABLE_HEAD}"
                f"<tbody>{model_rows(models, gids)}</tbody></table></div>")
        body = f"""
  <div class="crumb"><a href="index.html">홈</a> › {label}</div>
  <h1>{label} 시세표</h1>
  <p class="sub">모델 {len(ids)}개 · 모델을 클릭하면 거래 내역과 활성 매물을 볼 수 있습니다.</p>
  {chips_html}
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
  <h1>{m['label']} <span class="badge badge-wait">수집 대기</span></h1>
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
            f"<td class='hide-m'>{'세트' if s['is_set'] else ('헤드만' if s['head_only'] else '단품')}</td></tr>"
            for s in m["sold"]
        ) or "<tr><td colspan='4' style='color:#999'>아직 감지된 거래가 없습니다 — 스냅샷이 쌓이면 표시됩니다</td></tr>"
        active_rows = "".join(
            f"<tr><td>{listing_link(r)}</td><td class='num'>{won(r['price'])}</td>"
            f"<td class='num hide-m'>{r['num_faved']}</td>"
            f"<td class='hide-m'>{'세트' if r.get('is_set') else ('헤드만' if r.get('head_only') else '단품')}</td></tr>"
            for r in m["active_sample"][:12]
        )
        body = f"""
  <div class="crumb"><a href="index.html">홈</a> › <a href="cat-{m['category']}.html">{cat_label}</a> › {m['label']}</div>
  <h1>{m['label']} {badge(m['basis'])}</h1>
  <div class="price-card">
    <div class="price-label">실거래 추정가</div>
    <div class="price-big">{won(m['estimate'])}</div>
    <div class="range" style="margin-top:6px">정상 범위 {won(st['q1'])} ~ {won(st['q3'])} · 표본 {st['n']}건</div>
    <div class="range">호가 중앙값 {won(m['asking_median'])} · 활성 매물 {m['active_count']}건</div>
  </div>
  {price_chart(m.get('series', []), m['sold'])}
  <h2>감지된 거래</h2>
  <div class="tbl"><table><thead><tr><th>날짜</th><th>매물명</th><th class="num">최종 관측가</th><th class="hide-m">구성</th></tr></thead>
  <tbody>{sold_rows}</tbody></table></div>
  <h2>현재 활성 매물</h2>
  <div class="tbl"><table><thead><tr><th>매물명</th><th class="num">호가</th><th class="num hide-m">찜</th><th class="hide-m">구성</th></tr></thead>
  <tbody>{active_rows}</tbody></table></div>"""
        crumb_ld = ('<script type="application/ld+json">'
                    + json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList",
                                  "itemListElement": [
                                      {"@type": "ListItem", "position": 1, "name": "홈",
                                       "item": f"{BASE_URL}/index.html"},
                                      {"@type": "ListItem", "position": 2, "name": cat_label,
                                       "item": f"{BASE_URL}/cat-{m['category']}.html"},
                                      {"@type": "ListItem", "position": 3, "name": m["label"]}]},
                                 ensure_ascii=False) + "</script>")
        pages[f"m-{mid}.html"] = render(f"m-{mid}.html", f"{m['label']} 중고 시세",
                                        f"{m['label']} 중고 실거래가 시세 — 추정 {won(m['estimate'])}, "
                                        f"정상 범위 {won(st['q1'])}~{won(st['q3'])}", body, crumb_ld)

    for name, html in pages.items():
        (BASE / name).write_text(html, encoding="utf-8")

    # --- robots.txt & sitemap.xml ---
    base = BASE_URL.rstrip("/")
    (BASE / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
    urls = "\n".join(f"  <url><loc>{base}/{n}</loc><lastmod>{as_of}</lastmod></url>"
                     for n in sorted(pages) if n != "404.html")
    (BASE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n</urlset>\n", encoding="utf-8")
    print(f"generated {len(pages)} pages + robots.txt + sitemap.xml")


if __name__ == "__main__":
    main()
