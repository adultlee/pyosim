"""
제9회 전국동시지방선거 (2026-06-03) raw HTML → 지방선거.csv 추가
data/raw/0020260603/*.html 파싱
"""

import os
from bs4 import BeautifulSoup
import pandas as pd

RAW_DIR = "/Users/seong-in/Desktop/Git/pyosim/data/raw/0020260603"
OUT_PATH = "/Users/seong-in/Desktop/Git/pyosim/data_processed/지방선거.csv"

ELECTION_ROUND = 9
ELECTION_DATE = "2026-06-03"

# 선관위 HTML city 코드 → 시도 정식명 (기존 CSV 기준)
CITY_CODE_TO_SIDO = {
    "1100": "서울특별시", "2600": "부산광역시", "2700": "대구광역시", "2800": "인천광역시",
    "2900": "광주광역시", "3000": "대전광역시", "3100": "울산광역시", "5100": "세종특별자치시",
    "4100": "경기도", "5200": "강원특별자치도", "4300": "충청북도", "4400": "충청남도",
    "5300": "전북특별자치도", "4600": "전라남도", "4700": "경상북도", "4800": "경상남도",
    "4900": "제주특별자치도",
}

# 선관위 sgg 코드(4자리) → 구시군명
SGG_CODE_TO_NAME = {
    # 서울(1100)
    "1101": "종로구", "1102": "중구", "1103": "용산구", "1104": "성동구",
    "1105": "광진구", "1106": "동대문구", "1107": "중랑구", "1108": "성북구",
    "1109": "강북구", "1110": "도봉구", "1111": "노원구", "1112": "은평구",
    "1113": "서대문구", "1114": "마포구", "1115": "양천구", "1116": "강서구",
    "1117": "구로구", "1118": "금천구", "1119": "영등포구", "1120": "동작구",
    "1121": "관악구", "1122": "서초구", "1123": "강남구", "1124": "송파구",
    "1125": "강동구",
    # 부산(2600)
    "2601": "중구", "2602": "서구", "2603": "동구", "2604": "영도구",
    "2605": "부산진구", "2606": "동래구", "2607": "남구", "2608": "북구",
    "2609": "해운대구", "2610": "사하구", "2611": "금정구", "2612": "강서구",
    "2613": "연제구", "2614": "수영구", "2615": "사상구", "2616": "기장군",
    # 대구(2700)
    "2701": "중구", "2702": "동구", "2703": "서구", "2704": "남구",
    "2705": "북구", "2706": "수성구", "2707": "달서구", "2708": "달성군",
    "2709": "군위군",
    # 인천(2800)
    "2801": "중구", "2802": "동구", "2803": "미추홀구", "2804": "연수구",
    "2805": "남동구", "2806": "부평구", "2807": "계양구", "2808": "서구",
    "2809": "강화군", "2810": "옹진군",
    # 인천 9회 신규 자치구(영종·제물포·검단 신설, 서구 재배정)
    "2811": "영종구", "2812": "제물포구", "2813": "서구", "2814": "검단구",
    # 광주(2900)
    "2901": "동구", "2902": "서구", "2903": "남구", "2904": "북구",
    "2905": "광산구",
    # 대전(3000)
    "3001": "동구", "3002": "중구", "3003": "서구", "3004": "유성구",
    "3005": "대덕구",
    # 울산(3100)
    "3101": "중구", "3102": "남구", "3103": "동구", "3104": "북구",
    "3105": "울주군",
    # 세종(5100)
    "5101": "세종시",
    # 경기(4100)
    "4101": "수원시장안구", "4102": "수원시권선구", "4103": "수원시팔달구", "4104": "수원시영통구",
    "4105": "성남시수정구", "4106": "성남시중원구", "4107": "성남시분당구",
    "4108": "의정부시", "4109": "안양시만안구", "4110": "안양시동안구",
    "4111": "부천시", "4112": "광명시", "4113": "평택시", "4114": "동두천시",
    "4115": "안산시상록구", "4116": "안산시단원구",
    "4117": "고양시덕양구", "4118": "고양시일산동구", "4119": "고양시일산서구",
    "4120": "과천시", "4121": "구리시", "4122": "남양주시", "4123": "오산시",
    "4124": "시흥시", "4125": "군포시", "4126": "의왕시", "4127": "하남시",
    "4128": "용인시처인구", "4129": "용인시기흥구", "4130": "용인시수지구",
    "4131": "파주시", "4132": "이천시", "4133": "안성시", "4134": "김포시",
    "4135": "화성시", "4136": "광주시", "4137": "양주시", "4138": "포천시",
    "4139": "여주시", "4140": "연천군", "4141": "가평군", "4142": "양평군",
    # 경기 9회 신규 코드(부천·화성 행정구 신설 등)
    "4143": "양평군", "4144": "가평군",
    "4150": "부천시원미구", "4151": "부천시소사구", "4152": "부천시오정구",
    "4153": "화성시만세구", "4154": "화성시효행구", "4155": "화성시병점구", "4156": "화성시동탄구",
    # 강원(5200)
    "5201": "춘천시", "5202": "원주시", "5203": "강릉시", "5204": "동해시",
    "5205": "태백시", "5206": "속초시", "5207": "삼척시", "5208": "홍천군",
    "5209": "횡성군", "5210": "영월군", "5211": "평창군", "5212": "정선군",
    "5213": "철원군", "5214": "화천군", "5215": "양구군", "5216": "인제군",
    "5217": "고성군", "5218": "양양군",
    # 충북(4300)
    "4301": "청주시상당구", "4302": "청주시서원구", "4303": "청주시흥덕구", "4304": "청주시청원구",
    "4305": "충주시", "4306": "제천시", "4307": "보은군", "4308": "옥천군",
    "4309": "영동군", "4310": "증평군", "4311": "진천군", "4312": "괴산군",
    "4313": "음성군", "4314": "단양군",
    # 충남(4400)
    "4401": "천안시동남구", "4402": "천안시서북구", "4403": "공주시", "4404": "보령시",
    "4405": "아산시", "4406": "서산시", "4407": "논산시", "4408": "계룡시",
    "4409": "당진시", "4410": "금산군", "4411": "부여군", "4412": "서천군",
    "4413": "청양군", "4414": "홍성군", "4415": "예산군", "4416": "태안군",
    # 충남 9회 신규 코드(천안 행정구 재배정)
    "4417": "천안시서북구", "4418": "천안시동남구",
    # 전북(5300)
    "5301": "전주시완산구", "5302": "전주시덕진구", "5303": "군산시", "5304": "익산시",
    "5305": "정읍시", "5306": "남원시", "5307": "김제시", "5308": "완주군",
    "5309": "진안군", "5310": "무주군", "5311": "장수군", "5312": "임실군",
    "5313": "순창군", "5314": "고창군", "5315": "부안군",
    # 전북 9회 신규 코드(고창·부안 재배정)
    "5316": "고창군", "5317": "부안군",
    # 전남(4600)
    "4601": "목포시", "4602": "여수시", "4603": "순천시", "4604": "나주시",
    "4605": "광양시", "4606": "담양군", "4607": "곡성군", "4608": "구례군",
    "4609": "고흥군", "4610": "보성군", "4611": "화순군", "4612": "장흥군",
    "4613": "강진군", "4614": "해남군", "4615": "영암군", "4616": "무안군",
    "4617": "함평군", "4618": "영광군", "4619": "장성군", "4620": "완도군",
    "4621": "진도군", "4622": "신안군",
    # 전남 9회 신규 코드(함평·신안 재배정)
    "4623": "함평군", "4624": "신안군",
    # 경북(4700)
    "4701": "포항시남구", "4702": "포항시북구", "4703": "경주시", "4704": "김천시",
    "4705": "안동시", "4706": "구미시", "4707": "영주시", "4708": "영천시",
    "4709": "상주시", "4710": "문경시", "4711": "경산시", "4712": "군위군",
    "4713": "의성군", "4714": "청송군", "4715": "영양군", "4716": "영덕군",
    "4717": "청도군", "4718": "고령군", "4719": "성주군", "4720": "칠곡군",
    "4721": "예천군", "4722": "봉화군", "4723": "울진군", "4724": "울릉군",
    # 경남(4800)
    "4801": "창원시의창구", "4802": "창원시성산구", "4803": "창원시마산합포구",
    "4804": "창원시마산회원구", "4805": "창원시진해구",
    "4806": "진주시", "4807": "통영시", "4808": "사천시", "4809": "김해시",
    "4810": "밀양시", "4811": "거제시", "4812": "양산시", "4813": "의령군",
    "4814": "함안군", "4815": "창녕군", "4816": "고성군", "4817": "남해군",
    "4818": "하동군", "4819": "산청군", "4820": "함양군", "4821": "거창군",
    "4822": "합천군",
    # 경남 9회 신규 코드(창원 마산합포·마산회원·진해 재배정)
    "4823": "창원시마산합포구", "4824": "창원시마산회원구", "4825": "창원시진해구",
    # 제주(4900)
    "4901": "제주시", "4902": "서귀포시",
}

# ec 코드 → 선거종류
EC_TO_TYPE = {
    "ec2": "교육감",
    "ec3": "시도지사",
    "ec4": "구시군장",
    "ec5": "시도의원",
    "ec6": "광역비례",
    "ec8": "구시군의원",
    "ec9": "기초비례",
}

LEVEL_MAP = {
    "관내사전투표": "사전투표",
    "관외사전투표": "관외사전투표",
    "거소투표": "거소선상",
    "거소·선상투표": "거소선상",
    "거소우편투표": "거소선상",
    "선거일투표": "선거일투표",
}

SKIP_EUPS = {"합계", "소계", ""}
SKIP_EMD_KEYWORDS = {"잘못 투입", "잘못투입", "잘못투입된투표지"}

FINAL_COLS = [
    "선거_회차", "선거일", "선거종류", "시도", "구시군", "읍면동",
    "선거구명", "선거인수", "투표수", "후보자", "정당", "득표수",
    "무효투표수", "기권수", "level",
]


def clean_num(value):
    if value is None:
        return None
    text = str(value).replace(",", "").strip()
    if text in ("", "-"):
        return None
    try:
        return int(text.split(".")[0])
    except ValueError:
        return None


def get_level(name):
    return LEVEL_MAP.get(str(name).strip(), "당일투표")


def parse_candidates_from_thead(table):
    """thead 2행에서 후보자별 (정당, 이름) 리스트 반환. 마지막 '계' 컬럼 제외."""
    rows = table.find("thead").find_all("tr")
    if len(rows) < 2:
        return []
    candidate_cells = rows[1].find_all("th")
    candidates = []
    for cell in candidate_cells:
        # <br> 태그를 줄바꿈으로 변환 후 텍스트 추출
        for br in cell.find_all("br"):
            br.replace_with("\n")
        text = cell.get_text().strip().replace("\xa0", " ")
        if text in ("계", "합계"):
            continue
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) >= 2:
            party, name = lines[0], lines[1]
        elif len(lines) == 1:
            parts = lines[0].split(" ", 1)
            party = parts[0]
            name = parts[1] if len(parts) > 1 else ""
        else:
            continue
        candidates.append((party, name))
    return candidates


def parse_html_file(filepath, ec_code, city_code, sgg_code):
    sido = CITY_CODE_TO_SIDO.get(city_code, city_code)
    gu_name = SGG_CODE_TO_NAME.get(sgg_code, sgg_code)
    election_type = EC_TO_TYPE.get(ec_code, ec_code)

    with open(filepath, encoding="utf-8") as fh:
        soup = BeautifulSoup(fh, "html.parser")

    table = soup.find("table", id="table01")
    if not table:
        return []

    if "검색된 결과가 없습니다" in table.get_text():
        return []

    candidates = parse_candidates_from_thead(table)
    if not candidates:
        return []

    rows = []
    tbody = table.find("tbody")
    if not tbody:
        return []

    current_eup = None
    for tr in tbody.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 7:
            continue

        eup_text = cells[0].get_text().strip()
        gubun_text = cells[1].get_text().strip()

        # 합계/소계 행 스킵
        if eup_text in SKIP_EUPS and gubun_text == "":
            continue
        # 읍면동 합계(계) 행 스킵 - 개별 행으로 이미 포함
        if gubun_text == "계":
            continue
        # 잘못 투입된 투표지 행 스킵
        if any(kw in eup_text for kw in SKIP_EMD_KEYWORDS):
            continue

        if eup_text and eup_text not in SKIP_EUPS:
            current_eup = eup_text

        # 거소투표/관외사전투표는 읍면동이 없는 전체 행
        if eup_text in ("거소투표", "거소·선상투표", "거소우편투표", "관외사전투표"):
            current_eup = eup_text
            level = get_level(eup_text)
            emd = eup_text
        else:
            level = get_level(gubun_text) if gubun_text else "당일투표"
            emd = current_eup or ""

        try:
            num_voters = clean_num(cells[2].get_text())
            num_voted = clean_num(cells[3].get_text())
            invalid_votes = clean_num(cells[-2].get_text())
            abstentions = clean_num(cells[-1].get_text())
        except IndexError:
            continue

        vote_cells = cells[4: 4 + len(candidates)]

        for idx, (party, candidate) in enumerate(candidates):
            votes = clean_num(vote_cells[idx].get_text()) if idx < len(vote_cells) else None
            rows.append({
                "선거_회차": ELECTION_ROUND,
                "선거일": ELECTION_DATE,
                "선거종류": election_type,
                "시도": sido,
                "구시군": gu_name,
                "읍면동": emd,
                "선거구명": gu_name,
                "선거인수": num_voters,
                "투표수": num_voted,
                "후보자": candidate,
                "정당": party,
                "득표수": votes,
                "무효투표수": invalid_votes,
                "기권수": abstentions,
                "level": level,
            })

    return rows


def main():
    all_rows = []

    for fname in sorted(os.listdir(RAW_DIR)):
        if not fname.endswith(".html"):
            continue

        parts = fname.replace(".html", "").split("_")
        if len(parts) < 3:
            continue
        ec_code = parts[0]
        city_code = parts[1].replace("city", "")
        sgg_code = parts[2].replace("sgg", "")

        fpath = os.path.join(RAW_DIR, fname)
        rows = parse_html_file(fpath, ec_code, city_code, sgg_code)
        all_rows.extend(rows)

    if not all_rows:
        print("파싱된 데이터가 없습니다. 개표 데이터가 아직 없을 수 있습니다.")
        return

    new_df = pd.DataFrame(all_rows, columns=FINAL_COLS)

    # 기존 CSV에서 9회차 제거 후 추가 (재실행 안전)
    existing_df = pd.read_csv(OUT_PATH)
    existing_df = existing_df[existing_df["선거_회차"] != ELECTION_ROUND]
    combined = pd.concat([existing_df, new_df], ignore_index=True)
    combined.to_csv(OUT_PATH, index=False)

    print(f"완료: {len(new_df):,}행 추가 → {OUT_PATH}")
    print(new_df.groupby(["선거종류"]).size().to_string())


if __name__ == "__main__":
    main()
