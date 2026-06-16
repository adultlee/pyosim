"""4회(2006) 전국동시지방선거 읍면동별 개표결과 파서.

원본은 **선거종류 폴더 → 시도 폴더(코드_약칭) → 구시군별 .xls** 한 파일이 한 구시군
(또는 그 안 한 선거구)을 담는다. 5회와 매우 닮았다(.xls, 다행 헤더 ``정당\\n이름``
후보 셀, xlrd writeaccess 깨짐, 2006년엔 사전투표가 없어 부재자만 특수표). 다만 두 가지가
다르다.

1. 식별자가 전부 경로·파일명에 박혀 있다. 선거종류=race 폴더, 시도=시도 폴더 약칭,
   구시군=파일명 가운데 토막(``{코드}_{구시군}_{식별자}.xls``). 식별자 토막은
   지역구시도의원·지역구기초의원·교육의원에서 ``선거구``라서, 한 구시군이 여러 선거구
   파일로 쪼개진다 → 읍면동 키 충돌(부재자·잘못투입된투표지가 선거구마다 반복)을 막으려
   읍면동에 선거구명을 접두하고, 선거구 ``합계``를 구시군 단위로 합산한다(5회와 동일).
2. 읍면동이 많은 구시군/선거구는 한 시트가 **여러 블록**으로 쪼개진다(태그·라벨·후보
   헤더가 중간에 다시 나옴). 합계·부재자는 첫 블록에 한 번만 있고 뒤 블록은 읍면동
   연속이다(원본 840개 다중블록 파일 전수 확인). 그래서 블록을 형식적으로 나누지 않고
   시트 전체를 훑되 라벨/태그/후보헤더 잔재 행만 건너뛴다.

관측된 ROW 구조(라벨 기반 컬럼 탐색, 위치 고정 금지 — 선거종류별로 빈 컬럼 위치가 달라
투표수 컬럼이 col3~col5로 흔들린다):
- 상단: ``[선거종류]``/``[구시군]`` 대괄호 태그 행(데이터 아님).
- 라벨 행: ``읍면동명·선거인수·투표수·후보자별 득표수·무효투표수·기권수``.
- 후보 헤더 행: 셀 ``정당\\n이름``(비례는 정당만, 교육의원은 이름만). 유효표 '계'는 제외.
- 데이터: ``합계``(구시군/선거구 총계 → totals, rows에 안 냄), ``부재자``(거소·우편 격),
  ``잘못투입된투표지``, 그 외 읍면동(전부 당일 현장투표 1행).

level 매핑: 읍면동→당일투표(2006년은 현장투표뿐), 부재자→거소선상,
잘못투입된투표지→잘못투입. 한 구시군/선거구 ``합계 == 부재자 + Σ읍면동 + 잘못투입``으로
정합한다(원본에서 확인).
"""

import os
import re
import unicodedata
from collections import Counter

import xlrd
import xlrd.book

# 일부 .xls의 WRITEACCESS(작성자 메타) 레코드가 깨져 xlrd가 globals 파싱 중
# UnicodeDecodeError로 죽는다. 셀 데이터와 무관한 메타라 무시한다(5·6회와 동일).
xlrd.book.Book.handle_writeaccess = lambda self, data: None

# 시도 폴더 약칭(코드_약칭) → 정식 시도명(validate/OFFICIAL_TOP 키)
ABBR_TO_SIDO = {
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시",
    "인천": "인천광역시", "광주": "광주광역시", "대전": "대전광역시",
    "울산": "울산광역시", "경기": "경기도", "강원": "강원도",
    "충북": "충청북도", "충남": "충청남도", "전북": "전라북도",
    "전남": "전라남도", "경북": "경상북도", "경남": "경상남도",
    "제주": "제주특별자치도",
}
FULL_SIDO = set(ABBR_TO_SIDO.values())
# 8_교육의원 시도 폴더만 약칭이 아니라 '제주도'다(2006년 교육의원은 제주에서만 직선).
NAME_TO_SIDO = {"제주도": "제주특별자치도"}

# 최상위 race 폴더명(번호 접두 포함) 키워드 → 표준 선거종류
FOLDER_ETYPE = [
    ("시도지사", "시도지사"),
    ("구시군장", "구시군장"),
    ("비례대표시도의원", "광역비례"),
    ("비례대표기초의원", "기초비례"),
    ("지역구시도의원", "시도의원"),
    ("지역구기초의원", "구시군의원"),
    ("교육의원", "교육의원"),
]

# 후보 셀이 정당명만 있는(이름 없는) 비례대표 선거
PARTY_ONLY_TYPES = {"광역비례", "기초비례"}

EUPMD_LABEL = "읍면동명"
TOTAL_LABELS = {"합계", "계"}
ABSENTEE_LABEL = "부재자"
KNOWN_OTHER_EUPMD = {"잘못투입된투표지", "잘못투입·구분된투표지"}
# 후보 헤더의 빈 슬롯 표식(군산시장 등). 출마자 수보다 칸이 많을 때 ``후보자``로 채워
# 둔다 → 유효표 '계'처럼 후보가 아니다(squash 후 비교).
CANDIDATE_PLACEHOLDER = "후보자"
# 무투표당선 선거구 파일의 유일한 데이터 행. 후보·득표·합계가 전혀 없다(정상적 빈 파일).
NO_DATA_MARK = "해당데이타가없습니다."
# 무투표 파일의 skip 사유. '누락 의심' 경고와 분리해 정상 무투표로 집계한다.
NO_DATA_SKIP_REASON = "무투표(데이터 없음)"


def _norm(value):
    if value is None:
        return ""
    return unicodedata.normalize("NFC", str(value)).strip()


def _squash(text):
    """내부 공백 제거(``합   계``·``선거\\n인수`` → ``합계``·``선거인수``)."""
    return re.sub(r"\s+", "", text)


def _to_int(value):
    """'452,744'·452744·'73.0'·73.0 → 정수. 빈값·'·'·'-' → None."""
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
    이름만(교육의원 무소속 후보) → ('', 이름)."""
    parts = [piece.strip() for piece in cell.split("\n") if piece.strip()]
    if not parts:
        return None, None
    if len(parts) == 1:
        return "", parts[0]
    return "".join(parts[:-1]), parts[-1]


def _read_sheet(filepath):
    """첫 시트(데이터 시트)를 NFC 문자열 2차원으로."""
    workbook = xlrd.open_workbook(filepath)
    sheet = workbook.sheet_by_index(0)
    return [[_norm(sheet.cell_value(row, col)) for col in range(sheet.ncols)]
            for row in range(sheet.nrows)]


def _etype_from_folder(folder):
    for keyword, etype in FOLDER_ETYPE:
        if keyword in folder:
            return etype
    return None


def _sido_from_folder(folder):
    """시도 폴더명(``11_서울``·``제주도``) → 정식 시도명."""
    text = unicodedata.normalize("NFC", folder)
    if text in NAME_TO_SIDO:
        return NAME_TO_SIDO[text]
    abbr = text.split("_")[-1]
    return ABBR_TO_SIDO.get(abbr)


def _column_map(label_row):
    """라벨 행에서 컬럼 인덱스를 찾는다(내부 공백 제거 후 매칭). 위치 고정 금지."""
    columns = {}
    for index, cell in enumerate(label_row):
        label = _squash(cell)
        if label == EUPMD_LABEL:
            columns.setdefault("읍면동", index)
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
    """후보 헤더 행 → {컬럼인덱스: (정당, 후보자)}. 유효표 '계'·빈 슬롯 '후보자'는 제외.

    같은 (정당,후보자)가 한 파일에 둘 이상이면(창녕군 가선거구: 무소속 김우식 동명이인
    2명) KEY_COLS 충돌을 막으려 둘째부터 이름에 ``(2)``…를 붙여 유일하게 만든다. 각
    컬럼은 별개 후보라 득표는 그대로 합산된다."""
    mapping = {}
    seen = Counter()
    for col in range(cand_start, valid_col):
        cell = header_row[col] if col < len(header_row) else ""
        if cell == "" or cell == "계" or _squash(cell) == CANDIDATE_PLACEHOLDER:
            continue
        if party_only:
            party, name = _squash(cell), None
        else:
            party, name = _split_party_name(cell)
            if party is None:
                continue
        key = (party, name)
        seen[key] += 1
        if name is not None and seen[key] > 1:
            name = f"{name}({seen[key]})"  # 동명이인 N번째 → 이름(N)
        mapping[col] = (party, name)
    return mapping


def _context_from_path(filepath, base_dir):
    """경로·파일명에서 (선거종류, 시도, 구시군, 선거구)를 유추한다.

    경로: base_dir/{race 폴더}/{NN_시도}/{코드_구시군_식별자}.xls
    - 선거종류 = race 폴더, 시도 = 시도 폴더 약칭.
    - 구시군 = 파일명 가운데 토막(token[1]).
    - 선거구 = 파일명 마지막 토막(token[2]). 단 시도명·구시군명과 같으면(시도지사·
      구시군장·비례) 선거구가 없는 것이라 None. 다르면(지역구·교육의원) 선거구로 쓴다.
    """
    rel = unicodedata.normalize("NFC", os.path.relpath(filepath, base_dir))
    parts = rel.split(os.sep)
    race_folder = parts[0]
    sido_folder = parts[1] if len(parts) >= 2 else ""
    election_type = _etype_from_folder(race_folder)
    sido = _sido_from_folder(sido_folder)

    stem = unicodedata.normalize("NFC", os.path.splitext(parts[-1])[0])
    tokens = stem.split("_")
    county = tokens[1] if len(tokens) >= 2 else None
    last = tokens[2] if len(tokens) >= 3 else ""
    # 식별자 토막이 구시군명·시도명(약칭·정식)과 같으면 선거구 없음.
    district = None
    if last and last != county and last not in FULL_SIDO \
            and _sido_from_folder("_" + last) is None and last not in NAME_TO_SIDO:
        district = last
    return election_type, sido, county, district


def _parse_file(filepath, election_type, sido, county, district):
    """한 .xls를 파싱해 (rows, totals, unrecognized, skip_reason).

    skip_reason: 파일을 통째로 건너뛴 사유(또는 None). 조용한 누락 방지용.
    여러 블록이 한 시트에 쌓인 파일은 첫 라벨 행에서 컬럼·후보 헤더를 잡고 시트 전체를
    훑는다(합계·부재자는 첫 블록에 한 번만, 뒤 블록은 읍면동 연속). 읍면동은 district가
    있으면 ``{district} {읍면동}``으로 접두해 같은 구시군 안에서 키를 유일하게 만든다.
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
    # 무투표당선 선거구: 데이터 영역에 '해당 데이타가 없습니다.' 한 행만 있고 후보·득표·
    # 합계가 전혀 없다. 정상적 빈 파일이지만 조용히 사라지지 않도록 사유를 남겨
    # 호출부가 '누락 의심'과 분리해 무투표로 집계·보고한다.
    if any(eupmd_col < len(row) and _squash(row[eupmd_col]) == NO_DATA_MARK
           for row in sheet_rows[label_idx + 1:]):
        return [], [], [], NO_DATA_SKIP_REASON

    electorate_col = columns.get("선거인수")
    invalid_col = columns.get("무효투표수")
    abstain_col = columns.get("기권수")
    party_only = election_type in PARTY_ONLY_TYPES

    cand_start = votes_col + 1
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

    def emit_leaf(eupmd_raw, level, source_row):
        electorate = None
        if level == "당일투표" and electorate_col is not None \
                and electorate_col < len(source_row):
            electorate = _to_int(source_row[electorate_col])
        precinct = f"{district} {_norm(eupmd_raw)}" if district else _norm(eupmd_raw)
        turnout = _to_int(source_row[votes_col]) if votes_col < len(source_row) else None
        invalid = (_to_int(source_row[invalid_col])
                   if invalid_col is not None and invalid_col < len(source_row) else None)
        abstain = (_to_int(source_row[abstain_col])
                   if abstain_col is not None and abstain_col < len(source_row) else None)
        for col, (party, name) in candidates.items():
            rows.append({
                "선거_회차": 4, "선거종류": election_type, "시도": sido,
                "구시군": county, "읍면동": precinct, "선거구명": district,
                "선거인수": electorate, "투표수": turnout, "후보자": name,
                "정당": party,
                "득표수": _to_int(source_row[col]) if col < len(source_row) else None,
                "무효투표수": invalid, "기권수": abstain, "level": level,
            })

    # 시트 전체를 훑는다(다중 블록 흡수). 라벨/태그/후보헤더 잔재 행은 건너뛴다.
    for row in sheet_rows[label_idx + 1:]:
        if eupmd_col >= len(row):
            continue
        raw = row[eupmd_col]
        eupmd = _squash(raw)
        if eupmd == "" or eupmd == EUPMD_LABEL or raw.startswith("["):
            continue  # 빈칸·다음 블록 라벨·대괄호 태그 잔재

        if eupmd in TOTAL_LABELS:
            # 구시군/선거구 합계 → totals(rows엔 안 냄). 여러 선거구 파일이면 호출부가
            # 구시군 단위로 합산한다.
            totals.append({
                "선거종류": election_type, "시도": sido, "구시군": county,
                "level": None,
                "투표수": _to_int(row[votes_col]) if votes_col < len(row) else None,
            })
        elif eupmd == ABSENTEE_LABEL:
            emit_leaf(raw, "거소선상", row)
        elif eupmd in KNOWN_OTHER_EUPMD:
            emit_leaf(raw, "잘못투입", row)
        elif re.search(r"(동|읍|면|출장소|리)$", eupmd):
            emit_leaf(raw, "당일투표", row)
        else:
            # 알 수 없는 라벨 — emit 하지 않고 경고 대상으로 모은다(조용한 누락 금지).
            unrecognized.append({
                "선거종류": election_type, "시도": sido, "구시군": county,
                "읍면동": _norm(raw)})

    return rows, totals, unrecognized, None


def parse_4th(base_dir):
    """4회 지방선거 디렉터리(race 폴더 → 시도 폴더 → 구시군별 .xls)를 모두 파싱한다.

    반환: (rows, totals)
    - rows: 15개 스키마 컬럼의 tidy dict 리스트(선거일은 오케스트레이터가 채움).
    - totals: 구시군 합계 {선거종류,시도,구시군,level,투표수} 리스트. 한 구시군이 여러
      선거구 파일로 쪼개진 경우(시도의원·구시군의원·교육의원) 선거구 합계를 구시군 단위로
      합산해 한 항목으로 낸다.
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
            election_type, sido, county, district = \
                _context_from_path(filepath, base_dir)
            if election_type is None:
                all_skipped.append({"선거종류": None, "시도": sido, "구시군": county,
                                    "source": nfc_name, "reason": "선거종류 폴더 미인식"})
                continue
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

    # 무투표(정상 빈 파일)와 누락 의심(에러)을 분리해 보고한다.
    no_data = [block for block in all_skipped
               if block["reason"] == NO_DATA_SKIP_REASON]
    suspect = [block for block in all_skipped
               if block["reason"] != NO_DATA_SKIP_REASON]
    if all_unrecognized:
        _warn_unrecognized(all_unrecognized)
    if suspect:
        _warn_skipped(suspect)
    if no_data:
        print(f"[parse_4th] 무투표(데이터 없음) 파일 {len(no_data)}건 통과 — 정상")

    return all_rows, list(totals_by_key.values())


def _warn_unrecognized(unrecognized):
    """미인식 행을 (선거종류/시도/구시군/읍면동)별로 집계해 경고. 정상이면 0건."""
    counts = Counter(
        (row["선거종류"], row["시도"], row["구시군"], row["읍면동"])
        for row in unrecognized)
    print(f"[parse_4th] 경고: 미인식 행 {len(unrecognized)}건 "
          f"({len(counts)}종)을 emit 하지 않고 건너뜀:")
    for (etype, sido, county, eupmd), count in counts.most_common(30):
        print(f"  {count:6d}회  선거종류={etype} 시도={sido} 구시군={county} "
              f"읍면동={eupmd!r}")


def _warn_skipped(skipped):
    """파일을 통째로 건너뛴 경우를 사유별로 집계해 경고. 정상이면 0건."""
    counts = Counter(
        (block["reason"], block["선거종류"], block["시도"], block["구시군"])
        for block in skipped)
    print(f"[parse_4th] 경고: 파일 통째 건너뜀 {len(skipped)}건 "
          f"({len(counts)}종) — 데이터 누락 의심, 헤더/경로 매칭 점검 필요:")
    for (reason, etype, sido, county), count in counts.most_common(30):
        sample = next(block["source"] for block in skipped
                      if block["reason"] == reason and block["선거종류"] == etype
                      and block["시도"] == sido and block["구시군"] == county)
        print(f"  {count:4d}파일  사유={reason} 선거종류={etype} 시도={sido} "
              f"구시군={county} 예시={sample!r}")
