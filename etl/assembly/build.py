# etl/assembly/build.py
"""총선 ETL 오케스트레이터. parse → validate → CSV."""

import sys
from etl.assembly.schema import to_dataframe
from etl.assembly.validate import run_all_checks
from etl.assembly.official_totals import OFFICIAL_TOP
from etl.assembly.parse_16th import parse_16th
from etl.assembly.parse_17th import parse_17th
from etl.assembly.parse_18th import parse_18th
from etl.assembly.parse_19th import parse_19th
from etl.assembly.parse_20th import parse_20th
from etl.assembly.parse_21st import parse_21st
from etl.assembly.parse_22nd import parse_22nd

ELECTION_DATES = {
    "제16대": "2000-04-13",
    "제17대": "2004-04-15",
    "제18대": "2008-04-09",
    "제19대": "2012-04-11",
    "제20대": "2016-04-13",
    "제21대": "2020-04-15",
    "제22대": "2024-04-10",
}

PARSERS = [
    ("제16대", parse_16th),
    ("제17대", parse_17th),
    ("제18대", parse_18th),
    ("제19대", parse_19th),
    ("제20대", parse_20th),
    ("제21대", parse_21st),
    ("제22대", parse_22nd),
]

OUT_PATH = "data_processed/국회의원선거.csv"


def build():
    all_rows = []
    failed = False

    for round_str, parse_fn in PARSERS:
        print(f"=== {round_str} 파싱 ===")
        rows, totals = parse_fn()
        df = to_dataframe(rows)
        official = {k: v for k, v in OFFICIAL_TOP.items() if k[0] == round_str}
        errors = run_all_checks(df, totals, official)
        if errors:
            failed = True
            print(f"  [FAIL] {round_str} 검증 위반 {len(errors)}건:")
            for name, detail in errors[:20]:
                print(f"    {name}: {detail}")
        else:
            print(f"  [OK] {round_str} {len(rows):,}행 검증 통과")
        all_rows.extend(rows)

    if failed:
        print("\n검증 실패 — CSV를 쓰지 않습니다.")
        sys.exit(1)

    df = to_dataframe(all_rows)
    df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n[DONE] {len(df):,}행 → {OUT_PATH}")


if __name__ == "__main__":
    build()
