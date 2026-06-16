"""20대(2016) 국회의원선거 파서."""

import os
import re
import openpyxl

from etl.assembly.schema import normalize_level
from etl.assembly._helpers import to_int, normalize_sido, parse_party_candidate, is_skip_row

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data_raw")
ROUND = "제20대"
ELECTION_DATE = "2016-04-13"


def _parse_xlsx_file(path, 선거구분):
    """20대/21대 xlsx 개별 파일 파서.

    파일 구조:
      row0(idx=0): '개표상황(투표구별)'
      row1(idx=1): 출력일시
      row2(idx=2): '[국회의원선거][시도명][구시군명][선거구명]'
      row3(idx=3): 헤더 (읍면동명, 투표구명, 선거인수, 투표수, ...)
      row4(idx=4): 후보/정당 컬럼
      row5(idx=5): 데이터 시작 (빈 행 있을 수 있음)
    """
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as error:
        print(f"  [SKIP] {path}: {error}")
        return []
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if len(all_rows) < 6:
        return []

    title3 = str(all_rows[2][0] or "").strip()
    bracket_parts = re.findall(r"\[([^\]]+)\]", title3)
    sido_str = ""
    구시군_str = ""
    선거구명_str = ""
    if len(bracket_parts) >= 2:
        sido_str = normalize_sido(bracket_parts[1])
        if len(bracket_parts) >= 3:
            구시군_str = bracket_parts[2]
        선거구명_str = bracket_parts[3] if len(bracket_parts) >= 4 else 구시군_str

    # 비례대표 파일명에서 구시군명 추출 (헤더 오류 대응)
    # 파일명 패턴: '개표상황(투표구별)_밀양시.xlsx'
    fname_stem = os.path.splitext(os.path.basename(path))[0]
    if "_" in fname_stem and 선거구분 == "비례대표":
        fname_구시군 = fname_stem.split("_", 1)[-1]
        if fname_구시군 and fname_구시군 != 구시군_str:
            구시군_str = fname_구시군
            선거구명_str = fname_구시군

    header_row = list(all_rows[3])
    ncols = len(header_row)

    emd_col = 0
    투표구_col = 1
    선거인수_col = 2
    투표수_col = 3
    cand_start = 4

    무효_col = None
    기권_col = None
    for col_idx in range(ncols - 1, -1, -1):
        v = str(header_row[col_idx] or "").replace("\n", "").strip()
        if "기권" in v and 기권_col is None:
            기권_col = col_idx
        if "무효" in v and 무효_col is None:
            무효_col = col_idx

    end_col = min(c for c in [무효_col, 기권_col] if c is not None) if (무효_col or 기권_col) else ncols

    cand_row = list(all_rows[4])
    candidate_cols = []
    for col_idx in range(cand_start, end_col):
        raw = str(cand_row[col_idx] or "").strip()
        if not raw or raw in ("계", "\n"):
            continue
        party, cand = parse_party_candidate(raw)
        if party is None and cand is None:
            continue
        candidate_cols.append((col_idx, party or "", cand or ""))

    # 데이터 시작: row5(idx=5) 또는 row6
    if len(all_rows) > 5 and all(v is None or str(v).strip() == "" for v in all_rows[5]):
        data_start = 6
    else:
        data_start = 5

    rows = []
    current_emd = ""
    for r_idx in range(data_start, len(all_rows)):
        row = all_rows[r_idx]
        if len(row) < 4:
            continue
        emd = str(row[emd_col] or "").strip()
        투표구명 = str(row[투표구_col] or "").strip()

        # 소계행에서 읍면동명 갱신 (실제 데이터행에는 빈 값으로 오는 경우가 많음)
        if emd and 투표구명 in ("소계", ""):
            current_emd = emd

        if is_skip_row(투표구명):
            continue

        # 데이터행의 읍면동이 비어있으면 직전 소계행의 읍면동을 사용
        if not emd:
            emd = current_emd

        선거인수 = to_int(row[선거인수_col])
        투표수 = to_int(row[투표수_col])
        무효 = to_int(row[무효_col]) if 무효_col is not None and 무효_col < len(row) else None
        기권 = to_int(row[기권_col]) if 기권_col is not None and 기권_col < len(row) else None

        for col_idx, party, cand in candidate_cols:
            득표 = to_int(row[col_idx]) if col_idx < len(row) else None
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


def parse_20th(raw_dir=RAW_DIR):
    """20대 지역구+비례 파싱.

    Returns:
        (rows, totals) — totals는 빈 리스트.
    """
    base20 = os.path.join(raw_dir, "제20대 국회의원선거 투표구별 개표결과")
    rows = []
    for 구분 in ["지역구", "비례대표"]:
        dir_path = os.path.join(base20, 구분)
        for root, dirs, files in os.walk(dir_path):
            for fname in sorted(files):
                if fname.endswith(".xlsx"):
                    path = os.path.join(root, fname)
                    rows.extend(_parse_xlsx_file(path, 구분))
    return rows, []
