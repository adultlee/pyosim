"""16대(2000) 국회의원선거 파서."""

import os
import re
import xlrd

_EMD_FROM_STATION = re.compile(r"^([가-힣0-9.·]+(?:[가-힣0-9.· ]*[가-힣0-9.·])?)(?:제\s*|\s+)\d+투$")


def _extract_emd(투표구명):
    """투표구명에서 읍면동명 추출. 예: '주문진읍제 1투' → '주문진읍', '후평1동제 1투' → '후평1동'."""
    m = _EMD_FROM_STATION.match(투표구명)
    if not m:
        return None
    # '주문진읍제 1투' → group(1)='주문진읍제' → '제'는 서수 접미사이므로 제거
    # '광혜원면 1투' → group(1)='광혜원면' → 그대로
    raw = m.group(1).rstrip("제").strip()
    return raw

from etl.assembly.schema import normalize_level
from etl.assembly._helpers import to_int, is_skip_row

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data_raw")
ROUND = "제16대"
ELECTION_DATE = "2000-04-13"

# 선거구명 → 시도 매핑 (16대 전용)
_SIDO_16 = {
    "서울": ["종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구",
             "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구",
             "구로구", "금천구", "영등포구", "동작구", "관악구", "서초구", "강남구", "송파구", "강동구"],
    "부산": ["중구(부산)", "서구(부산)", "동구", "영도구", "부산진구", "동래구", "남구", "북구강서구",
             "해운대구기장군", "사하구", "금정구", "연제구", "수영구", "사상구"],
    "대구": ["중구(대구)", "동구(대구)", "서구(대구)", "남구(대구)", "북구(대구)", "수성구", "달서구", "달성군"],
    "인천": ["중구(인천)", "동구(인천)", "남구(인천)", "연수구", "남동구", "부평구", "계양구", "서구(인천)", "강화군옹진군"],
    "광주": ["동구(광주)", "서구(광주)", "남구(광주)", "북구(광주)", "광산구"],
    "대전": ["동구(대전)", "중구(대전)", "서구(대전)", "유성구", "대덕구"],
    "울산": ["중구(울산)", "남구(울산)", "동구(울산)", "북구(울산)", "울주군"],
    "경기": ["수원시", "성남시", "의정부시", "안양시", "부천시", "광명시", "평택시", "동두천시",
             "안산시", "고양시", "과천시", "구리시", "남양주시", "오산시", "시흥시", "군포시",
             "의왕시", "하남시", "용인시", "파주시", "이천시", "안성시", "김포시", "화성시",
             "광주시", "양주시", "여주군", "연천군", "포천군", "가평군", "양평군"],
    "강원": ["춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시", "홍천군",
             "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군", "양구군", "인제군", "고성군양양군"],
    "충북": ["청주시", "충주시", "제천시", "청원군", "보은군", "옥천군", "영동군", "진천군",
             "괴산군증평군", "음성군", "단양군"],
    "충남": ["천안시", "공주시", "보령시", "아산시", "서산시", "논산시", "연기군", "금산군",
             "부여군", "서천군", "청양군", "홍성군", "예산군", "태안군", "당진군"],
    "전북": ["전주시", "군산시", "익산시", "정읍시", "남원시", "김제시", "완주군", "진안군",
             "무주군", "장수군", "임실군", "순창군", "고창군", "부안군"],
    "전남": ["목포시", "여수시", "순천시", "나주시", "광양시구례군", "담양군곡성군장성군",
             "고흥군보성군", "화순군", "장흥군강진군", "해남군완도군진도군", "무안군신안군", "영암군",
             "함평군영광군"],
    "경북": ["포항시", "경주시", "김천시", "안동시", "구미시", "영주시", "영천시", "상주시",
             "문경시", "경산시", "군위군의성군청송군", "영양군울진군", "영덕군", "청도군고령군",
             "성주군칠곡군", "예천군", "봉화군", "울릉군독도"],
    "경남": ["창원시", "마산시", "진주시", "진해시", "통영시고성군", "사천시", "김해시", "밀양시",
             "거제시", "의령군함안군", "창녕군", "고성군", "하동군", "산청군합천군", "남해군하동군",
             "함양군거창군", "양산시"],
    "제주": ["제주시", "북제주군", "서귀포시,남제주군"],
}

_SIDO_16_EXTRA = {
    "중동구": "부산",
    "남원·순창": "전북", "진안·무주·장수": "전북", "고창·부안": "전북", "완주·임실": "전북",
    "고흥군": "전남", "장흥군영암군": "전남", "해남군진도군": "전남",
    "보성군화순군": "전남", "강진군완도군": "전남",
    "고령군성주군": "경북", "군위군의성군": "경북", "청송군영양군영덕군": "경북", "칠곡군": "경북",
}


def _infer_sido_16(선거구명_raw):
    """16대용: 선거구명 raw string에서 시도 추정."""
    name = str(선거구명_raw).strip()
    if name in _SIDO_16_EXTRA:
        return _SIDO_16_EXTRA[name]
    for sido, prefixes in _SIDO_16.items():
        for prefix in prefixes:
            if name.startswith(prefix.split("(")[0]):
                return sido
    for keyword, sido in [("서울", "서울"), ("부산", "부산"), ("대구", "대구"),
                          ("인천", "인천"), ("광주", "광주"), ("대전", "대전"), ("울산", "울산")]:
        if keyword in name:
            return sido
    return ""


def parse_16th(raw_dir=RAW_DIR):
    """16대 지역구 파싱.

    Returns:
        (rows, totals) — totals는 빈 리스트 (16대에는 합계행 추출 불필요).
    """
    path = os.path.join(raw_dir,
                        "국회의원선거 개표결과(제16대~19대)",
                        "제16대 국회의원선거",
                        "제16대국회의원선거투표구별득표상황.xls")
    wb = xlrd.open_workbook(path, encoding_override="cp949")
    ws = wb.sheet_by_index(0)
    rows = []

    # '#선거구명' 행으로 구간 구분
    section_starts = []
    for row_idx in range(ws.nrows):
        val = str(ws.cell_value(row_idx, 0))
        if val.startswith("#"):
            section_starts.append((row_idx, val[1:].strip()))

    for sec_idx, (sec_row, 선거구명_raw) in enumerate(section_starts):
        next_row = section_starts[sec_idx + 1][0] if sec_idx + 1 < len(section_starts) else ws.nrows
        sido = _infer_sido_16(선거구명_raw)
        선거구명 = 선거구명_raw

        party_row1 = sec_row + 2
        party_row2 = sec_row + 3
        candidate_row = sec_row + 4

        if candidate_row >= ws.nrows:
            continue

        ncols = ws.ncols
        candidate_cols = []
        for col_idx in range(3, ncols - 3):
            p1 = str(ws.cell_value(party_row1, col_idx)).strip()
            p2 = str(ws.cell_value(party_row2, col_idx)).strip()
            cand = str(ws.cell_value(candidate_row, col_idx)).strip()
            party = re.sub(r"\s+", " ", (p1 + " " + p2).strip()).strip()
            if party or cand:
                candidate_cols.append((col_idx, party, cand))

        data_start = candidate_row + 1
        current_emd = ""
        current_구시군 = ""
        for r_idx in range(data_start, next_row):
            투표구명 = str(ws.cell_value(r_idx, 0)).strip()
            if is_skip_row(투표구명):
                continue
            if 투표구명.startswith("#") or 투표구명 in ("투표구명", ""):
                continue

            # 군/시 구분 헤더행 (예: '담양군', '장성군') — 구시군 컨텍스트 갱신 후 건너뜀
            if re.fullmatch(r".+[시군]", 투표구명) and not ws.cell_value(r_idx, 1):
                current_구시군 = 투표구명
                current_emd = ""
                continue

            # 투표구명에서 읍면동명 추출 (예: '주문진읍제 1투' → '주문진읍')
            extracted = _extract_emd(투표구명)
            if extracted:
                current_emd = extracted

            선거인수 = to_int(ws.cell_value(r_idx, 1))
            투표수 = to_int(ws.cell_value(r_idx, 2))
            무효 = to_int(ws.cell_value(r_idx, ncols - 2))
            기권 = to_int(ws.cell_value(r_idx, ncols - 1))

            for col_idx, party, cand in candidate_cols:
                득표 = to_int(ws.cell_value(r_idx, col_idx))
                if not cand and not party:
                    continue
                rows.append({
                    "선거_회차": ROUND,
                    "선거일": ELECTION_DATE,
                    "선거구분": "지역구",
                    "시도": sido,
                    "구시군": current_구시군,
                    "읍면동": current_emd,
                    "투표구": 투표구명,
                    "선거구명": 선거구명,
                    "선거인수": 선거인수,
                    "투표수": 투표수,
                    "후보자": cand,
                    "정당": party,
                    "득표수": 득표,
                    "무효투표수": 무효,
                    "기권수": 기권,
                    "level": normalize_level(투표구명),
                })

    return rows, []
