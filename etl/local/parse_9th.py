"""9회(2026) 전국동시지방선거 파서.

원본: data/raw/0020260603/*.html (선관위 HTML 개표 결과)
파일명 패턴: {ec코드}_city{시도코드}_sgg{구시군코드}.html

반환: (rows, totals)
- rows: tidy row dict 리스트
- totals: [{"선거종류": str, "시도": str, "구시군": str, "투표수": int}]
"""

import os
from bs4 import BeautifulSoup

from etl.local.schema import normalize_level

RAW_DIR = "data/raw/0020260603"
ROUND = 9
ELECTION_DATE = "2026-06-03"

CITY_CODE_TO_SIDO = {
    "1100": "서울특별시", "2600": "부산광역시", "2700": "대구광역시", "2800": "인천광역시",
    "2900": "광주광역시", "3000": "대전광역시", "3100": "울산광역시", "5100": "세종특별자치시",
    "4100": "경기도", "5200": "강원특별자치도", "4300": "충청북도", "4400": "충청남도",
    "5300": "전북특별자치도", "4600": "전라남도", "4700": "경상북도", "4800": "경상남도",
    "4900": "제주특별자치도",
}

EC_TO_TYPE = {
    "ec2": "교육감",
    "ec3": "시도지사",
    "ec4": "구시군장",
    "ec5": "시도의원",
    "ec6": "광역비례",
    "ec8": "구시군의원",
    "ec9": "기초비례",
}

_WRONG_BALLOT_KW = {"잘못 투입", "잘못투입"}
_TOTAL_EUP = "합계"


def _clean_num(value):
    if value is None:
        return None
    text = str(value).replace(",", "").strip()
    if text in ("", "-"):
        return None
    try:
        return int(text.split(".")[0])
    except ValueError:
        return None


def _extract_gugun(soup):
    """HTML select에서 구시군명 추출. townCode → townCodeFromSgg 순서로 시도."""
    for sel_name in ("townCode", "townCodeFromSgg"):
        sel = soup.find("select", attrs={"name": sel_name})
        if sel:
            opt = sel.find("option", selected=True)
            if opt:
                name = opt.get_text().strip()
                if name and name != "▽ 선 택":
                    return name
    return None


def _parse_candidates(table):
    rows = table.find("thead").find_all("tr")
    if len(rows) < 2:
        return []
    candidates = []
    for cell in rows[1].find_all("th"):
        for br in cell.find_all("br"):
            br.replace_with("\n")
        text = cell.get_text().strip().replace("\xa0", " ")
        if text in ("계", "합계"):
            continue
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) >= 2:
            candidates.append((lines[0], lines[1]))
        elif len(lines) == 1:
            parts = lines[0].split(" ", 1)
            candidates.append((parts[0], parts[1] if len(parts) > 1 else ""))
    return candidates


def _parse_file(filepath, election_type, sido, gugun_fallback):
    with open(filepath, encoding="utf-8") as fh:
        soup = BeautifulSoup(fh, "html.parser")

    gugun = _extract_gugun(soup) or gugun_fallback

    table = soup.find("table", id="table01")
    if not table:
        return [], None
    if "검색된 결과가 없습니다" in table.get_text():
        return [], None

    candidates = _parse_candidates(table)
    if not candidates:
        return [], None

    tbody = table.find("tbody")
    if not tbody:
        return [], None

    rows = []
    total_votes = None
    current_eup = None

    for tr in tbody.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 5:
            continue

        eup_text = cells[0].get_text().strip()
        gubun_text = cells[1].get_text().strip()

        # 구시군 합계행 → totals 수집 후 스킵
        if eup_text == _TOTAL_EUP and gubun_text == "":
            total_votes = _clean_num(cells[3].get_text())
            continue

        # 읍면동 소계(계) 행 스킵
        if gubun_text == "계":
            continue

        # 잘못투입 행: rows에 포함 (totals 합산에 포함되어야 함)
        if any(kw in eup_text for kw in _WRONG_BALLOT_KW):
            level = "잘못투입"
            emd = eup_text
        # 거소·관외사전 행: eup_text가 투표구분 이름
        elif eup_text in ("거소투표", "거소·선상투표", "거소우편투표", "관외사전투표"):
            current_eup = eup_text
            level = normalize_level(eup_text)
            emd = eup_text
        elif eup_text and eup_text not in (_TOTAL_EUP, "소계"):
            current_eup = eup_text
            level = normalize_level(gubun_text) if gubun_text else "당일투표"
            emd = current_eup
        else:
            level = normalize_level(gubun_text) if gubun_text else "당일투표"
            emd = current_eup or ""

        try:
            num_voters = _clean_num(cells[2].get_text())
            num_voted = _clean_num(cells[3].get_text())
            invalid_votes = _clean_num(cells[-2].get_text())
            abstentions = _clean_num(cells[-1].get_text())
        except IndexError:
            continue

        vote_cells = cells[4: 4 + len(candidates)]
        for idx, (party, candidate) in enumerate(candidates):
            votes = _clean_num(vote_cells[idx].get_text()) if idx < len(vote_cells) else None
            rows.append({
                "선거_회차": ROUND,
                "선거일": ELECTION_DATE,
                "선거종류": election_type,
                "시도": sido,
                "구시군": gugun,
                "읍면동": emd,
                "선거구명": gugun,
                "선거인수": num_voters,
                "투표수": num_voted,
                "후보자": candidate,
                "정당": party,
                "득표수": votes,
                "무효투표수": invalid_votes,
                "기권수": abstentions,
                "level": level,
            })

    total = {"선거종류": election_type, "시도": sido, "구시군": gugun, "투표수": total_votes} if total_votes is not None else None
    return rows, total


def parse_9th(raw_dir=RAW_DIR):
    all_rows = []
    all_totals = []

    for fname in sorted(os.listdir(raw_dir)):
        if not fname.endswith(".html"):
            continue
        parts = fname.replace(".html", "").split("_")
        if len(parts) < 3:
            continue
        ec_code = parts[0]
        city_code = parts[1].replace("city", "")
        sgg_code = parts[2].replace("sgg", "")

        election_type = EC_TO_TYPE.get(ec_code, ec_code)
        sido = CITY_CODE_TO_SIDO.get(city_code, city_code)
        gugun_fallback = sgg_code  # HTML에서 못 읽을 경우 코드 그대로

        fpath = os.path.join(raw_dir, fname)
        rows, total = _parse_file(fpath, election_type, sido, gugun_fallback)
        all_rows.extend(rows)
        if total:
            all_totals.append(total)

    return all_rows, all_totals
