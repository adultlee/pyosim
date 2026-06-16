"""지방선거 ETL 오케스트레이터. parse → validate → CSV.

검증을 통과하지 못하면 CSV를 쓰지 않고 exit≠0.
"""

import sys

from etl.local.schema import to_dataframe
from etl.local.validate import run_all_checks
from etl.local.official_totals import OFFICIAL_TOP
from etl.local.parse_3rd import parse_3rd
from etl.local.parse_4th import parse_4th
from etl.local.parse_5th import parse_5th
from etl.local.parse_6th import parse_6th
from etl.local.parse_7th import parse_7th
from etl.local.parse_8th import parse_8th
from etl.local.parse_9th import parse_9th

ROOT = "data_raw"
LOCAL36 = f"{ROOT}/전국동시지방선거 개표결과(제3회~제6회)"

ELECTION_DATES = {
    3: "2002-06-13", 4: "2006-05-31", 5: "2010-06-02",
    6: "2014-06-04", 7: "2018-06-13", 8: "2022-06-01",
    9: "2026-06-03",
}

PARSERS = [
    (3, lambda: parse_3rd(f"{LOCAL36}/제3회 전국동시지방선거 개표자료"), {}),
    (4, lambda: parse_4th(f"{LOCAL36}/제4회 전국동시지방선거 개표자료"), {}),
    (5, lambda: parse_5th(f"{LOCAL36}/제5회 전국동시지방선거 개표자료"), {}),
    (6, lambda: parse_6th(f"{LOCAL36}/제6회 전국동시지방선거 개표결과"), {}),
    (7, lambda: parse_7th(f"{ROOT}/전국동시지방선거 개표결과(제7회)"), {}),
    (8, lambda: parse_8th(f"{ROOT}/제8회_전국동시지방선거_읍면동별_개표결과-게시판게시"), {}),
    # 9회: 광주·전남 시도지사 후보집합이 실제로 동일 — sido_consistency 검사 스킵
    (9, lambda: parse_9th(), {"skip_sido_consistency": True}),
]

OUT_PATH = "data_processed/지방선거.csv"


def build():
    all_rows = []
    all_totals = []
    failed = False

    for round_num, parse_fn, check_opts in PARSERS:
        print(f"=== {round_num}회 파싱 ===")
        rows, totals = parse_fn()
        for row in rows:
            row.setdefault("선거일", ELECTION_DATES[round_num])
        df = to_dataframe(rows)
        official = {k: v for k, v in OFFICIAL_TOP.items() if k[0] == round_num}
        errors = run_all_checks(df, totals, official, **check_opts)
        if errors:
            failed = True
            print(f"  [FAIL] {round_num}회 검증 위반 {len(errors)}건:")
            for name, detail in errors[:20]:
                print(f"    {name}: {detail}")
        else:
            print(f"  [OK] {round_num}회 {len(rows):,}행 검증 통과")
        all_rows.extend(rows)
        all_totals.extend(totals)

    if failed:
        print("\n검증 실패 — CSV를 쓰지 않습니다.")
        sys.exit(1)

    df = to_dataframe(all_rows)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n[DONE] {len(df):,}행 → {OUT_PATH}")


if __name__ == "__main__":
    build()
