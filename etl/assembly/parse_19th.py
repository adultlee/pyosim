"""19대(2012) 국회의원선거 파서."""

import os
import re
import xlrd

from etl.assembly.schema import normalize_level
from etl.assembly._helpers import to_int, normalize_sido, parse_party_candidate, is_skip_row

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data_raw")
ROUND = "제19대"
ELECTION_DATE = "2012-04-11"


def _parse_xls_file(path, 선거구분):
    """19대 xls 개별 파일 파서.

    파일 구조:
      row0: 제목
      row1: 빈 행
      row2: 선거 종류 제목
      row3: 헤더 (읍면동명, 투표구명, 선거인수, 투표수, ...)
      row4: 후보/정당 컬럼
      row5~: 데이터
    """
    wb = xlrd.open_workbook(path, encoding_override="cp949")
    ws = wb.sheet_by_index(0)
    ncols = ws.ncols
    rows = []

    if ws.nrows < 6:
        return rows

    header_row = 3
    cand_row = 4

    header = [str(ws.cell_value(header_row, col_idx)).strip() for col_idx in range(ncols)]
    emd_col = 1
    투표구_col = 2
    선거인수_col = 3
    투표수_col = 4
    cand_start = 5

    무효_col = None
    기권_col = None
    for col_idx in range(ncols - 1, -1, -1):
        v = header[col_idx].replace("\n", "").strip()
        if "기권" in v and 기권_col is None:
            기권_col = col_idx
        if "무효" in v and 무효_col is None:
            무효_col = col_idx

    end_col = min(c for c in [무효_col, 기권_col] if c is not None) if (무효_col or 기권_col) else ncols

    candidate_cols = []
    seen_candidates = set()
    for col_idx in range(cand_start, end_col):
        raw = str(ws.cell_value(cand_row, col_idx)).strip()
        if not raw or raw in ("계", "\n"):
            continue
        party, cand = parse_party_candidate(raw)
        if party is None and cand is None:
            continue
        key = (party or "", cand or "")
        if key in seen_candidates:
            continue
        seen_candidates.add(key)
        candidate_cols.append((col_idx, party or "", cand or ""))

    # 파일명으로부터 시도/구시군/선거구명 추출
    # 패턴: '비례_서울_강남구.xls', '국회의원_경북_고령군성주군칠곡군_성주군.xls'
    fname_base = os.path.basename(path)
    name_parts = fname_base.replace(".xls", "").replace(".xlsx", "").split("_")
    sido_str = ""
    구시군_str = ""
    선거구명_str = ""
    if len(name_parts) >= 3:
        sido_str = normalize_sido(name_parts[1])
        구시군_str = name_parts[2]
        선거구명_str = name_parts[3] if len(name_parts) >= 4 else name_parts[2]
    elif len(name_parts) == 2:
        sido_str = normalize_sido(name_parts[1])

    data_start = 5
    for r_idx in range(data_start, ws.nrows):
        emd = str(ws.cell_value(r_idx, emd_col)).strip()
        투표구명 = str(ws.cell_value(r_idx, 투표구_col)).strip()

        if is_skip_row(투표구명):
            continue

        선거인수 = to_int(ws.cell_value(r_idx, 선거인수_col))
        투표수 = to_int(ws.cell_value(r_idx, 투표수_col))
        무효 = to_int(ws.cell_value(r_idx, 무효_col)) if 무효_col is not None else None
        기권 = to_int(ws.cell_value(r_idx, 기권_col)) if 기권_col is not None else None

        for col_idx, party, cand in candidate_cols:
            득표 = to_int(ws.cell_value(r_idx, col_idx))
            rows.append({
                "선거_회차": ROUND,
                "선거일": ELECTION_DATE,
                "선거구분": 선거구분,
                "시도": sido_str,
                "구시군": 구시군_str,
                "읍면동": emd,
                "투표구": 투표구명,
                "선거구명": 선거구명_str,
                "선거인수": 선거인수,
                "투표수": 투표수,
                "후보자": cand if 선거구분 == "지역구" else "",
                "정당": party,
                "득표수": 득표,
                "무효투표수": 무효,
                "기권수": 기권,
                "level": normalize_level(투표구명),
            })

    return rows


def parse_19th(raw_dir=RAW_DIR):
    """19대 지역구+비례 파싱.

    Returns:
        (rows, totals) — totals는 빈 리스트.
    """
    base19 = os.path.join(raw_dir, "국회의원선거 개표결과(제16대~19대)", "제19대 국회의원선거")
    rows = []
    for 구분 in ["지역구", "비례대표"]:
        dir_path = os.path.join(base19, f"제19대 국회의원선거({구분})")
        for root, dirs, files in os.walk(dir_path):
            for fname in sorted(files):
                if fname.endswith(".xls") or fname.endswith(".xlsx"):
                    path = os.path.join(root, fname)
                    rows.extend(_parse_xls_file(path, 구분))
    return rows, []
