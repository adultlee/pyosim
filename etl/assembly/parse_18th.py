"""18대(2008) 국회의원선거 파서."""

import os
import xlrd

from etl.assembly.schema import normalize_level
from etl.assembly._helpers import to_int, is_skip_row
from etl.assembly.parse_17th import _parse_sido_file

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data_raw")
ROUND = "제18대"
ELECTION_DATE = "2008-04-09"

_SIDO_MAP_18 = {
    "서울": "서울", "부산": "부산", "대구": "대구", "인천": "인천", "광주": "광주",
    "대전": "대전", "울산": "울산", "경기": "경기", "강원": "강원", "충북": "충북",
    "충남": "충남", "전북": "전북", "전남": "전남", "경북": "경북", "경남": "경남", "제주": "제주",
}


def _parse_18th_비례(raw_dir):
    path = os.path.join(raw_dir, "국회의원선거 개표결과(제16대~19대)", "제18대 국회의원선거",
                        "제18대 국회의원선거(비례대표).xls")
    wb = xlrd.open_workbook(path, encoding_override="cp949")
    rows = []

    for sheet_idx in range(wb.nsheets):
        ws = wb.sheet_by_index(sheet_idx)
        sido = ws.name.strip()
        ncols = ws.ncols
        if ws.nrows < 3:
            continue

        party_row1 = [str(ws.cell_value(1, col_idx)).strip() for col_idx in range(ncols)]

        구시군_col = 0
        emd_col = 1
        투표구_col = 2
        선거인수_col = 3
        투표수_col = 4
        cand_start = 5

        무효_col = None
        기권_col = None
        for col_idx in range(ncols - 1, -1, -1):
            v = str(ws.cell_value(0, col_idx)).strip()
            if "기권" in v and 기권_col is None:
                기권_col = col_idx
            if "무효" in v and 무효_col is None:
                무효_col = col_idx

        end_col = min(c for c in [무효_col, 기권_col] if c is not None) if (무효_col or 기권_col) else ncols
        candidate_cols = []
        for col_idx in range(cand_start, end_col):
            party = party_row1[col_idx]
            if party in ("계", "", "무효\n투표수"):
                continue
            candidate_cols.append((col_idx, party))

        for r_idx in range(2, ws.nrows):
            구시군 = str(ws.cell_value(r_idx, 구시군_col)).strip()
            emd = str(ws.cell_value(r_idx, emd_col)).strip()
            투표구명 = str(ws.cell_value(r_idx, 투표구_col)).strip()

            if is_skip_row(투표구명):
                continue
            if not 투표구명:
                continue

            선거인수 = to_int(ws.cell_value(r_idx, 선거인수_col))
            투표수 = to_int(ws.cell_value(r_idx, 투표수_col))
            무효 = to_int(ws.cell_value(r_idx, 무효_col)) if 무효_col is not None else None
            기권 = to_int(ws.cell_value(r_idx, 기권_col)) if 기권_col is not None else None

            for col_idx, party in candidate_cols:
                득표 = to_int(ws.cell_value(r_idx, col_idx))
                rows.append({
                    "선거_회차": ROUND,
                    "선거일": ELECTION_DATE,
                    "선거구분": "비례대표",
                    "시도": sido,
                    "구시군": 구시군,
                    "읍면동": emd,
                    "투표구": 투표구명,
                    "선거구명": "",
                    "선거인수": 선거인수,
                    "투표수": 투표수,
                    "후보자": "",
                    "정당": party,
                    "득표수": 득표,
                    "무효투표수": 무효,
                    "기권수": 기권,
                    "level": normalize_level(투표구명),
                })

    return rows


def parse_18th(raw_dir=RAW_DIR):
    """18대 지역구+비례 파싱.

    Returns:
        (rows, totals) — totals는 빈 리스트.
    """
    base18 = os.path.join(raw_dir, "국회의원선거 개표결과(제16대~19대)", "제18대 국회의원선거")
    rows = []
    for fname, sido in _SIDO_MAP_18.items():
        path = os.path.join(base18, "제18대 국회의원선거(지역구)", f"{fname}.xls")
        if os.path.exists(path):
            rows.extend(_parse_sido_file(path, sido, "지역구", "제18대", ELECTION_DATE))
    rows.extend(_parse_18th_비례(raw_dir))
    return rows, []
