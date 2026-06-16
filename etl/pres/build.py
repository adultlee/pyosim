"""대선 ETL 오케스트레이터. parse → validate → CSV.

검증을 통과하지 못하면 CSV를 쓰지 않고 exit≠0.
"""

import sys

from etl.pres.schema import to_dataframe
from etl.pres.validate import run_all_checks
from etl.pres.official_totals import OFFICIAL_TOP
from etl.pres.parse_14 import parse_14
from etl.pres.parse_15 import parse_15
from etl.pres.parse_16 import parse_16
from etl.pres.parse_17 import parse_17
from etl.pres.parse_18 import parse_18
from etl.pres.parse_19 import parse_19
from etl.pres.parse_20 import parse_20
from etl.pres.parse_21 import parse_21

ELECTION_DATES = {
    14: "1992-12-18",
    15: "1997-12-18",
    16: "2002-12-19",
    17: "2007-12-19",
    18: "2012-12-19",
    19: "2017-05-09",
    20: "2022-03-09",
    21: "2025-06-03",
}

PARSERS = [
    (14, parse_14),
    (15, parse_15),
    (16, parse_16),
    (17, parse_17),
    (18, parse_18),
    (19, parse_19),
    (20, parse_20),
    (21, parse_21),
]

OUT_PATH = "data_processed/대통령선거.csv"


def build():
    all_rows = []
    all_totals = []
    failed = False

    for round_num, parse_fn in PARSERS:
        print(f"=== {round_num}대 파싱 ===")
        rows, totals = parse_fn()
        for row in rows:
            row.setdefault("선거일", ELECTION_DATES[round_num])
        df = to_dataframe(rows)
        official = {k: v for k, v in OFFICIAL_TOP.items() if k[0] == round_num}
        errors = run_all_checks(df, totals, official or None)
        if errors:
            failed = True
            print(f"  [FAIL] {round_num}대 검증 위반 {len(errors)}건:")
            for name, detail in errors[:20]:
                print(f"    {name}: {detail}")
        else:
            print(f"  [OK] {round_num}대 {len(rows):,}행 검증 통과")
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
