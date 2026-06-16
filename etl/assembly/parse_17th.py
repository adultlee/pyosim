"""17대(2004) 국회의원선거 파서."""

import os
import re
import xlrd

_EMD_FROM_STATION = re.compile(r"^([가-힣0-9]+(?:[가-힣0-9 ]*[가-힣0-9])?)(?:제\s*|\s+)\d+투$")


def _extract_emd(투표구명):
    """투표구명에서 읍면동명 추출. 예: '남면제1투' → '남면', '후평1동제1투' → '후평1동'."""
    m = _EMD_FROM_STATION.match(투표구명)
    if not m:
        return None
    return m.group(1).rstrip("제").strip()

from etl.assembly.schema import normalize_level
from etl.assembly._helpers import to_int, is_skip_row

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data_raw")
ROUND = "제17대"
ELECTION_DATE = "2004-04-15"

_SIDO_MAP_17 = {
    "01 서울": "서울", "02 부산": "부산", "03 대구": "대구", "04 인천": "인천",
    "05 광주": "광주", "06 대전": "대전", "07 울산": "울산", "08 경기": "경기",
    "09 강원": "강원", "10 충북": "충북", "11 충남": "충남", "12 전북": "전북",
    "13 전남": "전남", "14 경북": "경북", "15 경남": "경남", "16 제주": "제주",
}


def _parse_sido_file(path, sido, 선거구분, 회차=ROUND, 선거일=ELECTION_DATE):
    """시도별 xls, 시트별 선거구 공통 파서 (17대/18대 지역구)."""
    wb = xlrd.open_workbook(path, encoding_override="cp949")
    rows = []
    for sheet_idx in range(wb.nsheets):
        ws = wb.sheet_by_index(sheet_idx)
        선거구명 = ws.name.strip()
        ncols = ws.ncols
        if ws.nrows < 4:
            continue

        header_row0 = [str(ws.cell_value(0, col_idx)).strip() for col_idx in range(ncols)]

        if header_row0[0] in ("읍면동명",):
            # 18대 지역구: col0=읍면동, col1=투표구명, col2=선거인수, col3=투표수
            emd_col = 0
            투표구_col = 1
            선거인수_col = 2
            투표수_col = 3
            cand_start_col = 4
            data_start_row = 3
        else:
            # 17대: col0=투표구명, col1=선거인수, col2=투표수
            emd_col = None
            투표구_col = 0
            선거인수_col = 1
            투표수_col = 2
            cand_start_col = 3
            data_start_row = 3

        무효_col = None
        기권_col = None
        for col_idx in range(ncols - 1, -1, -1):
            v0 = str(ws.cell_value(0, col_idx)).strip()
            if "기권" in v0 and 기권_col is None:
                기권_col = col_idx
            if "무효" in v0 and 무효_col is None:
                무효_col = col_idx

        end_col = min(c for c in [무효_col, 기권_col] if c is not None) if (무효_col or 기권_col) else ncols

        candidate_cols = []
        for col_idx in range(cand_start_col, end_col):
            if 선거구분 == "지역구":
                party = re.sub(r"\s+", " ", str(ws.cell_value(1, col_idx))).strip()
                cand = re.sub(r"\s+", " ", str(ws.cell_value(2, col_idx))).strip()
            else:
                party = re.sub(r"\s+", " ", str(ws.cell_value(1, col_idx))).strip()
                cand = party

            if not party and not cand:
                continue
            if party in ("", "계") and cand in ("", "계"):
                continue
            candidate_cols.append((col_idx, party, cand))

        current_구시군 = ""
        current_emd = ""
        for r_idx in range(data_start_row, ws.nrows):
            투표구명 = str(ws.cell_value(r_idx, 투표구_col)).strip()
            if is_skip_row(투표구명):
                continue

            # 군/시 구분 헤더행 (예: '철원군', '양구군') — 구시군 컨텍스트 갱신 후 건너뜀
            if re.fullmatch(r".+[시군]", 투표구명) and 선거인수_col < ws.ncols and not ws.cell_value(r_idx, 선거인수_col):
                current_구시군 = 투표구명
                current_emd = ""
                continue

            emd = str(ws.cell_value(r_idx, emd_col)).strip() if emd_col is not None else ""

            # 투표구명에서 읍면동명 추출 (예: '남면제1투' → '남면')
            if emd_col is None:
                extracted = _extract_emd(투표구명)
                if extracted:
                    current_emd = extracted
                emd = current_emd

            선거인수 = to_int(ws.cell_value(r_idx, 선거인수_col))
            투표수 = to_int(ws.cell_value(r_idx, 투표수_col))
            무효 = to_int(ws.cell_value(r_idx, 무효_col)) if 무효_col is not None else None
            기권 = to_int(ws.cell_value(r_idx, 기권_col)) if 기권_col is not None else None

            for col_idx, party, cand in candidate_cols:
                득표 = to_int(ws.cell_value(r_idx, col_idx))
                actual_cand = cand if 선거구분 == "지역구" else ""
                rows.append({
                    "선거_회차": 회차,
                    "선거일": 선거일,
                    "선거구분": 선거구분,
                    "시도": sido,
                    "구시군": current_구시군,
                    "읍면동": emd,
                    "투표구": 투표구명,
                    "선거구명": 선거구명,
                    "선거인수": 선거인수,
                    "투표수": 투표수,
                    "후보자": actual_cand,
                    "정당": party,
                    "득표수": 득표,
                    "무효투표수": 무효,
                    "기권수": 기권,
                    "level": normalize_level(투표구명),
                })

    return rows


def parse_17th(raw_dir=RAW_DIR):
    """17대 지역구+비례 파싱.

    Returns:
        (rows, totals) — totals는 빈 리스트.
    """
    base17 = os.path.join(raw_dir, "국회의원선거 개표결과(제16대~19대)", "제17대 국회의원선거")
    rows = []
    for fname_stem, sido in _SIDO_MAP_17.items():
        for 구분 in ["지역구", "비례대표"]:
            path = os.path.join(base17, f"제17대 국회의원선거({구분})", f"{fname_stem}.xls")
            if os.path.exists(path):
                rows.extend(_parse_sido_file(path, sido, 구분))
    return rows, []
