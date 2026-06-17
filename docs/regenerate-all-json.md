# 전체 JSON 재생성 절차 (raw 보유 컴퓨터에서)

작성: 2026-06-17

## 왜 필요한가

이번 세션에서 분석 파이프라인을 두 군데 고쳤다:

1. **10표 임계값** — `analyze_twin_votes.py`가 이제 각 후보 10표 이상 동률만 집계한다
   (기존엔 0표만 거름). 군소후보 1~9표 노이즈가 빠진다.
2. **정당명(`parties`) 출력** — twins JSON에 후보→정당 맵이 들어간다. 웹앱 카드·hero·
   "주요 정당 순" 정렬이 이걸 쓴다.

**9회 지방선거 JSON만 이 환경에서 재생성했다.** 나머지(지방 3~8회, 총선 16~22대,
대선 14~21대)는 원본(`data_raw/...`)이 이 환경에 없어 못 굽었다. 그 원본을 가진
컴퓨터에서 아래를 한 번 돌리면 전부 정정된다.

## 사전 조건

- 이 저장소의 최신 커밋을 받았을 것 (`git pull`). 핵심 커밋:
  - `cec6faa` 9회 파서 EC 매핑 정정 + 분석 10표 임계값·정당명 출력
  - `2486575` 후보쌍 모아보기 + hero 통계 + 회차별 주요 정당 정렬
- `data_raw/` 이하에 선관위 원본이 있을 것 (각 파서가 기대하는 경로):
  - 지방 3~6회: `data_raw/전국동시지방선거 개표결과(제3회~제6회)/...`
  - 지방 7회: `data_raw/전국동시지방선거 개표결과(제7회)/...`
  - 지방 8회: `data_raw/제8회_전국동시지방선거_읍면동별_개표결과-게시판게시/...`
  - 지방 9회: `data/raw/0020260603/...`
  - 총선: `data_raw/...` (etl/assembly/parse_*.py 내 경로)
  - 대선: `data_raw/대통령선거 개표결과(...)/...`
- Python 가상환경 활성화 (`source .venv/bin/activate`).

## 실행 (저장소 루트에서)

```bash
# 1) CSV 3종 생성 — 검증 게이트 통과해야 CSV가 써진다(실패 시 exit≠0)
python -m etl.local.build        # → data_processed/지방선거.csv
python -m etl.assembly.build     # → data_processed/국회의원선거.csv
python -m etl.pres.build         # → data_processed/대통령선거.csv

# 2) CSV 3종 → twin_votes_*.json + index 재생성 (10표 임계값·정당명 포함)
python analyze_twin_votes.py

# 3) 결과 확인 — parties가 채워졌는지, 노이즈가 빠졌는지
#    (각 JSON의 모든 그룹에 parties가 있어야 하고, 득표 10 미만 그룹이 없어야 함)

# 4) 커밋 & 푸시 → Vercel 자동 배포
git add web/public/twin_votes_*.json data_processed/  # data_processed는 gitignore면 빠짐
git commit -m "data: 전체 회차 JSON 재생성 (10표 임계값 + 정당명)"
git push
```

## 검증 포인트

- build가 검증 실패로 멈추면 CSV가 안 써지고 exit≠0 — 파서/원본 문제이니 로그를 본다.
- `analyze_twin_votes.py` 출력에서 각 회차 "쌍둥이 그룹 N개"가 기존보다 크게 줄어드는 게
  정상 (노이즈 제거 효과).
- 웹앱에서 인물 후보(박찬대 등)에 정당명이 보이고, "주요 정당 순" 정렬 시 그 시대 양당이
  맨 위에 오면 성공.
