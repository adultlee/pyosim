"""21대(2020) 국회의원선거 파서."""

import os

from etl.assembly.parse_20th import _parse_xlsx_file as _parse_20th_xlsx

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data_raw")
ROUND = "제21대"
ELECTION_DATE = "2020-04-15"


def _parse_xlsx_file(path, 선거구분):
    """21대 xlsx 파일 파서 — 20대와 파일 구조 동일, 회차/날짜만 다름."""
    rows = _parse_20th_xlsx(path, 선거구분)
    for row in rows:
        row["선거_회차"] = ROUND
        row["선거일"] = ELECTION_DATE
    return rows


def parse_21st(raw_dir=RAW_DIR):
    """21대 지역구+비례 파싱.

    Returns:
        (rows, totals) — totals는 빈 리스트.
    """
    base21 = os.path.join(raw_dir, "제21대 국회의원선거(재보궐 포함) 투표구별 개표결과")
    rows = []
    for 구분 in ["지역구", "비례대표"]:
        dir_path = os.path.join(base21, 구분)
        for root, dirs, files in os.walk(dir_path):
            for fname in sorted(files):
                if fname.endswith(".xlsx"):
                    path = os.path.join(root, fname)
                    rows.extend(_parse_xlsx_file(path, 구분))
    return rows, []
