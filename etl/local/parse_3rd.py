"""3회(2002) 전국동시지방선거 투표구별 개표결과 파서.

3회는 역대 가장 까다로운 원본이다. 두 가지 파일 구조(A형·B형)가 섞여 있고, B형은
한글이 cp949였다가 latin1로 잘못 읽혀 모지바케(``ÅõÇ¥±¸¸í``)로 들어온다. 게다가 한
파일 안에 여러 선거구 블록이 쌓여 있고(시도의원·구시군의원), 블록마다 후보 집합과
``계`` 컬럼 위치가 다르다. 단위도 읍면동보다 더 잘게 쪼갠 **투표구**(``청운동제1투``)다.

## A형 (시도지사·광역비례): 파일 = 한 시도, 한글 정상 인코딩
- col0=위원회명(=구시군, carry-forward), col1=투표구명, col2=선거인수, col3=투표수,
  col4+=후보 득표, 그 뒤 ``계``.
- 후보 헤더는 라벨 행 다음다음 행(``한나라당 이명박``…). 비례는 정당만(``한나라당``).
- 시도 = 파일명(서울→서울특별시). 구시군 = col0(위원회명) carry-forward.
- 여러 블록(중간에 위원회명/후보 헤더 재출력)이 한 시트에 쌓여 있으나 후보 집합은
  파일 전체가 동일하다 → 재출력 헤더는 같은 후보로 덮어써도 무해하다.

## B형 (구시군장·시도의원·구시군의원): 파일 = 한 구시군, 모지바케 인코딩
- **모든 문자열 셀을 복원해야 한다**: ``cell.encode('latin1').decode('cp949')``.
- col0=투표구명/읍면동명(위원회명 컬럼 없음), col1=선거인수, col2=투표수, col3+=후보 득표.
- 구시군 = 파일명(강남구→강남구). 시도 = GU_SIDO_3RD로 구시군에서 역추론.
- **시도의원·구시군의원은 한 파일에 여러 선거구 블록**이 쌓여 있다. 각 블록은
  ``선거구명/읍면동``이 col0에 오는 후보 헤더 행으로 시작하고(선거인수·투표수 칸은 비고
  후보 칸에 이름이 박힘), 블록마다 후보 집합과 ``계`` 컬럼 위치가 다르다. 같은 투표구명이
  여러 선거구에 반복되므로(부재자·잘못투입도) 읍면동에 선거구명을 접두해 키 충돌을 막고,
  선거구 ``합계``를 구시군 단위로 합산한다(4·5회 district 접두 관용구와 동일).
- 구시군장은 단일 블록(선거구 없음).

## 공통 행 처리
- ``합계``→구시군/선거구 합계(totals, rows엔 안 냄), ``부재자``→거소선상,
  ``잘못투입된투표지``→잘못투입, ``소계``→SKIP(투표구의 읍면동 소계, 중간합),
  투표구/읍면동 행→emit(level=당일투표). 정합: 합계 == 부재자 + 잘못투입 + Σ투표구.
- 후보 셀 ``정당 이름``은 **첫 토막=정당, 나머지(공백제거)=후보자**로 쪼갠다
  (``한나라당 이   달``처럼 이름에 내부 공백이 있는 경우가 있어 마지막 토막만 취하면 안 됨).
  구시군의원은 정당 없는 이름만(``윤정희``)이라 정당="".

## 깨진 파일명 (MD5 dedup)
B형 폴더마다 ``+++ۢ+.xls`` 같은 깨진 이름 파일이 하나씩 있다(전부 ``오산시.xls``의
내용 복사본). 한글 이름을 먼저 처리하고 내용 해시가 이미 본 것이면 SKIP(건수 보고).
깨진 이름이 유니크한 내용이면 시트 내용에서 구시군을 역추론해 살린다(실데이터엔 0건).
"""

import hashlib
import os
import re
import unicodedata
from collections import Counter

import xlrd
import xlrd.book

# 일부 .xls의 WRITEACCESS(작성자 메타) 레코드가 깨져 xlrd가 globals 파싱 중
# UnicodeDecodeError로 죽는다. 셀 데이터와 무관한 메타라 무시한다(4·5·6회와 동일).
xlrd.book.Book.handle_writeaccess = lambda self, data: None

# 최상위 race 폴더명 키워드 → (표준 선거종류, 폼). A=시도 단위 정상인코딩,
# B=구시군 단위 모지바케·다중블록.
FOLDER_ETYPE = [
    ("시도지사", ("시도지사", "A")),
    ("비례대표", ("광역비례", "A")),
    ("구시군장", ("구시군장", "B")),
    ("시도의원", ("시도의원", "B")),
    ("구시군의원", ("구시군의원", "B")),
]

# 후보 셀이 정당명만 있는(이름 없는) 비례대표
PARTY_ONLY_TYPES = {"광역비례"}
# 후보 셀에 정당이 없는(이름만) 선거 — 기초의원
NO_PARTY_TYPES = {"구시군의원"}

# A형 파일명(시도 약칭) → 정식 시도명
ABBR_TO_SIDO = {
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시",
    "인천": "인천광역시", "광주": "광주광역시", "대전": "대전광역시",
    "울산": "울산광역시", "경기": "경기도", "강원": "강원도",
    "충북": "충청북도", "충남": "충청남도", "전북": "전라북도",
    "전남": "전라남도", "경북": "경상북도", "경남": "경상남도",
    "제주": "제주특별자치도",
}

# B형 구시군명 → 시도(약칭). 동명 구(중구·서구 등)는 파일명에 (부산)·(대구) 접미가
# 붙어 구분된다. process_local_elections.py:112 GU_SIDO_3RD를 그대로 가져옴.
GU_SIDO_ABBR = {
    # 서울
    "종로구": "서울", "중구": "서울", "용산구": "서울", "성동구": "서울", "광진구": "서울",
    "동대문구": "서울", "중랑구": "서울", "성북구": "서울", "강북구": "서울", "도봉구": "서울",
    "노원구": "서울", "은평구": "서울", "서대문구": "서울", "마포구": "서울", "양천구": "서울",
    "강서구": "서울", "구로구": "서울", "금천구": "서울", "영등포구": "서울", "동작구": "서울",
    "관악구": "서울", "서초구": "서울", "강남구": "서울", "송파구": "서울", "강동구": "서울",
    # 부산
    "중구(부산)": "부산", "서구(부산)": "부산", "동구(부산)": "부산", "영도구": "부산",
    "부산진구": "부산", "동래구": "부산", "남구(부산)": "부산", "북구(부산)": "부산",
    "해운대구": "부산", "사하구": "부산", "금정구": "부산", "강서구(부산)": "부산",
    "연제구": "부산", "수영구": "부산", "사상구": "부산", "기장군": "부산",
    # 대구
    "중구(대구)": "대구", "동구(대구)": "대구", "서구(대구)": "대구", "남구(대구)": "대구",
    "북구(대구)": "대구", "수성구": "대구", "달서구": "대구", "달성군": "대구",
    # 인천
    "중구(인천)": "인천", "동구(인천)": "인천", "남구(인천)": "인천", "연수구": "인천",
    "남동구": "인천", "부평구": "인천", "계양구": "인천", "서구(인천)": "인천",
    "강화군": "인천", "옹진군": "인천",
    # 광주
    "동구(광주)": "광주", "서구(광주)": "광주", "남구(광주)": "광주",
    "북구(광주)": "광주", "광산구": "광주",
    # 대전
    "동구(대전)": "대전", "중구(대전)": "대전", "서구(대전)": "대전",
    "유성구": "대전", "대덕구": "대전",
    # 울산
    "중구(울산)": "울산", "남구(울산)": "울산", "동구(울산)": "울산",
    "북구(울산)": "울산", "울주군": "울산",
    # 경기
    "수원시": "경기", "성남시": "경기", "의정부시": "경기", "안양시": "경기",
    "부천시": "경기", "광명시": "경기", "평택시": "경기", "동두천시": "경기",
    "안산시": "경기", "고양시": "경기", "과천시": "경기", "구리시": "경기",
    "남양주시": "경기", "오산시": "경기", "시흥시": "경기", "군포시": "경기",
    "의왕시": "경기", "하남시": "경기", "용인시": "경기", "파주시": "경기",
    "이천시": "경기", "안성시": "경기", "김포시": "경기", "화성시": "경기",
    "광주시": "경기", "양주시": "경기", "여주군": "경기", "연천군": "경기",
    "포천군": "경기", "가평군": "경기", "양평군": "경기",
    # 강원
    "춘천시": "강원", "원주시": "강원", "강릉시": "강원", "동해시": "강원",
    "태백시": "강원", "속초시": "강원", "삼척시": "강원", "홍천군": "강원",
    "횡성군": "강원", "영월군": "강원", "평창군": "강원", "정선군": "강원",
    "철원군": "강원", "화천군": "강원", "양구군": "강원", "인제군": "강원",
    "고성군(강원)": "강원", "양양군": "강원",
    # 충북
    "청주시": "충북", "충주시": "충북", "제천시": "충북", "청원군": "충북",
    "보은군": "충북", "옥천군": "충북", "영동군": "충북", "진천군": "충북",
    "괴산군": "충북", "음성군": "충북", "단양군": "충북", "증평군": "충북",
    # 충남
    "천안시": "충남", "공주시": "충남", "보령시": "충남", "아산시": "충남",
    "서산시": "충남", "논산시": "충남", "계룡시": "충남", "금산군": "충남",
    "연기군": "충남", "부여군": "충남", "서천군": "충남", "청양군": "충남",
    "홍성군": "충남", "예산군": "충남", "태안군": "충남", "당진군": "충남",
    # 전북
    "전주시": "전북", "군산시": "전북", "익산시": "전북", "정읍시": "전북",
    "남원시": "전북", "김제시": "전북", "완주군": "전북", "진안군": "전북",
    "무주군": "전북", "장수군": "전북", "임실군": "전북", "순창군": "전북",
    "고창군": "전북", "부안군": "전북",
    # 전남
    "목포시": "전남", "여수시": "전남", "순천시": "전남", "나주시": "전남",
    "광양시": "전남", "담양군": "전남", "곡성군": "전남", "구례군": "전남",
    "고흥군": "전남", "보성군": "전남", "화순군": "전남", "장흥군": "전남",
    "강진군": "전남", "해남군": "전남", "영암군": "전남", "무안군": "전남",
    "함평군": "전남", "영광군": "전남", "장성군": "전남", "완도군": "전남",
    "진도군": "전남", "신안군": "전남",
    # 경북
    "포항시": "경북", "경주시": "경북", "김천시": "경북", "안동시": "경북",
    "구미시": "경북", "영주시": "경북", "영천시": "경북", "상주시": "경북",
    "문경시": "경북", "경산시": "경북", "군위군": "경북", "의성군": "경북",
    "청송군": "경북", "영양군": "경북", "영덕군": "경북", "청도군": "경북",
    "고령군": "경북", "성주군": "경북", "칠곡군": "경북", "예천군": "경북",
    "봉화군": "경북", "울진군": "경북", "울릉군": "경북",
    # 경남
    "창원시": "경남", "마산시": "경남", "진주시": "경남", "진해시": "경남",
    "통영시": "경남", "사천시": "경남", "김해시": "경남", "밀양시": "경남",
    "거제시": "경남", "양산시": "경남", "의령군": "경남", "함안군": "경남",
    "창녕군": "경남", "고성군(경남)": "경남", "남해군": "경남", "하동군": "경남",
    "산청군": "경남", "함양군": "경남", "거창군": "경남", "합천군": "경남",
    # 제주
    "제주시": "제주", "서귀포시": "제주", "북제주군": "제주", "남제주군": "제주",
    # 자치시 산하 일반구(2002 당시 구시군 단위로 파일이 쪼개져 있음) + 동명 구 접미 변형
    "수원시장안구": "경기", "수원시권선구": "경기", "수원시팔달구": "경기",
    "성남시수정구": "경기", "성남시중원구": "경기", "성남시분당구": "경기",
    "안양시만안구": "경기", "안양시동안구": "경기",
    "부천시원미구": "경기", "부천시소사구": "경기", "부천시오정구": "경기",
    "고양시덕양구": "경기", "고양시일산구": "경기", "양주군": "경기",
    "청주시상당구": "충북", "청주시흥덕구": "충북",
    "전주시완산구": "전북", "전주시덕진구": "전북",
    "포항시남구": "경북", "포항시북구": "경북",
    "중구(서울)": "서울", "동부(부산)": "부산",
}

EUPMD_LABELS = {"투표구명", "읍면동명"}
COMMITTEE_LABEL = "위원회명"
TOTAL_LABEL = "합계"
SUBTOTAL_LABEL = "소계"
ABSENTEE_LABEL = "부재자"
KNOWN_OTHER = {"잘못투입된투표지", "잘못투입·구분된투표지"}
VALID_TOTAL_LABEL = "계"
# 후보 헤더에 끼는 라벨 잔재(후보 아님)
HEADER_NOISE = {"계", "유효투표수", "후보자별 득표수", "투 표 율 (%)",
                "유효 투표 율 (%)", "무효 투표 수", "기 권 수", "무효투표수", "기권수"}


def _norm(value):
    if value is None:
        return ""
    return unicodedata.normalize("NFC", str(value)).strip()


def _squash(text):
    """내부 공백 제거(``합   계``·``이   달`` → ``합계``·``이달``)."""
    return re.sub(r"\s+", "", text)


def _to_int(value):
    """'452,744'·452744·'73.0'·73.0 → 정수. 빈값·'·'·'-' → None.
    음수(잘못투입 -1)도 정수로 그대로 보존한다."""
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


def _is_number(text):
    """문자열이 숫자(콤마·소수점·음수 포함)면 True. 후보 헤더와 데이터 행 구분용."""
    cleaned = text.replace(",", "").replace(".", "").lstrip("-")
    return cleaned.isdigit()


def _repair(text):
    """모지바케(cp949→latin1 오독) 복원. 정상 한글이면 그대로 반환."""
    try:
        fixed = text.encode("latin1", errors="strict").decode("cp949", errors="strict")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    return fixed


def _needs_repair(sheet):
    """헤더 상단에 모지바케 마커가 있으면 True(B형). A형은 한글 정상."""
    for row in range(min(5, sheet.nrows)):
        for col in range(min(6, sheet.ncols)):
            value = sheet.cell_value(row, col)
            if isinstance(value, str) and any(marker in value for marker in "ÅÇ¥±¸¶º"):
                return True
    return False


def _split_party_name(cell, party_only, no_party):
    """후보 셀 → (정당, 후보자).

    - 비례(party_only): 정당만 → (정당, None).
    - 기초의원(no_party): 이름만 → ("", 이름).
    - 그 외 ``정당 이름``: 첫 토막=정당, 나머지(공백제거)=후보자. ``한나라당 이   달``처럼
      이름에 내부 공백이 있어 마지막 토막만 취하면 안 된다.
    """
    cell = _norm(cell)
    if party_only:
        return _squash(cell), None
    if no_party:
        return "", _squash(cell)
    parts = cell.split(None, 1)
    if len(parts) == 1:
        return "", _squash(parts[0])
    return parts[0], _squash(parts[1])


def _candidate_map(row, cand_start, party_only, no_party):
    """후보 헤더 행 → ({컬럼: (정당, 후보자)}, 끝컬럼). ``계`` 전까지 비라벨 셀이 후보.

    같은 (정당,후보자)가 한 블록에 둘 이상이면(동명이인) 둘째부터 이름에 ``(N)``을 붙여
    KEY_COLS 충돌을 막는다(4회와 동일)."""
    gye_col = next((col for col in range(cand_start, len(row))
                    if _squash(row[col]) == VALID_TOTAL_LABEL), len(row))
    mapping = {}
    seen = Counter()
    for col in range(cand_start, gye_col):
        cell = row[col]
        if not cell or _squash(cell) in {_squash(noise) for noise in HEADER_NOISE}:
            continue
        party, name = _split_party_name(cell, party_only, no_party)
        key = (party, name)
        seen[key] += 1
        if name is not None and seen[key] > 1:
            name = f"{name}({seen[key]})"
        mapping[col] = (party, name)
    return mapping, gye_col


def _read_sheet(filepath):
    """첫 시트를 (셀 2차원, repair?) 으로. B형이면 모든 문자열 셀을 복원한다."""
    sheet = xlrd.open_workbook(filepath).sheet_by_index(0)
    repair = _needs_repair(sheet)

    def conv(value):
        if isinstance(value, str) and repair:
            value = _repair(value)
        return _norm(value)

    grid = [[conv(sheet.cell_value(row, col)) for col in range(sheet.ncols)]
            for row in range(sheet.nrows)]
    return grid, repair


def _is_candidate_header(row, eupmd_col, electorate_col, votes_col, cand_start):
    """후보 헤더 행 판정. col0(읍면동/선거구) 칸은 선거구명이거나 비어 있고(구시군장의
    최상단 헤더는 비어 있다), 선거인수·투표수 칸은 비고, 후보 컬럼에 비숫자 텍스트가
    하나 이상 있다."""
    if eupmd_col >= len(row):
        return False
    label = _squash(row[eupmd_col])
    if label in EUPMD_LABELS or label == COMMITTEE_LABEL:
        return False
    if label in (TOTAL_LABEL, SUBTOTAL_LABEL, ABSENTEE_LABEL) or label in {
            _squash(other) for other in KNOWN_OTHER}:
        return False
    # 선거인수·투표수 칸이 숫자면 데이터 행이지 헤더가 아니다.
    for fixed_col in (electorate_col, votes_col):
        if fixed_col is not None and fixed_col < len(row) and _is_number(row[fixed_col]):
            return False
    # 후보 컬럼의 비숫자 텍스트. 페이지 머리표 ``[춘천시]`` 같은 대괄호 태그는 후보가
    # 아니므로 제외한다(이 태그를 후보 헤더로 오인하면 블록이 깨진다).
    text_cells = [row[col] for col in range(cand_start, len(row))
                  if col < len(row) and row[col] and not _is_number(row[col])
                  and not row[col].startswith("[")
                  and _squash(row[col]) not in {_squash(noise) for noise in HEADER_NOISE}]
    return len(text_cells) >= 1


def _parse_file(grid, election_type, form, sido, county):
    """한 시트(grid)를 파싱해 (rows, totals, unrecognized, skip_reason).

    A형: county는 None으로 들어와 위원회명(col0) carry-forward로 채운다. 후보 집합은
    파일 전체 동일(재출력 헤더 덮어써도 무해).
    B형: county는 파일명에서 고정. 시도의원·구시군의원은 다중 블록 — 후보 헤더 행마다
    current_candidates·current_district를 갱신하고, 읍면동에 선거구명을 접두한다.
    """
    # 라벨 행: 투표구명/읍면동명 셀이 있는 첫 행.
    label_idx = next((index for index, row in enumerate(grid)
                      if any(_squash(cell) in EUPMD_LABELS for cell in row)), None)
    if label_idx is None:
        return [], [], [], "투표구명/읍면동명 라벨 행 없음"
    label_row = grid[label_idx]
    eupmd_col = next(index for index, cell in enumerate(label_row)
                     if _squash(cell) in EUPMD_LABELS)
    has_committee = any(_squash(cell) == COMMITTEE_LABEL for cell in label_row)

    if form == "A":
        # col0=위원회명, col1=투표구명, col2=선거인수, col3=투표수, col4+=후보
        committee_col = 0
        electorate_col, votes_col, cand_start = 2, 3, 4
    else:
        # col0=투표구명/읍면동명, col1=선거인수, col2=투표수, col3+=후보
        committee_col = None
        electorate_col, votes_col, cand_start = eupmd_col + 1, eupmd_col + 2, eupmd_col + 3

    party_only = election_type in PARTY_ONLY_TYPES
    no_party = election_type in NO_PARTY_TYPES

    rows, totals, unrecognized = [], [], []
    current_county = county
    current_district = None
    current_candidates = {}

    def emit_leaf(precinct_raw, level, source_row):
        electorate = None
        if level == "당일투표" and electorate_col < len(source_row):
            electorate = _to_int(source_row[electorate_col])
        precinct = _norm(precinct_raw)
        if current_district:
            precinct = f"{current_district} {precinct}"
        turnout = _to_int(source_row[votes_col]) if votes_col < len(source_row) else None
        for col, (party, name) in current_candidates.items():
            rows.append({
                "선거_회차": 3, "선거종류": election_type, "시도": sido,
                "구시군": current_county, "읍면동": precinct,
                "선거구명": current_district,
                "선거인수": electorate, "투표수": turnout, "후보자": name,
                "정당": party,
                "득표수": _to_int(source_row[col]) if col < len(source_row) else None,
                "무효투표수": None, "기권수": None, "level": level,
            })

    if form == "A":
        # A형 후보 헤더는 라벨 행 다음다음(col0·col1 비고 col4+ 후보). 파일 전체 동일이라
        # 한 번만 읽어 고정한다(중간 재출력 헤더는 col1이 비어 자연히 skip).
        header_idx = label_idx + 2
        if header_idx < len(grid):
            mapping, _gye = _candidate_map(grid[header_idx], cand_start,
                                           party_only, no_party)
            current_candidates = mapping

    for row in grid[label_idx + 1:]:
        if eupmd_col >= len(row):
            continue
        # A형: 위원회명(col0)으로 구시군 carry-forward.
        if has_committee and committee_col is not None and committee_col < len(row):
            committee = _norm(row[committee_col])
            if committee and committee != COMMITTEE_LABEL:
                current_county = committee

        label = _squash(row[eupmd_col])
        if label in EUPMD_LABELS or label == COMMITTEE_LABEL:
            continue  # 재출력 라벨 행

        # B형: 후보 헤더 행마다 후보 집합·선거구 접두를 갱신(구시군장은 col0 빈
        # 최상단 헤더 1개, 시도의원·구시군의원은 선거구마다). A형은 위에서 고정.
        if form == "B" and _is_candidate_header(
                row, eupmd_col, electorate_col, votes_col, cand_start):
            mapping, _gye = _candidate_map(row, cand_start, party_only, no_party)
            if mapping:
                current_candidates = mapping
                # col0이 선거구명이면 접두로 쓰고, 비었으면(구시군장 단일블록) 없음.
                current_district = label if label else None
            continue

        if not label:
            continue  # 빈칸 행

        if not current_candidates:
            continue  # 아직 후보 헤더 전 — 데이터 없음

        if label == TOTAL_LABEL:
            totals.append({
                "선거종류": election_type, "시도": sido, "구시군": current_county,
                "level": None,
                "투표수": _to_int(row[votes_col]) if votes_col < len(row) else None,
            })
        elif label == SUBTOTAL_LABEL:
            continue  # 읍면동 소계(중간합) — emit 안 함
        elif label == ABSENTEE_LABEL:
            emit_leaf(row[eupmd_col], "거소선상", row)
        elif label in {_squash(other) for other in KNOWN_OTHER}:
            emit_leaf(row[eupmd_col], "잘못투입", row)
        elif votes_col < len(row) and _is_number(row[votes_col]):
            emit_leaf(row[eupmd_col], "당일투표", row)
        else:
            unrecognized.append({
                "선거종류": election_type, "시도": sido,
                "구시군": current_county, "읍면동": _norm(row[eupmd_col])})

    return rows, totals, unrecognized, None


def _sido_full(abbr):
    """약칭 시도 → 정식 시도명."""
    return ABBR_TO_SIDO.get(abbr)


def _county_to_sido(county):
    """B형 구시군명 → 정식 시도명. GU_SIDO_ABBR 매핑."""
    abbr = GU_SIDO_ABBR.get(county)
    return _sido_full(abbr) if abbr else None


def _guess_county_from_grid(grid):
    """깨진 파일명 B형: 시트 내용(선거구명·투표구명 셀)에서 구시군명 역추론."""
    for row in grid[:40]:
        for cell in row[:2]:
            text = _norm(cell)
            match = re.match(r"^([가-힣]+(?:시|군|구)(?:\([가-힣]+\))?)", text)
            if match and match.group(1) in GU_SIDO_ABBR:
                return match.group(1)
            base = re.match(r"^([가-힣]+(?:시|군|구))", text)
            if base and base.group(1) in GU_SIDO_ABBR:
                return base.group(1)
    return None


def parse_3rd(base_dir):
    """3회 지방선거 디렉터리(5개 race 폴더)를 모두 파싱한다.

    반환: (rows, totals)
    - rows: 15개 스키마 컬럼의 tidy dict 리스트(선거일은 오케스트레이터가 채움).
    - totals: 구시군 합계 {선거종류,시도,구시군,level,투표수} 리스트(선거구로 쪼개진
      시도의원·구시군의원은 선거구 합계를 구시군 단위로 합산).
    """
    base_dir = unicodedata.normalize("NFC", base_dir)
    all_rows = []
    totals_by_key = {}
    all_unrecognized = []
    all_skipped = []
    dedup_skipped = []
    salvaged = []

    def add_total(total):
        key = (total["선거종류"], total["시도"], total["구시군"])
        bucket = totals_by_key.setdefault(key, {
            "선거종류": total["선거종류"], "시도": total["시도"],
            "구시군": total["구시군"], "level": None, "투표수": 0})
        bucket["투표수"] += total["투표수"] or 0

    for folder in sorted(os.listdir(base_dir)):
        folder_path = os.path.join(base_dir, folder)
        if not os.path.isdir(folder_path):
            continue
        meta = next((value for keyword, value in FOLDER_ETYPE if keyword in folder), None)
        if meta is None:
            continue
        election_type, form = meta

        filenames = sorted(
            (name for name in os.listdir(folder_path) if name.lower().endswith(".xls")),
            # 한글 이름을 깨진 이름보다 먼저 처리해 정상 파일을 우선 등록(dedup 기준).
            key=lambda name: (0 if re.match(r"^[가-힣]", name) else 1, name))
        seen_hashes = set()

        for filename in filenames:
            filepath = os.path.join(folder_path, filename)
            with open(filepath, "rb") as handle:
                file_hash = hashlib.md5(handle.read()).hexdigest()
            stem = unicodedata.normalize("NFC", os.path.splitext(filename)[0])
            korean_name = bool(re.match(r"^[가-힣]", stem))

            if file_hash in seen_hashes:
                dedup_skipped.append({"선거종류": election_type, "파일": filename})
                continue
            seen_hashes.add(file_hash)

            try:
                grid, _repaired = _read_sheet(filepath)
            except Exception as error:
                all_skipped.append({"선거종류": election_type, "시도": None,
                                    "구시군": None, "source": filename,
                                    "reason": f"읽기 실패: {error}"})
                continue

            if form == "A":
                sido = _sido_full(stem)
                county = None
                if sido is None:
                    all_skipped.append({"선거종류": election_type, "시도": None,
                                        "구시군": None, "source": filename,
                                        "reason": "시도 식별 실패(A형 파일명)"})
                    continue
            else:
                county = stem
                if not korean_name or county not in GU_SIDO_ABBR:
                    guessed = _guess_county_from_grid(grid)
                    if guessed:
                        county = guessed
                        if not korean_name:
                            salvaged.append({"선거종류": election_type,
                                             "파일": filename, "추론구시군": guessed})
                sido = _county_to_sido(county)
                if sido is None:
                    all_skipped.append({"선거종류": election_type, "시도": None,
                                        "구시군": county, "source": filename,
                                        "reason": "구시군→시도 매핑 실패"})
                    continue

            try:
                file_rows, file_totals, file_unrec, skip = _parse_file(
                    grid, election_type, form, sido, county)
            except Exception as error:
                all_skipped.append({"선거종류": election_type, "시도": sido,
                                    "구시군": county, "source": filename,
                                    "reason": f"파싱 실패: {error}"})
                continue
            if skip is not None:
                all_skipped.append({"선거종류": election_type, "시도": sido,
                                    "구시군": county, "source": filename, "reason": skip})
                continue
            all_rows.extend(file_rows)
            for total in file_totals:
                add_total(total)
            all_unrecognized.extend(file_unrec)

    if all_unrecognized:
        _warn_unrecognized(all_unrecognized)
    if all_skipped:
        _warn_skipped(all_skipped)
    if dedup_skipped:
        counts = Counter(block["선거종류"] for block in dedup_skipped)
        print(f"[parse_3rd] 내용 중복(깨진 파일명) {len(dedup_skipped)}건 dedup-skip "
              f"— 정상: {dict(counts)}")
    if salvaged:
        print(f"[parse_3rd] 깨진 파일명 {len(salvaged)}건 내용 역추론으로 살림: "
              f"{[(block['선거종류'], block['추론구시군']) for block in salvaged]}")

    return all_rows, list(totals_by_key.values())


def _warn_unrecognized(unrecognized):
    """미인식 행을 (선거종류/시도/구시군/읍면동)별로 집계해 경고. 정상이면 0건."""
    counts = Counter(
        (row["선거종류"], row["시도"], row["구시군"], row["읍면동"])
        for row in unrecognized)
    print(f"[parse_3rd] 경고: 미인식 행 {len(unrecognized)}건 "
          f"({len(counts)}종)을 emit 하지 않고 건너뜀:")
    for (etype, sido, county, eupmd), count in counts.most_common(30):
        print(f"  {count:6d}회  선거종류={etype} 시도={sido} 구시군={county} "
              f"읍면동={eupmd!r}")


def _warn_skipped(skipped):
    """파일을 통째로 건너뛴 경우를 사유별로 집계해 경고. 정상이면 0건."""
    counts = Counter(
        (block["reason"], block["선거종류"], block["시도"], block["구시군"])
        for block in skipped)
    print(f"[parse_3rd] 경고: 파일 통째 건너뜀 {len(skipped)}건 "
          f"({len(counts)}종) — 데이터 누락 의심, 헤더/경로 매칭 점검 필요:")
    for (reason, etype, sido, county), count in counts.most_common(30):
        sample = next(block["source"] for block in skipped
                      if block["reason"] == reason and block["선거종류"] == etype
                      and block["시도"] == sido and block["구시군"] == county)
        print(f"  {count:4d}파일  사유={reason} 선거종류={etype} 시도={sido} "
              f"구시군={county} 예시={sample!r}")
