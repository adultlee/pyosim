"""5회(2010) 전국동시지방선거 읍면동별 개표결과 파서.

원본은 **선거종류 폴더 → 시도별 .xls**로 정리돼 있다. 6회와 닮았지만(.xls,
다행 헤더 ``정당\\n이름`` 후보 셀, xlrd writeaccess 깨짐) 두 가지가 단순하다.

1. 시도 이름이 경로(폴더·파일명)에 박혀 있어 시도 헤더 갱신이 필요 없다.
2. **2010년엔 사전투표가 없었다.** 따라서 6·7·8회의 관내사전/선거일 분리 행이 없고,
   각 읍면동이 당일 현장투표 1행이다. 특수표는 ``부재자``(거소·우편 격) 하나뿐이고,
   ``잘못투입된투표지``가 일부 파일에 더 있다. 즉 한 구시군의
   ``합계 == 부재자 + Σ읍면동 + 잘못투입``으로 정합한다(원본에서 확인).

관측된 두 가지 파일 레이아웃(컬럼 라벨로 구분, 위치 고정 인덱싱 금지):

- **시도 단위 파일**(시도지사·광역비례·교육감): ``{선거종류}/{NN_시도}.xls`` 한 파일에
  한 시도 전체. 컬럼 ``구시군명·읍면동명·선거인수·투표수·…``. 맨 위 ``{시도}|합계``는
  시도 전체 합계라 버리고, 그 아래 구시군별 ``합계`` 행을 totals로 emit. 숫자는 float
  문자열('8211461.0').

- **구시군 단위 파일**(구시군장·시도의원·구시군의원·기초비례·교육의원): 한 파일이 한
  구시군(또는 그 안 한 선거구). 컬럼에 ``구시군명``이 없고 ``읍면동명``만 있다. 구시군은
  경로에서 얻는다. 한 구시군이 여러 선거구 파일로 쪼개진 경우(시도의원 강남구1..4,
  구시군의원 강남구가..아) 각 파일 ``합계``는 선거구 소계라 구시군 단위로 합산하고,
  읍면동 키 충돌(큰 읍면동이 여러 선거구에 걸침)을 막으려 읍면동에 선거구명을 접두한다.
  숫자는 콤마 문자열('452,744'). 일부 파일은 맨 왼쪽에 빈 컬럼이 하나 있어 데이터가
  오른쪽으로 한 칸 밀린다 → 라벨 기반 컬럼 탐색으로 흡수한다.

선거종류별 경로에서의 구시군/선거구 위치가 다르다:
- 구시군장·기초비례: ``{시도}/{구시군}.xls`` — 구시군=파일명, 선거구 없음.
- 시도의원·구시군의원: ``{시도}/{구시군}/{구시군선거구}.xls`` — 구시군=중간폴더, 선거구=파일명.
- 교육의원: ``{시도}/{선거구}/{구시군}.xls`` — 선거구=중간폴더, 구시군=파일명(한 구시군은
  정확히 한 선거구에만 속하고 그 파일 합계가 곧 구시군 합계).

level 매핑: 읍면동→당일투표(2010년은 현장투표뿐), 부재자→거소선상, 잘못투입된투표지→잘못투입.
"""

import os
import re
import unicodedata
from collections import Counter

import xlrd
import xlrd.book

# 일부 .xls의 WRITEACCESS(작성자 메타) 레코드가 깨져 xlrd가 globals 파싱 중
# UnicodeDecodeError로 죽는다. 셀 데이터와 무관한 메타라 무시한다(6회와 동일).
xlrd.book.Book.handle_writeaccess = lambda self, data: None

# 시도 정식명(OFFICIAL_TOP/validate 키). 5회 파일명·폴더명은 이미 정식명이라 그대로 쓴다.
FULL_SIDO = {
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "경기도", "강원도", "충청북도", "충청남도",
    "전라북도", "전라남도", "경상북도", "경상남도", "제주특별자치도",
}

# 최상위 폴더명(번호 접두 포함) 키워드 → 표준 선거종류
FOLDER_ETYPE = [
    ("시도지사", "시도지사"),
    ("구시군장", "구시군장"),
    ("광역의원비례대표", "광역비례"),
    ("기초의원비례대표", "기초비례"),
    ("시도의원", "시도의원"),
    ("구시군의원", "구시군의원"),
    ("교육감", "교육감"),
    ("교육의원", "교육의원"),
]

# 후보 셀이 정당명만 있는(이름 없는) 비례대표 선거
PARTY_ONLY_TYPES = {"광역비례", "기초비례"}

# 읍면동명 자리의 특수 라벨 → level(또는 합계 처리). 공백 제거 후 비교.
EUPMD_LABEL = "읍면동명"
# 구시군 컬럼 라벨. 대부분 '구시군명'이나 경북 시도지사 파일만 '구시군별'을 쓴다.
COUNTY_LABELS = {"구시군명", "구시군별"}
TOTAL_LABELS = {"합계", "계"}
ABSENTEE_LABEL = "부재자"
KNOWN_OTHER_EUPMD = {"잘못투입된투표지", "잘못투입·구분된투표지"}


def _norm(value):
    if value is None:
        return ""
    return unicodedata.normalize("NFC", str(value)).strip()


def _squash(text):
    """내부 공백 제거(``합   계`` → ``합계``)."""
    return re.sub(r"\s+", "", text)


def _to_int(value):
    """'452,744'·452744·'8211461.0'·8211461.0 → 정수. 빈값·'·'·'-' → None."""
    if value is None:
        return None
    text = unicodedata.normalize("NFC", str(value)).split("\n")[0]
    text = text.replace(",", "").strip()
    if text in ("", "·", "-"):
        return None
    try:
        return int(text)
    except ValueError:
        try:
            return int(float(text))
        except ValueError:
            return None


def _split_party_name(cell):
    """``정당\\n이름`` → (정당, 이름). 마지막 조각=이름, 나머지를 합쳐 정당.
    이름만(교육감·교육의원 무소속) → ('', 이름)."""
    parts = [piece.strip() for piece in cell.split("\n") if piece.strip()]
    if not parts:
        return None, None
    if len(parts) == 1:
        return "", parts[0]
    return "".join(parts[:-1]), parts[-1]


def _read_sheet(filepath):
    """첫 시트(데이터 시트)를 NFC 문자열 2차원으로. 나머지 시트는 비어 있다."""
    workbook = xlrd.open_workbook(filepath)
    sheet = workbook.sheet_by_index(0)
    return [[_norm(sheet.cell_value(row, col)) for col in range(sheet.ncols)]
            for row in range(sheet.nrows)]


def _etype_from_folder(folder):
    for keyword, etype in FOLDER_ETYPE:
        if keyword in folder:
            return etype
    return None


def _column_map(label_row):
    """라벨 행에서 컬럼 인덱스를 찾는다(내부 공백 제거 후 매칭). 위치 고정 금지."""
    columns = {}
    for index, cell in enumerate(label_row):
        label = _squash(cell)
        if label == EUPMD_LABEL:
            columns.setdefault("읍면동", index)
        elif label in COUNTY_LABELS:
            columns.setdefault("구시군", index)
        elif label.startswith("선거인수"):
            columns.setdefault("선거인수", index)
        elif label.startswith("투표수"):
            columns.setdefault("투표수", index)
        elif label.startswith("무효"):
            columns.setdefault("무효투표수", index)
        elif label.startswith("기권"):
            columns.setdefault("기권수", index)
    return columns


def _candidate_header(header_row, cand_start, valid_col, party_only):
    """후보 헤더 행 → {컬럼인덱스: (정당, 후보자)}. 유효표 '계'(valid_col)는 제외."""
    mapping = {}
    for col in range(cand_start, valid_col):
        cell = header_row[col] if col < len(header_row) else ""
        if cell == "" or cell == "계":
            continue
        if party_only:
            mapping[col] = (_squash(cell), None)
        else:
            party, name = _split_party_name(cell)
            if party is not None:
                mapping[col] = (party, name)
    return mapping


def _parse_file(filepath, election_type, sido, county, district):
    """한 .xls를 파싱해 (rows, totals, unrecognized, skip_reason).

    skip_reason: 파일을 통째로 건너뛴 사유 문자열(또는 None). 조용한 누락 방지용.
    rows의 읍면동은 district가 있으면 ``{district} {읍면동}``으로 접두해 같은 구시군
    안에서 키를 유일하게 만든다. county(구시군명)는 시도 단위 파일에선 None으로 들어와
    데이터 행의 구시군명 컬럼에서 채운다.
    """
    sheet_rows = _read_sheet(filepath)
    label_idx = next((index for index, row in enumerate(sheet_rows)
                      if any(_squash(cell) == EUPMD_LABEL for cell in row)), None)
    if label_idx is None:
        return [], [], [], "읍면동명 라벨 행 없음"
    label_row = sheet_rows[label_idx]
    columns = _column_map(label_row)
    eupmd_col = columns.get("읍면동")
    votes_col = columns.get("투표수")
    if eupmd_col is None or votes_col is None:
        return [], [], [], "읍면동/투표수 컬럼 못 찾음"
    electorate_col = columns.get("선거인수")
    invalid_col = columns.get("무효투표수")
    abstain_col = columns.get("기권수")
    county_col = columns.get("구시군")  # 시도 단위 파일에만 존재
    party_only = election_type in PARTY_ONLY_TYPES

    cand_start = votes_col + 1
    # 유효표 '계' 컬럼: 후보 헤더 행(라벨 행 다음)에서 '계'를 찾는다. 없으면 무효 앞.
    header_row = sheet_rows[label_idx + 1] if label_idx + 1 < len(sheet_rows) else []
    valid_col = next((index for index in range(cand_start, len(header_row))
                      if header_row[index] == "계"), None)
    if valid_col is None and invalid_col is not None:
        valid_col = invalid_col - 1
    if valid_col is None:
        return [], [], [], "유효표 '계' 컬럼 못 찾음"
    candidates = _candidate_header(header_row, cand_start, valid_col, party_only)
    if not candidates:
        return [], [], [], "후보 헤더 없음"

    rows, totals, unrecognized = [], [], []
    current_county = county  # 구시군 단위 파일이면 경로에서 고정, 시도 파일이면 행마다 갱신

    def emit_leaf(eupmd_raw, level, source_row, county_name):
        electorate = None
        if level == "당일투표" and electorate_col is not None and electorate_col < len(source_row):
            electorate = _to_int(source_row[electorate_col])
        precinct = f"{district} {_norm(eupmd_raw)}" if district else _norm(eupmd_raw)
        turnout = _to_int(source_row[votes_col]) if votes_col < len(source_row) else None
        invalid = (_to_int(source_row[invalid_col])
                   if invalid_col is not None and invalid_col < len(source_row) else None)
        abstain = (_to_int(source_row[abstain_col])
                   if abstain_col is not None and abstain_col < len(source_row) else None)
        for col, (party, name) in candidates.items():
            rows.append({
                "선거_회차": 5, "선거종류": election_type, "시도": sido,
                "구시군": county_name, "읍면동": precinct, "선거구명": district,
                "선거인수": electorate, "투표수": turnout, "후보자": name,
                "정당": party,
                "득표수": _to_int(source_row[col]) if col < len(source_row) else None,
                "무효투표수": invalid, "기권수": abstain, "level": level,
            })

    for row in sheet_rows[label_idx + 2:]:
        if eupmd_col >= len(row):
            continue
        eupmd = _squash(row[eupmd_col])
        if eupmd == "":
            continue
        # 시도 단위 파일: 구시군명 컬럼으로 현재 구시군 추적.
        county_name = current_county
        if county_col is not None and county_col < len(row) and _norm(row[county_col]):
            county_name = _norm(row[county_col])

        if eupmd in TOTAL_LABELS:
            # 시도 전체 합계(구시군명 == 시도명)는 버린다. 그 외는 구시군 합계 → totals.
            is_province_total = (county_col is not None and county_name == sido)
            if not is_province_total:
                totals.append({
                    "선거종류": election_type, "시도": sido,
                    "구시군": county_name, "level": None,
                    "투표수": _to_int(row[votes_col]) if votes_col < len(row) else None,
                })
            continue

        if eupmd == ABSENTEE_LABEL:
            emit_leaf(row[eupmd_col], "거소선상", row, county_name)
        elif eupmd in KNOWN_OTHER_EUPMD:
            emit_leaf(row[eupmd_col], "잘못투입", row, county_name)
        else:
            # 일반 읍면동(당일 현장투표). 알 수 없는 라벨이면 unrecognized.
            if re.search(r"(동|읍|면|출장소|리)$", eupmd):
                emit_leaf(row[eupmd_col], "당일투표", row, county_name)
            else:
                unrecognized.append({
                    "선거종류": election_type, "시도": sido,
                    "구시군": county_name, "읍면동": _norm(row[eupmd_col]), "구분": ""})

    return rows, totals, unrecognized, None


def _context_from_path(filepath, base_dir, election_type):
    """파일 경로에서 (시도, 구시군, 선거구)를 유추한다. 선거종류별로 위치가 다르다.

    경로 구조: base_dir/{선거종류폴더}/{NN_시도}[.xls | /...].
    - 시도지사·광역비례·교육감: base/folder/{NN_시도}.xls — 구시군은 파일 안 컬럼에 있어
      None, 선거구 없음.
    - 구시군장·기초비례: base/folder/{NN_시도}/{구시군}.xls — 구시군=파일명, 선거구 없음.
    - 시도의원·구시군의원: base/folder/{NN_시도}/{구시군}/{선거구}.xls —
      구시군=중간폴더, 선거구=파일명.
    - 교육의원: base/folder/{NN_시도}/{선거구}/{구시군}.xls —
      선거구=중간폴더, 구시군=파일명.
    """
    rel = unicodedata.normalize("NFC", os.path.relpath(filepath, base_dir))
    parts = rel.split(os.sep)
    # parts[0] = 선거종류 폴더, parts[1] = NN_시도(폴더 또는 파일명)
    sido = _sido_from_text(parts[1])
    filename = os.path.splitext(parts[-1])[0]
    depth = len(parts)  # 폴더+파일 토막 수

    if depth == 2:
        # 시도 단위 파일(구시군명 컬럼이 파일 안에 있음)
        return sido, None, None
    if election_type == "교육의원":
        # base/folder/시도/선거구/구시군.xls
        district = parts[2] if depth >= 4 else None
        county = filename
        return sido, county, district
    if depth == 3:
        # base/folder/시도/구시군.xls (구시군장·기초비례)
        return sido, filename, None
    # depth >= 4: base/folder/시도/구시군/선거구.xls (시도의원·구시군의원)
    county = parts[2]
    district = filename
    return sido, county, district


def _sido_from_text(text):
    text = unicodedata.normalize("NFC", text)
    for full in FULL_SIDO:
        if full in text:
            return full
    return None


def parse_5th(base_dir):
    """5회 지방선거 디렉터리(선거종류 폴더 → 시도별 .xls)를 모두 파싱한다.

    반환: (rows, totals)
    - rows: 15개 스키마 컬럼의 tidy dict 리스트(선거일은 오케스트레이터가 채움).
    - totals: 구시군 합계 {선거종류,시도,구시군,level,투표수} 리스트. 한 구시군이 여러
      선거구 파일로 쪼개진 경우 합계를 구시군 단위로 합산해 한 항목으로 낸다.
    """
    all_rows = []
    totals_by_key = {}
    all_unrecognized = []
    all_skipped = []

    def add_total(total):
        key = (total["선거종류"], total["시도"], total["구시군"])
        bucket = totals_by_key.setdefault(key, {
            "선거종류": total["선거종류"], "시도": total["시도"],
            "구시군": total["구시군"], "level": None, "투표수": 0})
        bucket["투표수"] += total["투표수"] or 0

    base_dir = unicodedata.normalize("NFC", base_dir)
    for root, _dirs, files in os.walk(base_dir):
        for filename in sorted(files):
            if not filename.lower().endswith(".xls"):
                continue
            filepath = os.path.join(root, filename)
            nfc_name = unicodedata.normalize("NFC",
                                             os.path.relpath(filepath, base_dir))
            folder = nfc_name.split(os.sep)[0]
            election_type = _etype_from_folder(folder)
            if election_type is None:
                all_skipped.append({"선거종류": None, "시도": None, "구시군": None,
                                    "source": nfc_name, "reason": "선거종류 폴더 미인식"})
                continue
            sido, county, district = _context_from_path(filepath, base_dir, election_type)
            if sido is None:
                all_skipped.append({"선거종류": election_type, "시도": None,
                                    "구시군": county, "source": nfc_name,
                                    "reason": "시도 식별 실패"})
                continue
            try:
                file_rows, file_totals, file_unrec, skip = _parse_file(
                    filepath, election_type, sido, county, district)
            except Exception as error:
                all_skipped.append({"선거종류": election_type, "시도": sido,
                                    "구시군": county, "source": nfc_name,
                                    "reason": f"읽기/파싱 실패: {error}"})
                continue
            if skip is not None:
                all_skipped.append({"선거종류": election_type, "시도": sido,
                                    "구시군": county, "source": nfc_name, "reason": skip})
                continue
            all_rows.extend(file_rows)
            for total in file_totals:
                add_total(total)
            all_unrecognized.extend(file_unrec)

    if all_unrecognized:
        _warn_unrecognized(all_unrecognized)
    if all_skipped:
        _warn_skipped(all_skipped)

    return all_rows, list(totals_by_key.values())


def _warn_unrecognized(unrecognized):
    """미인식 행을 (선거종류/시도/구시군/읍면동)별로 집계해 경고. 정상이면 0건."""
    counts = Counter(
        (row["선거종류"], row["시도"], row["구시군"], row["읍면동"])
        for row in unrecognized)
    print(f"[parse_5th] 경고: 미인식 행 {len(unrecognized)}건 "
          f"({len(counts)}종)을 emit 하지 않고 건너뜀:")
    for (etype, sido, county, eupmd), count in counts.most_common(30):
        print(f"  {count:6d}회  선거종류={etype} 시도={sido} 구시군={county} "
              f"읍면동={eupmd!r}")


def _warn_skipped(skipped):
    """파일을 통째로 건너뛴 경우를 사유별로 집계해 경고. 정상이면 0건."""
    counts = Counter(
        (block["reason"], block["선거종류"], block["시도"], block["구시군"])
        for block in skipped)
    print(f"[parse_5th] 경고: 파일 통째 건너뜀 {len(skipped)}건 "
          f"({len(counts)}종) — 데이터 누락 의심, 헤더/경로 매칭 점검 필요:")
    for (reason, etype, sido, county), count in counts.most_common(30):
        sample = next(block["source"] for block in skipped
                      if block["reason"] == reason and block["선거종류"] == etype
                      and block["시도"] == sido and block["구시군"] == county)
        print(f"  {count:4d}파일  사유={reason} 선거종류={etype} 시도={sido} "
              f"구시군={county} 예시={sample!r}")
