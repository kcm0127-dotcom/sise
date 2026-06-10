"""Generate a multi-page static site from stats.json.

Pages:
  index.html          home — search box, category cards, recently detected sales
  cat-{key}.html      category price table
  m-{model_id}.html   model detail — estimate, detected sales, active listings

    python site_gen.py
"""

import json
from pathlib import Path

BASE = Path(__file__).parent

# ---- deployment settings ----
BASE_URL = "https://sise.pages.dev"  # Cloudflare Pages 주소 (커스텀 도메인 연결 시 교체)
ADSENSE_CLIENT = "ca-pub-6840959424010586"  # 퍼즐마루와 동일 퍼블리셔
SITE_NAME = "팔린가"

CATEGORY_LABELS = {"gpu": "그래픽카드", "camera": "카메라", "golf": "골프채"}
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

    home_body = f"""
  <h1>이 물건, 실제로 얼마에 팔렸을까?</h1>
  <p class="sub">호가가 아닌 실거래 추정가로 보는 중고 시세.</p>
  <div class="search"><input id="q" type="search" placeholder="모델명 검색 — 예: 4070, A7M4, 스텔스" autocomplete="off"><div class="hits" id="hits"></div></div>
  <div class="cards">{cards}</div>
  <h2>최근 감지된 거래</h2>
  <table><thead><tr><th>날짜</th><th>모델</th><th>매물명</th><th class="num">최종 관측가</th></tr></thead>
  <tbody>{sales_rows}</tbody></table>"""
    pages["index.html"] = render("index.html", "중고 실거래가 시세",
                                 "그래픽카드, 카메라, 골프채 중고 실거래가 시세 — 호가가 아닌 실제로 팔린 가격",
                                 home_body, search_script)
    pages["about.html"] = render("about.html", "서비스 소개",
                                 "팔린가 서비스 소개 — 중고 실거래가 시세 산정 방식과 데이터 출처", ABOUT_BODY)
    pages["privacy.html"] = render("privacy.html", "개인정보처리방침",
                                   "팔린가 개인정보처리방침", PRIVACY_BODY)

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
