"""
재보궐선거 raw 데이터 → 통합 CSV 정제 스크립트
출력: data_processed/재보궐선거.csv

파일 형식 분류:
  A) 2001~2002: 선거구 단위 요약 (wide, 3행 헤더 구조)
  B) 2005~2010: 일부 투표구 단위 데이터 (국회의원은 투표구별, 나머지는 선거구 단위)
     - 2005 xls: '후보자별득표(xxx)' 시트들 (선거구 단위 요약)
     - 2007 이후: 투표구별 xls (읍면동/투표구 포함)
  C) 2009~2010: 투표구별 xls (시트별 선거구)
  D) 2011~: 폴더별 투표구별 xls/xlsx
  E) 2013 standalone xlsx / 2018~2019 standalone xlsx
"""

import os
import re
import sys
import unicodedata
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

BASE = "/Users/seong-in/Desktop/Git/pyosim"
RAW_DIR = os.path.join(BASE, "data_raw", "04_재보궐선거_결과(1998년_이후)")
OUT_CSV = os.path.join(BASE, "data_processed", "재보궐선거.csv")

FINAL_COLS = [
    "선거일", "선거종류", "시도", "구시군", "읍면동", "투표구",
    "선거구명", "선거인수", "투표수", "후보자", "정당", "득표수", "무효투표수", "기권수",
]

# 합계/소계 등 집계행 키워드
SKIP_ROW_KEYWORDS = {
    "합계", "소계", "계", "부재자", "부재자투표", "국내부재자투표",
    "국내부재자", "거소투표", "거소우편투표", "관외사전투표", "관내사전투표",
    "관외사전", "관내사전", "재외투표", "국외부재자투표", "잘못투입된투표지",
    "잘못된투표지", "거소·선상투표", "선상투표", "(득표율)",
}

skipped_files = []
all_records = []


# ─────────────────────────────────────────────────────────────────────────────
# 유틸 함수
# ─────────────────────────────────────────────────────────────────────────────

def to_int(val):
    if val is None:
        return None
    val_str = str(val).replace(",", "").strip()
    if not val_str or val_str in ("nan", "-", "NaN", ""):
        return None
    try:
        return int(float(val_str))
    except (ValueError, TypeError):
        return None


def is_number(val):
    if val is None:
        return False
    try:
        float(str(val).replace(",", "").strip())
        return True
    except (ValueError, TypeError):
        return False


def parse_party_candidate(col_str):
    """'정당\n후보자' 형식 → (정당, 후보자)"""
    if not col_str:
        return None, None
    raw = str(col_str).strip()
    # Clean up _x000D_ artifacts from xlsx
    raw = raw.replace("_x000D_", "").strip()
    if not raw or raw in ("", "\n", "계", " "):
        return None, None
    if "\n" in raw:
        parts = [p.strip() for p in raw.split("\n") if p.strip()]
        if len(parts) >= 2:
            return parts[0], parts[1]
        if len(parts) == 1:
            return parts[0], ""
    return raw, ""


def normalize_election_type(raw_str):
    """선거 종류 정규화"""
    if not raw_str:
        return raw_str
    s = str(raw_str).strip()
    mapping = {
        "국회의원선거": "국회의원",
        "국회의원보궐선거": "국회의원",
        "국회의원": "국회의원",
        "시·도지사선거": "시도지사",
        "시도지사선거": "시도지사",
        "시도지사": "시도지사",
        "구·시·군장선거": "구시군장",
        "구시군장선거": "구시군장",
        "구시군의장선거": "구시군장",
        "구·시·군의장선거": "구시군장",
        "구시군장": "구시군장",
        "시·도의회의원선거": "시도의회의원",
        "시도의회의원선거": "시도의회의원",
        "시도의원선거": "시도의회의원",
        "시도의회의원": "시도의회의원",
        "구·시·군의회의원선거": "구시군의회의원",
        "구시군의회의원선거": "구시군의회의원",
        "구시군의원선거": "구시군의회의원",
        "구시군의회의원": "구시군의회의원",
        "교육감선거": "교육감",
        "교육감": "교육감",
    }
    for key, val in mapping.items():
        if key in s:
            return val
    return s


def parse_date_from_filename(name):
    """파일명/폴더명에서 선거일 추출 → YYYY-MM-DD
    macOS 파일시스템은 NFD 유니코드를 사용하므로 NFC로 정규화 후 매칭
    """
    name_nfc = unicodedata.normalize("NFC", name)
    match = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', name_nfc)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return None


def infer_election_type_from_path(filepath):
    """파일 경로에서 선거 종류 추론"""
    path_lower = unicodedata.normalize("NFC", filepath).replace("\\", "/")
    if "국회의원" in path_lower or "assembly" in path_lower.lower():
        return "국회의원"
    if "시도지사" in path_lower:
        return "시도지사"
    if "구시군의장" in path_lower or "구·시·군장" in path_lower or "구시군장" in path_lower:
        return "구시군장"
    if "시도의회의원" in path_lower or "시도의원" in path_lower or "시·도의회의원" in path_lower:
        return "시도의회의원"
    if "구시군의회의원" in path_lower or "구시군의원" in path_lower or "구·시·군의회의원" in path_lower:
        return "구시군의회의원"
    if "교육감" in path_lower:
        return "교육감"
    if "광역의원" in path_lower:
        return "시도의회의원"
    if "기초의원" in path_lower:
        return "구시군의회의원"
    if "기초장" in path_lower or "기초단체장" in path_lower:
        return "구시군장"
    return None


def infer_election_type_from_sheet(sheet_name):
    """시트명에서 선거 종류 추론"""
    s = unicodedata.normalize("NFC", str(sheet_name))
    if "국회의원" in s:
        return "국회의원"
    if "시도지사" in s or "시·도지사" in s:
        return "시도지사"
    if "구시군의장" in s or "구·시·군의장" in s or "구시군의장" in s or "구시군장" in s:
        return "구시군장"
    if "기초단체장" in s or "기초장" in s or "단체장" in s:
        return "구시군장"
    if "시도의회" in s or "시·도의회" in s or "광역의원" in s:
        return "시도의회의원"
    if "구시군의회" in s or "구·시·군의회" in s or "기초의원" in s:
        return "구시군의회의원"
    if "교육감" in s:
        return "교육감"
    # 시트명 패턴으로 추론 (2008 형식: 울주군수, 의령군다선거구, 구미시제4선거구 등)
    if re.search(r'[군시]수$', s) or re.search(r'[군시]장$', s):
        return "구시군장"
    if re.search(r'[가나다라마바사아자차카타파하]선거구$', s):
        return "구시군의회의원"
    if re.search(r'제\d+선거구$', s):
        return "시도의회의원"
    return None


def is_summary_row(row_label):
    """합계/소계 등 행인지 판단"""
    if row_label is None:
        return False
    s = str(row_label).strip()
    if not s or s == "nan":
        return False
    return s in SKIP_ROW_KEYWORDS or "소계" in s or "합계" in s


# ─────────────────────────────────────────────────────────────────────────────
# 파서 A: 2001~2002 요약형 (선거구 단위, 3행 반복 구조)
# 구조: [헤더행(선거일, 선거구명, 선거인수, 투표수, 투표율, 후보자들, 계, 무효투표수, 기권자수)]
#       [득표수 행]
#       [득표율 행]
# ─────────────────────────────────────────────────────────────────────────────

def parse_format_A(filepath, election_date):
    """2001~2002 summary xls 파싱 → records list"""
    records = []
    try:
        df = pd.read_excel(filepath, header=None, dtype=str)
    except Exception as exc:
        print(f"  [WARN] 읽기 실패 {filepath}: {exc}")
        return records

    # 선거 종류 추출 (파일/시트 제목 행에서)
    election_type = infer_election_type_from_path(filepath)
    if not election_type:
        election_type = "국회의원"  # 2001/2002는 모두 국회의원

    # 헤더 행 찾기: '선거구명' 또는 '선거일' 포함 행
    header_row_idx = None
    for idx, row in df.iterrows():
        row_vals = [str(v).strip() for v in row if str(v).strip() not in ("", "nan")]
        if "선거구명" in row_vals or ("선거일" in row_vals and "선거인수" in row_vals):
            header_row_idx = idx
            break

    if header_row_idx is None:
        print(f"  [WARN] 헤더 행 못 찾음: {filepath}")
        return records

    header = df.iloc[header_row_idx]

    # 후보자 컬럼 위치 찾기 (후보자별 득표수 다음)
    cand_start = None
    cand_end = None
    for col_idx, val in enumerate(header):
        val_str = str(val).strip()
        if "후보자별 득표수" in val_str or "후보자별\n득표수" in val_str:
            cand_start = col_idx
        if "무효" in val_str and "투표" in val_str:
            cand_end = col_idx
            break

    # 데이터 행 처리 (3행씩: 헤더/후보자, 득표수, 득표율)
    data_start = header_row_idx + 1
    row_idx = data_start
    rows = df.values
    n_rows = len(rows)

    while row_idx < n_rows:
        row = rows[row_idx]

        # 선거구명 위치 찾기
        선거구명 = None
        선거인수_val = None
        투표수_val = None
        무효투표수_val = None
        기권수_val = None

        # 첫 번째 비어있지 않은 값이 선거일, 두 번째가 선거구명
        non_empty = [(idx, str(v).strip()) for idx, v in enumerate(row)
                     if str(v).strip() not in ("", "nan")]
        if not non_empty:
            row_idx += 1
            continue

        # 첫 비어있지 않은 셀이 날짜형식이면 그 다음이 선거구명
        first_val = non_empty[0][1]
        if re.match(r'\d{2}\.\d+\.\d+', first_val) or re.match(r'\d{4}-\d{2}-\d{2}', first_val):
            if len(non_empty) >= 2:
                선거구명 = non_empty[1][1]
                # 선거인수: 3번째 비어있지 않은
                if len(non_empty) >= 3:
                    선거인수_val = to_int(non_empty[2][1])
                # 투표수: 4번째
                if len(non_empty) >= 4:
                    투표수_val = to_int(non_empty[3][1])
        else:
            row_idx += 1
            continue

        if not 선거구명:
            row_idx += 1
            continue

        # 후보자 정보는 같은 행(header_row에서 위치 파악한 후보자 컬럼들)
        # 다음 행이 득표수 행
        if row_idx + 1 >= n_rows:
            break

        next_row = rows[row_idx + 1]

        # 후보자 컬럼들: cand_start ~ cand_end (exclusive)
        candidates = []
        if cand_start is not None and cand_end is not None:
            for col_i in range(cand_start, cand_end):
                party_cand_str = str(row[col_i]).strip() if str(row[col_i]).strip() not in ("nan", "") else None
                if party_cand_str and party_cand_str not in ("계", "nan"):
                    party, cand = parse_party_candidate(party_cand_str)
                    if party:
                        vote_val = to_int(next_row[col_i]) if col_i < len(next_row) else None
                        candidates.append((party, cand, vote_val))

        # 무효투표수, 기권수 위치
        for col_i, val in enumerate(header):
            val_str = str(val).strip()
            if "무효" in val_str and "투표" in val_str:
                무효투표수_val = to_int(next_row[col_i]) if col_i < len(next_row) else None
            if "기권" in val_str:
                기권수_val = to_int(next_row[col_i]) if col_i < len(next_row) else None

        # 선거구명에서 시도/구시군 분리 시도
        시도 = ""
        구시군 = 선거구명.strip().replace(" ", "").replace("\n", "")

        for candidate_rec in candidates:
            party, cand, vote_val = candidate_rec
            records.append({
                "선거일": election_date,
                "선거종류": election_type,
                "시도": 시도,
                "구시군": 구시군,
                "읍면동": "",
                "투표구": "",
                "선거구명": 선거구명.replace("\n", "").replace(" ", ""),
                "선거인수": 선거인수_val,
                "투표수": 투표수_val,
                "후보자": cand,
                "정당": party,
                "득표수": vote_val,
                "무효투표수": 무효투표수_val,
                "기권수": 기권수_val,
            })

        row_idx += 3  # 헤더+득표수+득표율 3행씩 건너뜀

    return records


# ─────────────────────────────────────────────────────────────────────────────
# 파서 B: 2005 요약형 (선거구 단위, 복잡한 merged-cell 구조)
# 구조: 시도명, 선거구명 등이 merged되어 있어 NaN 전파
# ─────────────────────────────────────────────────────────────────────────────

def parse_format_B_summary(df, election_date, election_type):
    """2005~2007 summary 시트 파싱 (선거구 단위)"""
    records = []

    # 헤더 행 찾기: '시·도명' 또는 '시도명' 또는 '선거구명' 포함
    header_row_idx = None
    for idx in range(min(10, len(df))):
        row_vals = [str(v).strip() for v in df.iloc[idx] if str(v).strip() not in ("", "nan")]
        if any(v in ("시·도명", "시도명", "선거구명", "선거구분") for v in row_vals):
            header_row_idx = idx
            break

    if header_row_idx is None:
        return records

    header = df.iloc[header_row_idx]

    # 후보자 정보는 header_row + 1 (정당/후보자명 행)
    cand_header_idx = header_row_idx + 1

    # 컬럼 위치 파악
    col_sido = None
    col_district = None
    col_electorate = None
    col_votes = None
    col_invalid = None
    col_abstention = None
    cand_cols = []

    for col_i, val in enumerate(header):
        val_str = str(val).strip()
        if val_str in ("시·도명", "시도명"):
            col_sido = col_i
        elif val_str in ("선거구명", "선거구분"):
            col_district = col_i
        elif "선거인수" in val_str:
            col_electorate = col_i
        elif "투표수" in val_str or "투표자수" in val_str:
            col_votes = col_i
        elif "무효" in val_str and "투표" in val_str:
            col_invalid = col_i
        elif "기권" in val_str:
            col_abstention = col_i
        elif "후보자별 득표수" in val_str or "후보자별\n득표수" in val_str:
            pass

    # 후보자 컬럼 범위: col_invalid 전까지에서 후보자명이 있는 컬럼들
    cand_row = df.iloc[cand_header_idx] if cand_header_idx < len(df) else None

    data_start = header_row_idx + 2
    # Merged cells in pandas read as NaN → forward fill 시도명/선거구명
    prev_sido = ""
    prev_district = ""
    prev_electorate = None
    prev_votes = None
    prev_invalid = None
    prev_abstention = None

    row_idx = data_start
    rows = df.values
    n_rows = len(rows)

    while row_idx < n_rows:
        row = rows[row_idx]

        # 빈 행 건너뜀
        non_empty = [str(v).strip() for v in row if str(v).strip() not in ("", "nan")]
        if not non_empty:
            row_idx += 1
            continue

        # 합계/소계 행 건너뜀
        first_non_empty = non_empty[0] if non_empty else ""
        if first_non_empty in ("계", "합계") or "(득표율)" in first_non_empty:
            row_idx += 1
            continue

        # 시도명
        if col_sido is not None and col_sido < len(row):
            sido_val = str(row[col_sido]).strip()
            if sido_val and sido_val not in ("nan", ""):
                prev_sido = sido_val.replace(" ", "").replace("　", "")
        시도 = prev_sido

        # 선거구명
        if col_district is not None and col_district < len(row):
            dist_val = str(row[col_district]).strip()
            if dist_val and dist_val not in ("nan", ""):
                prev_district = dist_val
        선거구명 = prev_district

        # 선거인수/투표수 - 이 행에 있으면 업데이트
        if col_electorate is not None and col_electorate < len(row):
            e_val = to_int(row[col_electorate])
            if e_val:
                prev_electorate = e_val
        if col_votes is not None and col_votes < len(row):
            v_val = to_int(row[col_votes])
            if v_val:
                prev_votes = v_val
        if col_invalid is not None and col_invalid < len(row):
            inv_val = to_int(row[col_invalid])
            if inv_val:
                prev_invalid = inv_val
        if col_abstention is not None and col_abstention < len(row):
            abs_val = to_int(row[col_abstention])
            if abs_val:
                prev_abstention = abs_val

        # 득표수 행인지 확인: 후보자명이 있는 컬럼에 숫자가 있으면
        if cand_row is not None:
            for col_i, cand_val in enumerate(cand_row):
                cand_str = str(cand_val).strip()
                if cand_str in ("", "nan", "계"):
                    continue
                party, cand_name = parse_party_candidate(cand_str)
                if party and col_i < len(row):
                    # 이 행에 후보자 이름이 있으면 이름 행, 없으면 득표수 행
                    cell_val = str(row[col_i]).strip()
                    if cell_val not in ("", "nan") and not is_number(cell_val):
                        # 이 행이 후보자 이름 행인 경우
                        # 다음 행이 득표수 행
                        if row_idx + 1 < n_rows:
                            next_row = rows[row_idx + 1]
                            vote_val = to_int(next_row[col_i])
                            if vote_val is not None:
                                records.append({
                                    "선거일": election_date,
                                    "선거종류": election_type,
                                    "시도": 시도,
                                    "구시군": "",
                                    "읍면동": "",
                                    "투표구": "",
                                    "선거구명": 선거구명,
                                    "선거인수": prev_electorate,
                                    "투표수": prev_votes,
                                    "후보자": cell_val.strip(),
                                    "정당": party,
                                    "득표수": vote_val,
                                    "무효투표수": prev_invalid,
                                    "기권수": prev_abstention,
                                })
                    elif cell_val not in ("", "nan") and is_number(cell_val):
                        # 이 행이 득표수 행
                        vote_val = to_int(cell_val)
                        records.append({
                            "선거일": election_date,
                            "선거종류": election_type,
                            "시도": 시도,
                            "구시군": "",
                            "읍면동": "",
                            "투표구": "",
                            "선거구명": 선거구명,
                            "선거인수": prev_electorate,
                            "투표수": prev_votes,
                            "후보자": cand_name or cand_str,
                            "정당": party,
                            "득표수": vote_val,
                            "무효투표수": prev_invalid,
                            "기권수": prev_abstention,
                        })

        row_idx += 1

    return records


# ─────────────────────────────────────────────────────────────────────────────
# 파서 C: 투표구별 형식 (2009~) - 표준 형식
# 구조: 2행 헤더(col3:읍면동명, col4:투표구명, col5:선거인수, col6:투표수, 후보자들, 무효투표수, 기권수)
#       - 후보자 컬럼: '정당\n후보자명' 형식
#       - 합계/소계 행 제거
# ─────────────────────────────────────────────────────────────────────────────

def parse_precinct_sheet(df, election_date, election_type, 시도="", 구시군="", 선거구명_override=""):
    """투표구별 시트 파싱 → records list"""
    records = []

    # 헤더 구조 찾기
    # 일반적으로 첫 3~5행이 메타정보, 그 다음이 컬럼 헤더
    header_row1_idx = None
    header_row2_idx = None

    for idx in range(min(8, len(df))):
        row_vals = [str(v).strip() for v in df.iloc[idx] if str(v).strip() not in ("", "nan")]
        if "읍면동명" in row_vals or "투표구명" in row_vals:
            header_row1_idx = idx
            break

    if header_row1_idx is None:
        return records

    header1 = df.iloc[header_row1_idx]
    # 다음 행이 후보자명 행인지 확인
    if header_row1_idx + 1 < len(df):
        next_row_vals = [str(v).strip() for v in df.iloc[header_row1_idx + 1]]
        has_party_cand = any("\n" in v for v in next_row_vals if v not in ("", "nan"))
        if has_party_cand or any(v not in ("", "nan") for v in next_row_vals):
            header_row2_idx = header_row1_idx + 1

    data_start = (header_row2_idx + 1) if header_row2_idx is not None else (header_row1_idx + 1)
    # 빈 행 하나 더 있을 수 있음
    if data_start < len(df):
        test_row = df.iloc[data_start]
        test_vals = [str(v).strip() for v in test_row if str(v).strip() not in ("", "nan")]
        if not test_vals:
            data_start += 1

    # 컬럼 위치 파악
    col_emd = None       # 읍면동명
    col_precinct = None  # 투표구명
    col_electorate = None  # 선거인수
    col_votes = None     # 투표수
    col_invalid = None   # 무효투표수
    col_abstention = None  # 기권수
    col_sido = None      # 시도명 (있는 경우)
    col_sigungu = None   # 구시군명 (있는 경우)
    col_district = None  # 선거구명 (있는 경우)

    for col_i, val in enumerate(header1):
        val_str = str(val).strip()
        if val_str in ("읍면동명", "읍면동"):
            col_emd = col_i
        elif val_str in ("투표구명", "투표구"):
            col_precinct = col_i
        elif "선거인수" in val_str:
            col_electorate = col_i
        elif val_str in ("투표수", "투표자수"):
            col_votes = col_i
        elif "무효" in val_str and "투표" in val_str:
            col_invalid = col_i
        elif "기권" in val_str:
            col_abstention = col_i
        elif val_str in ("시도명", "시·도명"):
            col_sido = col_i
        elif val_str in ("구시군명", "구·시·군명"):
            col_sigungu = col_i
        elif val_str in ("선거구명",):
            col_district = col_i

    if col_electorate is None or col_votes is None:
        return records

    # 후보자 컬럼 파악: header2에서 '정당\n후보자' 형식 찾기
    # 또는 header1에서 '후보자별 득표수' 다음 컬럼들
    cand_cols = []  # (col_i, party, cand_name)

    if header_row2_idx is not None:
        header2 = df.iloc[header_row2_idx]
        for col_i, val in enumerate(header2):
            val_str = str(val).strip().replace("_x000D_", "")
            if val_str in ("", "nan", "계"):
                continue
            party, cand_name = parse_party_candidate(val_str)
            if party and party not in ("계", "후보자별 득표수"):
                cand_cols.append((col_i, party, cand_name or ""))
    else:
        # 헤더가 1행인 경우 (2009 일부 파일)
        # header1에서 후보자명 컬럼 찾기
        for col_i, val in enumerate(header1):
            val_str = str(val).strip()
            if val_str in ("", "nan", "계") or val_str in ("읍면동명", "투표구명", "선거인수", "투표수", "기권수"):
                continue
            if "선거인수" in val_str or "투표수" in val_str or "기권" in val_str or "무효" in val_str:
                continue
            party, cand_name = parse_party_candidate(val_str)
            if party:
                cand_cols.append((col_i, party, cand_name or ""))

    # 3-row header 감지: header2의 모든 cand_name이 빈 경우, 다음 행에서 이름 가져오기
    if cand_cols and all(cand_name == "" for _, _, cand_name in cand_cols) and header_row2_idx is not None:
        next_idx = header_row2_idx + 1
        if next_idx < len(df):
            next_row_vals = [str(v).strip() for v in df.iloc[next_idx] if str(v).strip() not in ("", "nan")]
            num_count = sum(1 for v in next_row_vals if is_number(v.replace(",", "")))
            if next_row_vals and num_count < len(next_row_vals) * 0.3:
                name_row = df.iloc[next_idx]
                updated_cands = []
                for col_i, party, _ in cand_cols:
                    cand_name = ""
                    if col_i < len(name_row):
                        name_val = str(name_row.iloc[col_i]).strip()
                        if name_val and name_val not in ("nan", "", "계"):
                            cand_name = name_val
                    updated_cands.append((col_i, party, cand_name))
                cand_cols = updated_cands
                data_start = next_idx + 1  # name row도 건너뜀

    if not cand_cols:
        return records

    # 선거구명 추출: 상단 메타 행에서 [XXX선거][YYY] 패턴
    meta_선거구명 = 선거구명_override
    meta_시도 = 시도
    meta_구시군 = 구시군

    for idx in range(min(header_row1_idx, 6)):
        row_vals_str = " ".join([str(v).strip() for v in df.iloc[idx]])
        # [국회의원선거][경기도][성남시분당구을] 패턴
        bracket_matches = re.findall(r'\[([^\]]+)\]', row_vals_str)
        if bracket_matches:
            for bm in bracket_matches:
                bm_clean = bm.strip()
                if any(kw in bm_clean for kw in ["선거", "의원", "지사", "장선거"]):
                    if not meta_선거구명:
                        # 다음 bracket이 지역명
                        pass
                    et = normalize_election_type(bm_clean)
                    if et != bm_clean:
                        election_type = et
                elif not meta_시도 and any(kw in bm_clean for kw in ["특별시", "광역시", "도", "특별자치도"]):
                    meta_시도 = bm_clean
                elif not meta_선거구명 and len(bm_clean) > 1:
                    meta_선거구명 = bm_clean

    # 데이터 행 처리
    rows = df.values
    n_rows = len(rows)
    prev_emd = ""
    prev_sido = meta_시도
    prev_sigungu = meta_구시군
    prev_district = meta_선거구명

    for row_idx in range(data_start, n_rows):
        row = rows[row_idx]
        n_cols = len(row)

        # 빈 행 건너뜀
        non_empty = [str(v).strip() for v in row if str(v).strip() not in ("", "nan")]
        if not non_empty:
            continue

        # 시도/구시군 갱신
        if col_sido is not None and col_sido < n_cols:
            v = str(row[col_sido]).strip()
            if v and v not in ("nan", ""):
                prev_sido = v
        if col_sigungu is not None and col_sigungu < n_cols:
            v = str(row[col_sigungu]).strip()
            if v and v not in ("nan", ""):
                prev_sigungu = v
        if col_district is not None and col_district < n_cols:
            v = str(row[col_district]).strip()
            if v and v not in ("nan", ""):
                prev_district = v

        # 읍면동명
        emd_val = ""
        if col_emd is not None and col_emd < n_cols:
            v = str(row[col_emd]).strip()
            if v and v not in ("nan", ""):
                if not is_summary_row(v):
                    prev_emd = v
                emd_val = v

        # 투표구명
        precinct_val = ""
        if col_precinct is not None and col_precinct < n_cols:
            v = str(row[col_precinct]).strip()
            if v and v not in ("nan", ""):
                precinct_val = v

        # 합계/소계 행 건너뜀
        if is_summary_row(emd_val) or is_summary_row(precinct_val):
            continue

        # 읍면동 없고 투표구 없으면 메타행 가능성
        if not emd_val and not precinct_val:
            # 투표구가 없지만 선거인수가 있으면 집계행일 수 있음
            if col_electorate < n_cols:
                elec = to_int(row[col_electorate])
                if elec is None:
                    continue

        # 선거인수/투표수/무효투표수/기권수
        선거인수 = to_int(row[col_electorate]) if col_electorate < n_cols else None
        투표수 = to_int(row[col_votes]) if col_votes < n_cols else None
        무효투표수 = to_int(row[col_invalid]) if col_invalid is not None and col_invalid < n_cols else None
        기권수 = to_int(row[col_abstention]) if col_abstention is not None and col_abstention < n_cols else None

        if 선거인수 is None and 투표수 is None:
            continue

        # 읍면동 이름 결정 (merge된 셀은 위 행에서 전파)
        emd_display = emd_val if emd_val and not is_summary_row(emd_val) else prev_emd

        for col_i, party, cand_name in cand_cols:
            if col_i >= n_cols:
                continue
            vote_val = to_int(row[col_i])
            if vote_val is None:
                vote_raw = str(row[col_i]).strip()
                if vote_raw in ("", "nan", "0"):
                    vote_val = 0 if vote_raw == "0" else None
                else:
                    continue

            records.append({
                "선거일": election_date,
                "선거종류": election_type,
                "시도": prev_sido,
                "구시군": prev_sigungu,
                "읍면동": emd_display,
                "투표구": precinct_val,
                "선거구명": prev_district,
                "선거인수": 선거인수,
                "투표수": 투표수,
                "후보자": cand_name,
                "정당": party,
                "득표수": vote_val,
                "무효투표수": 무효투표수,
                "기권수": 기권수,
            })

    return records


# ─────────────────────────────────────────────────────────────────────────────
# 파서 D: 2017+ 표준형 (시도명/구시군명/선거구명 컬럼이 있는 형식)
# ─────────────────────────────────────────────────────────────────────────────

def parse_format_2017plus(df, election_date, election_type_override=""):
    """2017~2019 format: 시도명/구시군명/선거구명 컬럼 포함"""
    records = []

    # 헤더 행 찾기
    header_row1_idx = None
    for idx in range(min(5, len(df))):
        row_vals = [str(v).strip() for v in df.iloc[idx]]
        if "시도명" in row_vals or "시·도명" in row_vals:
            header_row1_idx = idx
            break

    if header_row1_idx is None:
        return records

    header1 = df.iloc[header_row1_idx]

    # 다음 행: 후보자명 행
    header_row2_idx = header_row1_idx + 1 if header_row1_idx + 1 < len(df) else None

    # 컬럼 위치
    col_sido = None
    col_sigungu = None
    col_district = None  # 선거구명
    col_emd = None
    col_precinct = None
    col_electorate = None
    col_votes = None
    col_invalid = None
    col_abstention = None
    col_election_type = None

    for col_i, val in enumerate(header1):
        val_str = str(val).strip()
        if val_str in ("시도명", "시·도명"):
            col_sido = col_i
        elif val_str in ("구시군명", "구·시·군명"):
            col_sigungu = col_i
        elif val_str == "선거구명":
            col_district = col_i
        elif val_str in ("읍면동명", "읍면동"):
            col_emd = col_i
        elif val_str in ("투표구명", "투표구"):
            col_precinct = col_i
        elif "선거인수" in val_str:
            col_electorate = col_i
        elif val_str in ("투표수", "투표자수"):
            col_votes = col_i
        elif "무효" in val_str and "투표" in val_str:
            col_invalid = col_i
        elif "기권" in val_str:
            col_abstention = col_i
        elif "선거종류" in val_str:
            col_election_type = col_i

    if col_electorate is None or col_votes is None:
        return records

    # 후보자 컬럼
    cand_cols = []
    if header_row2_idx is not None:
        header2 = df.iloc[header_row2_idx]
        for col_i, val in enumerate(header2):
            val_str = str(val).strip().replace("_x000D_", "").replace("\r", "")
            if val_str in ("", "nan", "계"):
                continue
            if col_i == col_sido or col_i == col_sigungu or col_i == col_district:
                continue
            party, cand_name = parse_party_candidate(val_str)
            if party and party not in ("계", "후보자별 득표수", "후보자별"):
                cand_cols.append((col_i, party, cand_name or ""))

    if not cand_cols:
        return records

    # 3-row header 감지: 후보자명이 비어있고 다음 행에 이름만 있는 경우 (2008 형식)
    # header2의 cand 컬럼 값이 모두 정당명 (이름 없음)이면 다음 행에서 이름 가져오기
    header3_idx = None
    if header_row2_idx is not None and all(cand_name == "" for _, _, cand_name in cand_cols):
        next_idx = header_row2_idx + 1
        if next_idx < len(df):
            next_row_vals = [str(v).strip() for v in df.iloc[next_idx] if str(v).strip() not in ("", "nan")]
            # 다음 행이 이름 행인지: 숫자 없고 한글 이름들
            num_count = sum(1 for v in next_row_vals if is_number(v.replace(",", "")))
            if next_row_vals and num_count < len(next_row_vals) * 0.3:
                header3_idx = next_idx
                # 이름 업데이트
                name_row = df.iloc[next_idx]
                updated_cands = []
                for col_i, party, _ in cand_cols:
                    cand_name = ""
                    if col_i < len(name_row):
                        name_val = str(name_row.iloc[col_i]).strip()
                        if name_val and name_val not in ("nan", "", "계"):
                            cand_name = name_val
                    updated_cands.append((col_i, party, cand_name))
                cand_cols = updated_cands

    data_start = (header3_idx + 1 if header3_idx is not None
                  else header_row2_idx + 1 if header_row2_idx is not None
                  else header_row1_idx + 1)
    # 빈 행 건너뜀
    while data_start < len(df):
        test_vals = [str(v).strip() for v in df.iloc[data_start] if str(v).strip() not in ("", "nan")]
        if test_vals:
            break
        data_start += 1

    rows = df.values
    n_rows = len(rows)

    for row_idx in range(data_start, n_rows):
        row = rows[row_idx]
        n_cols = len(row)

        # 빈 행 건너뜀
        non_empty = [str(v).strip() for v in row if str(v).strip() not in ("", "nan")]
        if not non_empty:
            continue

        # 시도/구시군/선거구명
        시도 = str(row[col_sido]).strip() if col_sido is not None and col_sido < n_cols else ""
        구시군 = str(row[col_sigungu]).strip() if col_sigungu is not None and col_sigungu < n_cols else ""
        선거구명 = str(row[col_district]).strip() if col_district is not None and col_district < n_cols else ""
        시도 = "" if 시도 in ("nan", "") else 시도
        구시군 = "" if 구시군 in ("nan", "") else 구시군
        선거구명 = "" if 선거구명 in ("nan", "") else 선거구명

        # 읍면동/투표구명
        emd_val = str(row[col_emd]).strip() if col_emd is not None and col_emd < n_cols else ""
        precinct_val = str(row[col_precinct]).strip() if col_precinct is not None and col_precinct < n_cols else ""
        emd_val = "" if emd_val in ("nan", "") else emd_val
        precinct_val = "" if precinct_val in ("nan", "") else precinct_val

        # 합계/소계 행 건너뜀
        if is_summary_row(emd_val) or is_summary_row(precinct_val):
            continue
        # '합계' 행: 구시군이 비어있고 읍면동이 합계
        if emd_val in ("합계", "") and precinct_val in ("합계", "NaN", "nan", ""):
            # 최상위 합계 행은 건너뜀
            if not emd_val and not precinct_val:
                continue

        # 선거종류
        el_type = election_type_override
        if col_election_type is not None and col_election_type < n_cols:
            et_val = str(row[col_election_type]).strip()
            if et_val not in ("nan", ""):
                el_type = normalize_election_type(et_val)

        선거인수 = to_int(row[col_electorate]) if col_electorate < n_cols else None
        투표수 = to_int(row[col_votes]) if col_votes < n_cols else None
        무효투표수 = to_int(row[col_invalid]) if col_invalid is not None and col_invalid < n_cols else None
        기권수 = to_int(row[col_abstention]) if col_abstention is not None and col_abstention < n_cols else None

        if 선거인수 is None and 투표수 is None:
            continue

        for col_i, party, cand_name in cand_cols:
            if col_i >= n_cols:
                continue
            vote_val = to_int(row[col_i])
            if vote_val is None:
                vote_raw = str(row[col_i]).strip()
                if vote_raw == "0":
                    vote_val = 0
                else:
                    continue

            records.append({
                "선거일": election_date,
                "선거종류": el_type,
                "시도": 시도,
                "구시군": 구시군,
                "읍면동": emd_val,
                "투표구": precinct_val,
                "선거구명": 선거구명,
                "선거인수": 선거인수,
                "투표수": 투표수,
                "후보자": cand_name,
                "정당": party,
                "득표수": vote_val,
                "무효투표수": 무효투표수,
                "기권수": 기권수,
            })

    return records


# ─────────────────────────────────────────────────────────────────────────────
# 파서 E: 2005~2010 선거구 단위 요약형
# 구조: 시도명/선거구명/선거인수/투표수 + 후보자들이 한 행에, 다음 행에 후보자 이름, 그 다음에 득표수
# 선거구 블록은 4행씩 반복: [정당행, 이름행, 득표수행, 득표율행]
# 후보자가 많으면 추가 블록이 아래에 이어짐
# ─────────────────────────────────────────────────────────────────────────────

def parse_constituency_summary(df, election_date, election_type):
    """2005~2010 선거구 단위 요약 시트 파싱"""
    records = []

    # 선거 종류를 상단 메타 행에서도 탐색
    if not election_type:
        for meta_idx in range(min(4, len(df))):
            meta_str = " ".join([str(v).strip() for v in df.iloc[meta_idx]])
            meta_nfc = unicodedata.normalize("NFC", meta_str)
            if "국회의원" in meta_nfc:
                election_type = "국회의원"
                break
            if "기초단체장" in meta_nfc or "기초장" in meta_nfc:
                election_type = "구시군장"
                break
            if "광역의원" in meta_nfc:
                election_type = "시도의회의원"
                break
            if "기초의원" in meta_nfc:
                election_type = "구시군의회의원"
                break

    # 헤더 행 찾기: '시·도명' 또는 '시도명' 포함
    header_row_idx = None
    for idx in range(min(8, len(df))):
        row_str = " ".join([str(v).strip() for v in df.iloc[idx]])
        if any(kw in row_str for kw in ["시·도명", "시도명", "선거구명"]):
            header_row_idx = idx
            break

    if header_row_idx is None:
        return records

    header1 = df.iloc[header_row_idx]
    # 다음 행이 서브헤더(투표율 등)인지 확인
    subheader_idx = header_row_idx + 1
    subheader = df.iloc[subheader_idx] if subheader_idx < len(df) else None

    # 컬럼 위치
    col_gubn = None   # 구분 컬럼 (선거 종류가 행마다 명시된 경우)
    col_sido = None
    col_district = None
    col_electorate = None
    col_votes = None
    col_invalid = None
    col_abstention = None
    cand_start_col = None  # 후보자 시작 컬럼

    for col_i, val in enumerate(header1):
        val_str = str(val).strip()
        if val_str == "구분":
            col_gubn = col_i
        elif val_str in ("시·도명", "시도명"):
            col_sido = col_i
        elif val_str == "선거구명":
            col_district = col_i
        elif "선거인수" in val_str:
            col_electorate = col_i
        elif "투표수" in val_str or "투표자수" in val_str:
            if "무효" not in val_str:
                col_votes = col_i
        elif "무효" in val_str:
            col_invalid = col_i
        elif "기권" in val_str:
            col_abstention = col_i
        elif "후보자별" in val_str:
            cand_start_col = col_i

    if col_electorate is None and col_votes is None:
        return records

    # 후보자 컬럼 범위: cand_start_col ~ col_invalid (exclusive)
    if cand_start_col is None:
        cand_start_col = (col_votes or 0) + 1
    cand_end_col = col_invalid if col_invalid is not None else len(header1)

    data_start = header_row_idx + 2  # 헤더 + 서브헤더 건너뜀

    rows = df.values
    n_rows = len(rows)
    n_cols = df.shape[1]

    # 선거구 블록 파싱
    # 각 선거구는 여러 행으로 구성:
    #   행 A: 시도명, (선거구명), 선거인수, 투표수(투표율%), [정당1\n이름1, ...], 무효투표수, 기권수
    #   행 B: [후보자이름들] (시도/선거구 NaN)
    #   행 C: [득표수들]
    #   행 D: [득표율들]
    #   행 E~: 후보자가 많으면 추가 정당/이름/득표수/득표율 세트 반복

    prev_sido = ""
    prev_district = ""
    prev_electorate = None
    prev_votes = None
    prev_invalid = None
    prev_abstention = None
    current_candidates = []  # (party, name)
    row_idx = data_start

    def flush_candidates(candidates, vote_row_idx):
        """후보자 목록 + 득표수 행 처리"""
        recs = []
        if row_idx_inner >= n_rows:
            return recs
        vote_row = rows[vote_row_idx]
        for col_i, (party, cand_name) in candidates:
            if col_i >= len(vote_row):
                continue
            vote_val = to_int(vote_row[col_i])
            if vote_val is not None:
                recs.append({
                    "선거일": election_date,
                    "선거종류": election_type,
                    "시도": prev_sido_inner,
                    "구시군": "",
                    "읍면동": "",
                    "투표구": "",
                    "선거구명": prev_district_inner,
                    "선거인수": prev_electorate_inner,
                    "투표수": prev_votes_inner,
                    "후보자": cand_name,
                    "정당": party,
                    "득표수": vote_val,
                    "무효투표수": prev_invalid_inner,
                    "기권수": prev_abstention_inner,
                })
        return recs

    # 더 단순한 접근: 선거구 시작을 시도명 또는 선거구명이 있는 행으로 감지
    row_idx = data_start
    current_sido = ""
    current_district = ""
    current_electorate = None
    current_votes = None
    current_invalid = None
    current_abstention = None
    current_cands = []  # [(col_i, party, name)]
    state = "expect_block"  # expect_block | in_cand_names | in_votes | in_pct

    while row_idx < n_rows:
        row = rows[row_idx]
        non_empty_vals = [(i, str(v).strip()) for i, v in enumerate(row)
                          if str(v).strip() not in ("", "nan")]
        non_empty_strs = [v for _, v in non_empty_vals]

        if not non_empty_strs:
            row_idx += 1
            continue

        # 득표율 행 건너뜀 (괄호 숫자나 소수점 숫자들)
        def _is_pct(v):
            if re.match(r'^\([\d.]+\)$', v):
                return True
            if re.match(r'^[\d.]+$', v) and '.' in v:
                try:
                    return float(v.replace(',', '')) <= 100
                except ValueError:
                    return False
            return False
        pct_count = sum(1 for v in non_empty_strs if _is_pct(v))
        if pct_count >= len(non_empty_strs) * 0.6 and pct_count >= 2:
            row_idx += 1
            continue

        # 시도명이 있는 새로운 선거구 블록 시작?
        has_sido = col_sido is not None and col_sido < len(row) and str(row[col_sido]).strip() not in ("", "nan")
        # 선거인수 컬럼에 숫자가 있는지
        has_electorate = (col_electorate is not None and col_electorate < len(row)
                          and to_int(row[col_electorate]) is not None)
        # 투표수 컬럼에 숫자가 있는지
        has_votes = (col_votes is not None and col_votes < len(row)
                     and to_int(row[col_votes]) is not None)

        # 선거구 단위 집계행: 선거인수와 투표수가 모두 있는 행
        if has_electorate or has_votes:
            # 이 행은 새 선거구 블록의 첫 행
            # 구분 컬럼에서 선거 종류 업데이트 (2010 형식)
            if col_gubn is not None and col_gubn < len(row):
                gubn_val = str(row[col_gubn]).strip().replace(" ", "").replace("　", "").replace("\n", "")
                if gubn_val and gubn_val not in ("nan", ""):
                    inferred = infer_election_type_from_sheet(gubn_val)
                    if inferred:
                        election_type = inferred
            if col_sido is not None and col_sido < len(row):
                v = str(row[col_sido]).strip()
                if v and v not in ("nan", ""):
                    current_sido = v.replace(" ", "").replace("　", "")
            if col_district is not None and col_district < len(row):
                v = str(row[col_district]).strip()
                if v and v not in ("nan", ""):
                    current_district = v.replace("\n", "").replace(" ", "")
            if col_electorate is not None and col_electorate < len(row):
                current_electorate = to_int(row[col_electorate])
            if col_votes is not None and col_votes < len(row):
                current_votes = to_int(row[col_votes])
            if col_invalid is not None and col_invalid < len(row):
                inv = to_int(row[col_invalid])
                if inv is not None:
                    current_invalid = inv
            if col_abstention is not None and col_abstention < len(row):
                ab = to_int(row[col_abstention])
                if ab is not None:
                    current_abstention = ab

            # 같은 행에 정당명들이 있을 수 있음 (첫 번째 후보자 그룹)
            current_cands = []
            for col_i in range(cand_start_col, min(cand_end_col, len(row))):
                cell = str(row[col_i]).strip()
                if cell in ("nan", "", "계"):
                    continue
                party, name = parse_party_candidate(cell)
                if party:
                    current_cands.append((col_i, party, name or ""))

            # 다음 행이 후보자 이름 행인지 확인
            if row_idx + 1 < n_rows:
                name_row = rows[row_idx + 1]
                name_row_vals = [str(v).strip() for v in name_row if str(v).strip() not in ("", "nan")]
                # 이름 행: 숫자가 거의 없고 문자열이 대부분
                num_count = sum(1 for v in name_row_vals if is_number(v))
                # 후보자 이름 행이면 (이름들 + 정당 없는 셀들)
                if name_row_vals and num_count < len(name_row_vals) * 0.5:
                    # 이름 행: current_cands에 이름 업데이트
                    if current_cands:
                        updated_cands = []
                        for col_i, party, name in current_cands:
                            if col_i < len(name_row):
                                name_val = str(name_row[col_i]).strip()
                                if name_val and name_val not in ("nan", "", "계"):
                                    name = name_val
                            updated_cands.append((col_i, party, name))
                        current_cands = updated_cands
                        row_idx += 1  # 이름 행 소비

            # 다음 행이 득표수 행
            if row_idx + 1 < n_rows:
                vote_row = rows[row_idx + 1]
                vote_row_vals = [str(v).strip() for v in vote_row if str(v).strip() not in ("", "nan")]
                num_count = sum(1 for v in vote_row_vals if is_number(v.replace(",", "")))
                if num_count >= len(vote_row_vals) * 0.5 and vote_row_vals:
                    for col_i, party, name in current_cands:
                        if col_i >= len(vote_row):
                            continue
                        vote_val = to_int(vote_row[col_i])
                        if vote_val is not None and current_votes is not None:
                            records.append({
                                "선거일": election_date,
                                "선거종류": election_type,
                                "시도": current_sido,
                                "구시군": "",
                                "읍면동": "",
                                "투표구": "",
                                "선거구명": current_district,
                                "선거인수": current_electorate,
                                "투표수": current_votes,
                                "후보자": name,
                                "정당": party,
                                "득표수": vote_val,
                                "무효투표수": current_invalid,
                                "기권수": current_abstention,
                            })
                    row_idx += 1  # 득표수 행 소비

        # 선거인수/투표수 없는 행 - 추가 후보자 그룹인지 확인
        elif current_district and current_votes is not None:
            # 정당명\n이름 형식의 셀이 있는지
            party_cand_count = sum(1 for i, v in non_empty_vals
                                   if "\n" in v and i >= cand_start_col)
            if party_cand_count >= 1:
                add_cands = []
                for col_i in range(cand_start_col, min(cand_end_col, len(row))):
                    cell = str(row[col_i]).strip()
                    if cell in ("nan", "", "계"):
                        continue
                    party, name = parse_party_candidate(cell)
                    if party:
                        add_cands.append((col_i, party, name or ""))

                # 다음 행이 이름 행인지
                if add_cands and row_idx + 1 < n_rows:
                    name_row = rows[row_idx + 1]
                    name_row_vals = [str(v).strip() for v in name_row if str(v).strip() not in ("", "nan")]
                    num_count = sum(1 for v in name_row_vals if is_number(v))
                    if name_row_vals and num_count < len(name_row_vals) * 0.5:
                        updated_cands = []
                        for col_i, party, name in add_cands:
                            if col_i < len(name_row):
                                name_val = str(name_row[col_i]).strip()
                                if name_val and name_val not in ("nan", "", "계"):
                                    name = name_val
                            updated_cands.append((col_i, party, name))
                        add_cands = updated_cands
                        row_idx += 1

                # 다음 행이 득표수 행
                if add_cands and row_idx + 1 < n_rows:
                    vote_row = rows[row_idx + 1]
                    vote_row_vals = [str(v).strip() for v in vote_row if str(v).strip() not in ("", "nan")]
                    num_count = sum(1 for v in vote_row_vals if is_number(v.replace(",", "")))
                    if num_count >= len(vote_row_vals) * 0.5 and vote_row_vals:
                        for col_i, party, name in add_cands:
                            if col_i >= len(vote_row):
                                continue
                            vote_val = to_int(vote_row[col_i])
                            if vote_val is not None:
                                records.append({
                                    "선거일": election_date,
                                    "선거종류": election_type,
                                    "시도": current_sido,
                                    "구시군": "",
                                    "읍면동": "",
                                    "투표구": "",
                                    "선거구명": current_district,
                                    "선거인수": current_electorate,
                                    "투표수": current_votes,
                                    "후보자": name,
                                    "정당": party,
                                    "득표수": vote_val,
                                    "무효투표수": current_invalid,
                                    "기권수": current_abstention,
                                })
                        row_idx += 1  # 득표수 행 소비

        row_idx += 1

    return records


# ─────────────────────────────────────────────────────────────────────────────
# 파서 F: 구형 선거일 컬럼 형식 (2001~2008 일부)
# 구조: 선거일 | 선거구명 | 선거인수 | 투표수 | (후보자들) | 계 | 무효 | 기권
#       다음 행에 득표수, 그 다음에 득표율
# ─────────────────────────────────────────────────────────────────────────────

def parse_old_date_format_sheet(df, election_date, election_type):
    """선거일 컬럼이 있는 구형 요약 형식 파싱"""
    records = []

    # 헤더 행 찾기
    header_row_idx = None
    for idx in range(min(6, len(df))):
        row_vals = [str(v).strip() for v in df.iloc[idx]]
        if "선거일" in row_vals and "선거구명" in row_vals:
            header_row_idx = idx
            break

    if header_row_idx is None:
        return records

    header = df.iloc[header_row_idx].tolist()
    col_district = None
    col_electorate = None
    col_votes = None
    col_invalid = None
    col_abstention = None
    cand_start = None
    cand_end = None

    for col_i, val in enumerate(header):
        val_str = str(val).strip()
        if val_str == "선거구명":
            col_district = col_i
        elif "선거인수" in val_str:
            col_electorate = col_i
        elif "투표수" in val_str and "무효" not in val_str:
            col_votes = col_i
        elif "무효" in val_str:
            col_invalid = col_i
            cand_end = col_i
        elif "기권" in val_str:
            col_abstention = col_i
        elif "후보자별 득표수" in val_str or "후보자별\n득표수" in val_str:
            cand_start = col_i + 1

    if cand_start is None and col_votes is not None:
        cand_start = col_votes + 1

    rows = df.values
    n_rows = len(rows)
    row_idx = header_row_idx + 1

    # 데이터는 3행씩: [선거구명+후보자정당명 행, 득표수 행, 득표율 행]
    while row_idx < n_rows:
        row = rows[row_idx]
        non_empty = [str(v).strip() for v in row if str(v).strip() not in ("", "nan")]
        if not non_empty:
            row_idx += 1
            continue

        # 선거구명 확인
        선거구명 = None
        if col_district is not None and col_district < len(row):
            v = str(row[col_district]).strip()
            if v and v not in ("nan", ""):
                선거구명 = v.replace("\n", "").replace(" ", "")

        if not 선거구명:
            row_idx += 1
            continue

        # 숫자 값들
        선거인수 = to_int(row[col_electorate]) if col_electorate is not None and col_electorate < len(row) else None
        투표수 = to_int(row[col_votes]) if col_votes is not None and col_votes < len(row) else None
        무효투표수 = to_int(row[col_invalid]) if col_invalid is not None and col_invalid < len(row) else None
        기권수 = to_int(row[col_abstention]) if col_abstention is not None and col_abstention < len(row) else None

        # 후보자 정보 수집 (여러 행에 걸쳐있을 수 있음)
        cands = []
        if cand_start is not None and cand_end is not None:
            for col_i in range(cand_start, min(cand_end, len(row))):
                cell = str(row[col_i]).strip()
                if cell in ("nan", "", "계"):
                    continue
                party, name = parse_party_candidate(cell)
                if party:
                    cands.append((col_i, party, name or ""))

        # 다음 행이 득표수 행인지 또는 이름 행인지
        if not cands or row_idx + 1 >= n_rows:
            row_idx += 3
            continue

        next_row = rows[row_idx + 1]
        # 다음 행에 후보자 이름이 있으면 그 다음이 득표수 행
        next_row_vals = [str(v).strip() for v in next_row if str(v).strip() not in ("", "nan")]
        next_num_count = sum(1 for v in next_row_vals if is_number(v.replace(",", "")))

        if next_num_count < len(next_row_vals) * 0.5 and next_row_vals:
            # 이름 행 - 이름 업데이트
            updated_cands = []
            for col_i, party, name in cands:
                if col_i < len(next_row):
                    name_val = str(next_row[col_i]).strip()
                    if name_val and name_val not in ("nan", "", "계"):
                        name = name_val
                updated_cands.append((col_i, party, name))
            cands = updated_cands
            # 득표수 행은 row_idx + 2
            vote_row_offset = 2
        else:
            # 다음 행이 득표수 행
            vote_row_offset = 1

        if row_idx + vote_row_offset < n_rows:
            vote_row = rows[row_idx + vote_row_offset]
            for col_i, party, name in cands:
                if col_i >= len(vote_row):
                    continue
                vote_val = to_int(vote_row[col_i])
                if vote_val is not None:
                    records.append({
                        "선거일": election_date,
                        "선거종류": election_type,
                        "시도": "",
                        "구시군": "",
                        "읍면동": "",
                        "투표구": "",
                        "선거구명": 선거구명,
                        "선거인수": 선거인수,
                        "투표수": 투표수,
                        "후보자": name,
                        "정당": party,
                        "득표수": vote_val,
                        "무효투표수": 무효투표수,
                        "기권수": 기권수,
                    })

        row_idx += 3  # 정당행 + 이름행(선택) + 득표수행 + 득표율행 = 대략 3행

    return records


# ─────────────────────────────────────────────────────────────────────────────
# 파일 처리 디스패처
# ─────────────────────────────────────────────────────────────────────────────

def process_excel_file(filepath, election_date, election_type_hint="",
                       시도="", 구시군="", 선거구명=""):
    """엑셀 파일 처리 → records list"""
    records = []
    try:
        xl = pd.ExcelFile(filepath)
    except Exception as exc:
        print(f"  [WARN] ExcelFile 열기 실패 {filepath}: {exc}")
        return records

    for sheet_name in xl.sheet_names:
        try:
            df = pd.read_excel(filepath, sheet_name=sheet_name, header=None, dtype=str)
        except Exception as exc:
            print(f"  [WARN] 시트 읽기 실패 {filepath}:{sheet_name}: {exc}")
            continue

        if df.empty:
            continue

        # '선거일' 컬럼이 있는 2001~2008 구형 요약 형식 감지
        has_date_col = any("선거일" == str(v).strip() for v in df.iloc[:5].values.flatten())
        if has_date_col:
            # 구형 요약 형식 (선거일, 선거구명, 선거인수, 투표수, 후보자들...)
            el_type = election_type_hint or infer_election_type_from_sheet(sheet_name) or ""
            recs = parse_old_date_format_sheet(df, election_date, el_type)
            records.extend(recs)
            continue

        # 전체 내용을 문자열로 보고 포맷 판별
        all_vals = " ".join([str(v) for v in df.values.flatten()])

        # 시도명 컬럼이 있는 2017+ 형식
        has_sido_col = any("시도명" in str(v).strip() or "시·도명" in str(v).strip()
                           for v in df.iloc[:5].values.flatten())

        # 선거구명 + 투표구명 있는 표준 투표구별 형식
        has_precinct = any("투표구명" in str(v).strip() for v in df.iloc[:8].values.flatten())
        has_emd = any("읍면동명" in str(v).strip() for v in df.iloc[:8].values.flatten())

        # 선거 종류 결정
        el_type = election_type_hint
        if not el_type:
            el_type = infer_election_type_from_sheet(sheet_name)
        if not el_type:
            el_type = infer_election_type_from_path(filepath)
        if not el_type:
            # 시트 헤더에서 [XXX선거] 패턴 탐색
            for row_idx in range(min(5, len(df))):
                row_str = " ".join([str(v).strip() for v in df.iloc[row_idx]])
                bracket_matches = re.findall(r'\[([^\]]+)\]', row_str)
                for bm in bracket_matches:
                    et = normalize_election_type(bm.strip())
                    if et != bm.strip():
                        el_type = et
                        break
                if el_type:
                    break

        # 시트명이 위치명인 경우 구시군 힌트로 사용 (선거 종류 키워드 없는 경우)
        sheet_as_sigungu = ""
        sheet_name_nfc = unicodedata.normalize("NFC", str(sheet_name))
        if not 구시군 and not any(kw in sheet_name_nfc for kw in
                                  ["선거", "의원", "지사", "단체장", "회의원", "대통령",
                                   "국회", "교육감"]):
            # 시트명이 단순 지역명이면 구시군으로 사용
            sheet_as_sigungu = sheet_name_nfc

        if has_sido_col and (has_precinct or has_emd):
            recs = parse_format_2017plus(df, election_date, el_type)
        elif has_precinct or has_emd:
            recs = parse_precinct_sheet(df, election_date, el_type,
                                        시도=시도, 구시군=구시군 or sheet_as_sigungu,
                                        선거구명_override=선거구명)
        else:
            # 요약형: 2005~2010 constituency-level summary (has 시·도명 but no 읍면동/투표구)
            recs = parse_constituency_summary(df, election_date, el_type)

        records.extend(recs)

    return records


# ─────────────────────────────────────────────────────────────────────────────
# 2001~2002 특수 파서 (선거구 요약)
# ─────────────────────────────────────────────────────────────────────────────

def process_old_summary_xls(filepath, election_date):
    """2001~2002 형식 처리"""
    records = []
    try:
        df = pd.read_excel(filepath, header=None, dtype=str)
    except Exception as exc:
        print(f"  [WARN] 읽기 실패 {filepath}: {exc}")
        return records

    election_type = infer_election_type_from_path(filepath)
    if not election_type:
        election_type = "국회의원"

    # 헤더 행 찾기
    header_row_idx = None
    for idx in range(min(5, len(df))):
        row_vals = [str(v).strip() for v in df.iloc[idx]]
        if "선거구명" in row_vals or ("선거일" in row_vals and "투표수" in row_vals):
            header_row_idx = idx
            break

    if header_row_idx is None:
        return records

    header = df.iloc[header_row_idx].tolist()
    col_date_or_district = None
    col_district = None
    col_electorate = None
    col_votes = None
    col_invalid = None
    col_abstention = None

    for col_i, val in enumerate(header):
        val_str = str(val).strip()
        if val_str == "선거일":
            col_date_or_district = col_i
        elif val_str == "선거구명":
            col_district = col_i
        elif "선거인수" in val_str:
            col_electorate = col_i
        elif "투표수" in val_str and "무효" not in val_str:
            col_votes = col_i
        elif "무효" in val_str:
            col_invalid = col_i
        elif "기권" in val_str:
            col_abstention = col_i

    # 후보자 컬럼 탐색: 헤더 다음 행들에서 '정당\n이름' 패턴
    rows = df.values
    n_rows = len(rows)

    # 데이터는 3행씩: 헤더행(후보자들), 득표수 행, 득표율 행
    row_idx = header_row_idx + 1
    while row_idx < n_rows:
        row = rows[row_idx]

        # 선거일/선거구명 확인
        선거구명_val = None
        선거인수_val = None
        투표수_val = None

        # 선거일이 있는 행
        if col_date_or_district is not None:
            date_cell = str(row[col_date_or_district]).strip()
            if date_cell in ("nan", ""):
                row_idx += 1
                continue

        if col_district is not None and col_district < len(row):
            선거구명_val = str(row[col_district]).strip()
            if 선거구명_val in ("nan", ""):
                row_idx += 1
                continue
        else:
            # 두 번째 비어있지 않은 셀
            non_empty_cells = [(i, str(v).strip()) for i, v in enumerate(row)
                               if str(v).strip() not in ("", "nan")]
            if len(non_empty_cells) >= 2:
                선거구명_val = non_empty_cells[1][1]
            else:
                row_idx += 1
                continue

        if col_electorate is not None and col_electorate < len(row):
            선거인수_val = to_int(row[col_electorate])
        if col_votes is not None and col_votes < len(row):
            투표수_val = to_int(row[col_votes])

        # 다음 행이 득표수 행
        if row_idx + 1 >= n_rows:
            break
        vote_row = rows[row_idx + 1]

        # 무효투표수, 기권수
        무효투표수_val = None
        기권수_val = None
        if col_invalid is not None and col_invalid < len(vote_row):
            무효투표수_val = to_int(row[col_invalid])  # 같은 행에 있을 수 있음
        if col_abstention is not None and col_abstention < len(row):
            기권수_val = to_int(row[col_abstention])

        # 후보자 컬럼들: header 행의 후보자 칸
        # '후보자별 득표수' 다음부터 '무효투표수' 전까지
        cand_start = None
        cand_end = col_invalid

        for col_i, val in enumerate(header):
            val_str = str(val).strip()
            if "후보자별 득표수" in val_str or "후보자별\n득표수" in val_str:
                cand_start = col_i + 1
                break

        if cand_start is None:
            # fallback: 투표수 다음부터
            cand_start = (col_votes or 0) + 1

        if cand_end is None:
            cand_end = len(header)

        for col_i in range(cand_start, cand_end):
            if col_i >= len(row):
                continue
            party_cand_str = str(row[col_i]).strip()
            if party_cand_str in ("nan", "", "계"):
                continue
            party, cand_name = parse_party_candidate(party_cand_str)
            if not party:
                continue
            vote_val = to_int(vote_row[col_i]) if col_i < len(vote_row) else None
            if vote_val is None:
                continue

            records.append({
                "선거일": election_date,
                "선거종류": election_type,
                "시도": "",
                "구시군": "",
                "읍면동": "",
                "투표구": "",
                "선거구명": 선거구명_val.replace("\n", "").replace(" ", ""),
                "선거인수": 선거인수_val,
                "투표수": 투표수_val,
                "후보자": cand_name or "",
                "정당": party,
                "득표수": vote_val,
                "무효투표수": 무효투표수_val,
                "기권수": 기권수_val,
            })

        row_idx += 3  # 헤더+득표수+득표율 3행

    return records


# ─────────────────────────────────────────────────────────────────────────────
# 폴더/파일 수집 및 처리
# ─────────────────────────────────────────────────────────────────────────────

def collect_all_files():
    """RAW_DIR 하위의 모든 처리 대상 파일 수집"""
    items = []  # (election_date, filepath, election_type_hint, 시도, 구시군, 선거구명)

    entries = sorted(os.listdir(RAW_DIR))

    for entry in entries:
        entry_path = os.path.join(RAW_DIR, entry)

        # zip 파일 건너뜀
        if entry.endswith(".zip"):
            continue

        election_date = parse_date_from_filename(entry)

        if os.path.isfile(entry_path):
            ext = os.path.splitext(entry)[1].lower()
            if ext == ".hwp":
                skipped_files.append(entry_path)
                continue
            if ext in (".xls", ".xlsx"):
                et_hint = infer_type_from_district_name(entry)
                items.append((election_date, entry_path, et_hint, "", "", ""))
        elif os.path.isdir(entry_path):
            # 재귀적으로 xls/xlsx 파일 수집
            for root, dirs, files in os.walk(entry_path):
                dirs.sort()
                for fname in sorted(files):
                    ext = os.path.splitext(fname)[1].lower()
                    if ext == ".hwp":
                        skipped_files.append(os.path.join(root, fname))
                        continue
                    if ext in (".xls", ".xlsx"):
                        fpath = os.path.join(root, fname)
                        rel_path = os.path.relpath(root, entry_path)
                        # 선거 종류 힌트: 폴더명/파일명에서 추론
                        et_hint = infer_election_type_from_path(os.path.join(rel_path, fname))
                        if not et_hint:
                            et_hint = infer_type_from_district_name(fname)
                        items.append((election_date, fpath, et_hint, "", "", ""))

    return items


# 2014년 7월30일: 선거구명에서 선거 종류 추론을 위한 패턴
# 시/군 단위 → 구시군장, 구 단위 or '을/갑' 포함 → 국회의원
DISTRICT_TYPE_HINTS = {
    # 명확한 국회의원 패턴 (구+을/갑 or 시+을/갑)
    "광산구을": "국회의원", "동작구을": "국회의원", "울산남구을": "국회의원",
    "수원시을": "국회의원", "수원시병": "국회의원", "수원시정": "국회의원",
    "평택시을": "국회의원", "김포시": "국회의원", "대덕구": "국회의원",
    "해운대구기장군갑": "국회의원",
    # 구시군장 패턴 (군 단위)
    "곡성군": "구시군장", "담양군": "구시군장", "영광군": "구시군장",
    "장성군": "구시군장", "함평군": "구시군장", "화순군": "구시군장",
    "태안군": "구시군장", "서산시": "구시군장", "나주시": "구시군장",
    "순천시": "구시군장", "충주시": "구시군장",
}


def infer_type_from_district_name(fname):
    """파일명(투표구별_XXX) 에서 선거구명 추출 후 선거 종류 추론"""
    fname_nfc = unicodedata.normalize("NFC", fname)
    match = re.search(r'투표구별_(.+?)\)', fname_nfc)
    if match:
        district = match.group(1)
        if district in DISTRICT_TYPE_HINTS:
            return DISTRICT_TYPE_HINTS[district]
        # 을/갑/병/정/무 포함 → 국회의원
        if re.search(r'[을갑병정]$', district):
            return "국회의원"
        # 가/나/다 등 기초의원 선거구 패턴
        if re.search(r'[가나다라마바사아자차카타파하]$', district):
            return "구시군의회의원"
        # 군으로 끝나면 구시군장
        if district.endswith("군"):
            return "구시군장"
        # 시로 끝나면 구시군장 (단, 구로 끝나는 경우 제외)
        if re.search(r'[시]$', district) and "구" not in district:
            return "구시군장"
    return ""


SIDO_NAME_MAP = {
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시", "인천": "인천광역시",
    "광주": "광주광역시", "대전": "대전광역시", "울산": "울산광역시", "세종": "세종특별자치시",
    "경기": "경기도", "강원": "강원도", "충북": "충청북도", "충남": "충청남도",
    "전북": "전라북도", "전남": "전라남도", "경북": "경상북도", "경남": "경상남도",
    "제주": "제주특별자치도",
}


def extract_sido_from_path(filepath):
    """파일명에서 시도명 추출 (e.g. 시도지사선거_서울.xlsx → 서울특별시)"""
    fname = unicodedata.normalize("NFC", os.path.basename(filepath))
    # 파일명 끝부분의 _시도명 패턴
    match = re.search(r'_([가-힣]+)\.xlsx?$', fname)
    if match:
        sido_short = match.group(1)
        if sido_short in SIDO_NAME_MAP:
            return SIDO_NAME_MAP[sido_short]
        # 이미 전체 이름인 경우
        for full in SIDO_NAME_MAP.values():
            if sido_short == full or sido_short in full:
                return full
    return ""


def process_file_item(election_date, filepath, election_type_hint, 시도, 구시군, 선거구명):
    """단일 파일 처리"""
    fname = os.path.basename(filepath)
    print(f"  처리중: {os.path.relpath(filepath, RAW_DIR)}")

    # 시도 힌트가 없으면 파일명에서 추출 시도
    if not 시도:
        시도 = extract_sido_from_path(filepath)

    # 2001, 2002: 요약형 (선거구 단위)
    if election_date in ("2001-10-25", "2002-08-08"):
        return process_old_summary_xls(filepath, election_date)

    # 일반 투표구별 파일
    return process_excel_file(filepath, election_date, election_type_hint, 시도, 구시군, 선거구명)


# ─────────────────────────────────────────────────────────────────────────────
# 메인 실행
# ─────────────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)

    print("파일 수집 중...")
    file_items = collect_all_files()
    print(f"총 {len(file_items)}개 파일 발견")
    print(f"HWP 스킵: {len(skipped_files)}개")
    for sf in skipped_files:
        print(f"  SKIP: {os.path.basename(sf)}")

    print("\n처리 시작...")
    date_stats = {}

    for election_date, filepath, et_hint, sido, sigungu, district in file_items:
        recs = process_file_item(election_date, filepath, et_hint, sido, sigungu, district)
        all_records.extend(recs)
        if election_date:
            date_stats[election_date] = date_stats.get(election_date, 0) + len(recs)

    if not all_records:
        print("처리된 레코드가 없습니다.")
        return

    print(f"\n총 레코드 수: {len(all_records)}")

    # DataFrame 생성
    df_out = pd.DataFrame(all_records, columns=FINAL_COLS)

    # 숫자 컬럼 변환
    for col in ["선거인수", "투표수", "득표수", "무효투표수", "기권수"]:
        df_out[col] = pd.to_numeric(df_out[col], errors="coerce").astype("Int64")

    # 문자열 정리
    for col in ["선거일", "선거종류", "시도", "구시군", "읍면동", "투표구", "선거구명", "후보자", "정당"]:
        df_out[col] = df_out[col].fillna("").astype(str).str.strip()

    # 교육감 선거에서 정당/후보자 컬럼이 바뀐 경우 수정
    # (교육감은 무소속 출마, 정당 없이 이름만 있어서 parse_party_candidate가 이름→정당으로 분류)
    edu_null_cand = (df_out["선거종류"] == "교육감") & (df_out["후보자"] == "") & (df_out["정당"] != "")
    if edu_null_cand.any():
        df_out.loc[edu_null_cand, "후보자"] = df_out.loc[edu_null_cand, "정당"]
        df_out.loc[edu_null_cand, "정당"] = "무소속"

    # 다른 선거에서도 후보자 공란 + 정당이 사람 이름처럼 보이는 경우 수정
    # (당명이 아닌 2~4자 한글 이름이 정당 컬럼에 들어있는 경우)
    def looks_like_name(s):
        if not s:
            return False
        s = str(s).strip()
        if len(s) < 2 or len(s) > 5:
            return False
        # 정당 키워드 없는 경우
        party_keywords = ["당", "연합", "통합", "진보", "보수", "민주", "한나라", "국민", "열린",
                          "새누리", "무소속", "자민련", "민노", "의힘", "정의"]
        if any(kw in s for kw in party_keywords):
            return False
        # 한글만 2~4자
        return bool(re.match(r'^[가-힣]{2,4}$', s))

    non_edu_null_cand = (df_out["선거종류"] != "교육감") & (df_out["후보자"] == "") & (df_out["정당"].apply(looks_like_name))
    if non_edu_null_cand.any():
        df_out.loc[non_edu_null_cand, "후보자"] = df_out.loc[non_edu_null_cand, "정당"]
        df_out.loc[non_edu_null_cand, "정당"] = "무소속"

    # 선거종류 null → 선거구명 패턴으로 추론
    null_mask = df_out["선거종류"] == ""
    if null_mask.any():
        def infer_from_district(district):
            if not district:
                return ""
            d = unicodedata.normalize("NFC", str(district))
            if re.search(r'[을갑병정]$', d) or "구을" in d or "구갑" in d:
                return "국회의원"
            if d.endswith("군수") or d.endswith("시장"):
                return "구시군장"
            if re.search(r'[가나다라마바사아자차]\)', d) or re.search(r'\(제\d+선거구\)', d):
                return "구시군의회의원"
            return ""
        inferred = df_out.loc[null_mask, "선거구명"].apply(infer_from_district)
        df_out.loc[null_mask, "선거종류"] = inferred

    # 중복 제거
    before_dedup = len(df_out)
    df_out = df_out.drop_duplicates()
    after_dedup = len(df_out)
    if before_dedup != after_dedup:
        print(f"중복 제거: {before_dedup - after_dedup}행 제거")

    # 정렬
    df_out = df_out.sort_values(["선거일", "선거종류", "시도", "구시군", "읍면동", "투표구"]).reset_index(drop=True)

    # 저장
    df_out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {OUT_CSV}")
    print(f"총 행 수: {len(df_out)}")
    print(f"컬럼: {list(df_out.columns)}")

    print("\n=== 선거일별 통계 ===")
    stats = df_out.groupby(["선거일", "선거종류"]).size().reset_index(name="행수")
    print(stats.to_string(index=False))

    print("\n=== 선거일별 합계 ===")
    stats2 = df_out.groupby("선거일").size().reset_index(name="행수")
    print(stats2.to_string(index=False))


if __name__ == "__main__":
    main()
