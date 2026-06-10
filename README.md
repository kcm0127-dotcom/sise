# 팔린가 MVP — 중고 실거래가 파이프라인

다나와 스타일의 중고 실거래가 사이트 MVP. 기획서(`../중고시세_서비스_기획서.md`) §5~6 구현.

## 구조

```
catalog_gen.py  모델 사전 생성기 — GPU 39종, 카메라 37종, 드라이버 19종 (총 95종)
catalog.json    생성된 모델 사전 (직접 수정하지 말고 catalog_gen.py 수정 후 재생성)
collector.py    일일 스냅샷 수집기 (번개장터 검색 API, 일 1회 실행)
pipeline.py     정제 — 더미가격/카테고리/키워드 필터, 모델 매칭, 세트·헤드만 플래그
stats.py        거래 추정(스냅샷 diff) + 중앙값·IQR 통계 → stats.json
site_gen.py     stats.json → 멀티페이지 사이트 (index + 카테고리 + 모델 상세, 검색 포함)
snapshots/      일별 스냅샷 (JSONL). 현재 실데이터 기반 픽스처 2일치 포함
```

## 실행 (본인 PC에서)

```bash
python collector.py        # 스윕 모드(기본): 카테고리 전체 매물 수집 — 매일 1회
python collector.py query  # 쿼리 모드: 모델별 검색 (좁은 범위, 레거시)
python stats.py            # 정제 → 거래 추정 → stats.json
python site_gen.py         # 멀티페이지 사이트 생성
```

스윕 모드는 카테고리의 모든 활성 매물을 수집한다 (GPU 카테고리 기준 약 1.4만 건 ≈ 140페이지).
모델 사전에 없는 매물도 일단 수집되고, 파이프라인이 사전 기반으로 분류한다 — 새 모델을
사전에 추가하면 이미 쌓인 스냅샷에서 소급 집계된다는 게 스윕 모드의 큰 장점.
요청량은 3개 카테고리 합계 일 300~500요청, 3초 간격으로 약 20~25분.

의존성 없음 (표준 라이브러리만 사용). cron 예시: `0 3 * * * cd ~/sise && python3 collector.py && python3 stats.py && python3 site_gen.py`

## 동작 원리

1. **수집**: 모델별 검색 쿼리로 활성 매물을 매일 스냅샷. 검색에는 판매중 매물만 노출되므로,
2. **거래 추정**: 어제 있던 매물이 오늘 사라지면 거래 발생으로 추정 (마지막 관측가 = 거래가 근사치). 정제에서 탈락한 매물은 사라져도 거래로 치지 않음.
3. **통계**: 단품 매물만으로 중앙값·IQR 계산. 시세 추정은 3단 폴백 —
   ① 모델 실거래 표본 5건 이상 → 실거래 중앙값,
   ② 부족하면 카테고리 단위 체결 할인율(실거래중앙값/호가중앙값 학습값)을 호가에 적용,
   ③ 그것도 없으면 호가 분포 하단(Q1~중앙값 중간점) 사용. 화면에 산정 근거 배지 표시.

## 모델 추가 방법

`catalog_gen.py`의 GPUS / CAMS / DRIVERS 리스트에 한 줄 추가 후 재실행:
`(slug, 표시명, 검색어, include 정규식, (가격하한, 가격상한 — 만원))`.
변형 구분(4070 vs Ti vs SUPER 등)은 include 정규식의 부정 lookahead로 처리.
파이프라인이 교차 재매칭을 하므로("RTX 4070" 검색에 딸려온 Ti 매물을 Ti 모델로 재배정)
검색어가 겹쳐도 데이터가 유실되지 않음.

수집량 참고: 95개 모델 × 최대 3페이지 × 5초 딜레이 ≈ 일 1회 25분 내외.

가격 범위는 시세가 아니라 이상치 차단용 울타리(넉넉하게 설정). 운영하며 튜닝.

## 주의

- 비공식 엔드포인트 사용. **일 1회, 저빈도 유지**, 차단·이의 제기 시 즉시 중단. 상용화 전 법률 자문 필수 (기획서 §5, §9).
- 수집 데이터는 집계값만 노출하고 원문을 재게시하지 않는 원칙 유지.

## 배포 (Cloudflare Pages — 퍼즐마루와 동일 방식)

1. GitHub에 빈 저장소 생성 (예: kcm0127-dotcom/sise) 후:
   ```bash
   cd ~/Claude/Projects/App\ Develops/sise
   rm -f .git/HEAD.lock .git/index.lock .git/objects/maintenance.lock
   git remote add origin https://github.com/kcm0127-dotcom/sise.git
   git push -u origin main
   ```
2. Cloudflare 대시보드 → Workers & Pages → Create → Pages →
   **Connect to Git** → sise 저장소 선택 → 빌드 설정은 모두 비움(정적 파일) → Deploy
3. 배포 주소(`https://sise.pages.dev` 또는 프로젝트명.pages.dev)를 확인하고,
   `site_gen.py`의 `BASE_URL`과 다르면 수정 후 다시 push
4. 일일 자동 갱신은 cron 등록:
   ```
   0 3 * * * /bin/bash "$HOME/Claude/Projects/App Develops/sise/deploy.sh" >> "$HOME/sise-deploy.log" 2>&1
   ```
   deploy.sh가 수집 → 통계 → 빌드 → push를 하고, push되면 Cloudflare가 자동 재배포한다.

## 구글 애드센스 연결

1. 사이트가 배포되고 콘텐츠(모델 페이지 + 소개/개인정보처리방침)가 충분히 쌓인 뒤
   [애드센스](https://adsense.google.com)에 사이트 등록 — 보통 도메인 연결을 권장 (커스텀 도메인 추천)
2. 발급받은 클라이언트 ID를 `site_gen.py`의 `ADSENSE_CLIENT`에 입력 — 퍼즐마루 퍼블리셔 ID(pub-6840959424010586)가 이미 설정·ads.txt 포함됨. 애드센스 콘솔에서 '사이트 추가'만 하면 됨 → 전 페이지 head에 코드 삽입됨
3. 승인 후 자동 광고를 켜거나 광고 단위 코드를 페이지에 추가
4. 승인 팁: 개인정보처리방침/소개/문의(이미 포함됨), 충분한 페이지 수(101페이지 충족),
   사이트 완성도와 자체 콘텐츠가 핵심. "수집 대기" 빈 페이지가 많으면 불리할 수 있으니
   데이터가 채워진 뒤 신청 권장

## 다음 할 일

- [ ] 본인 PC에서 collector.py 실제 가동 (스냅샷 2일치 이상 쌓이면 거래 감지 시작)
- [ ] 모델 사전 확장 (GPU 상위 20개 → 카메라 바디 10개 → 드라이버 10개)
- [ ] 시세 추이 차트 (일별 stats.json 누적 후 site_gen에 추가)
- [ ] SQLite 전환 (스냅샷이 30일치 이상 쌓이면), 이후 Next.js 프론트로 이전
