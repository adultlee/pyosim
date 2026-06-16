"""16대(2002) 대통령선거 파서."""

import re
import pandas as pd

from etl.pres.schema import normalize_level

RAW_PATH = "data_raw/대통령선거 개표결과(제14대~제18대)/제16대 대통령선거 개표자료.xls"
RAW_18_PATH = "data_raw/대통령선거 개표결과(제14대~제18대)/제18대 대통령선거 개표자료.xls"
ROUND = 16

PARTY_MAP = {
    "이회창": "한나라당",
    "노무현": "새천년민주당",
    "이한동": "하나로국민연합",
    "권영길": "민주노동당",
    "김영규": "사회당",
    "김길수": "무소속",
}

GUGUN_SIDO_EXTRA = {
    "양주군": "경기도", "고양시일산구": "경기도", "용인시": "경기도",
    "포천군": "경기도", "천안시": "충청남도", "연기군": "충청남도",
    "당진군": "충청남도", "창원시": "경상남도", "마산시": "경상남도",
    "진해시": "경상남도", "북제주군": "제주특별자치도", "남제주군": "제주특별자치도",
}

SIDO_SHORT = {
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시",
    "인천": "인천광역시", "광주": "광주광역시", "대전": "대전광역시",
    "울산": "울산광역시", "경기": "경기도", "강원": "강원도",
    "충북": "충청북도", "충남": "충청남도", "전북": "전라북도",
    "전남": "전라남도", "경북": "경상북도", "경남": "경상남도",
    "제주": "제주특별자치도",
}


def _clean_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def _build_gugun_sido_map():
    raw = pd.read_excel(RAW_18_PATH, header=None)
    data = raw.iloc[5:].copy()
    data.columns = ["_", "시도", "구시군"] + list(range(data.shape[1] - 3))
    data["시도"] = data["시도"].ffill()
    g = (
        data[["시도", "구시군"]]
        .dropna(subset=["구시군"])
        .pipe(lambda d: d[~d["구시군"].astype(str).str.contains("합계|소계", na=False)])
    )
    # 같은 구시군명이 여러 시도에 있을 수 있으므로 첫 번째 등장값 사용
    mapping = (
        g.groupby("구시군", sort=False)["시도"]
        .first()
        .str.strip()
        .to_dict()
    )
    mapping.update(GUGUN_SIDO_EXTRA)
    return mapping


_GUGUN_SIDO_MAP = None


def _get_gugun_sido_map():
    global _GUGUN_SIDO_MAP
    if _GUGUN_SIDO_MAP is None:
        _GUGUN_SIDO_MAP = _build_gugun_sido_map()
    return _GUGUN_SIDO_MAP


def _lookup_sido(committee):
    gugun_sido = _get_gugun_sido_map()
    raw = committee.strip("[] ")
    match = re.search(r"\(([^)]+)\)", raw)
    if match:
        return SIDO_SHORT.get(match.group(1), match.group(1))
    gugun_name = raw
    return gugun_sido.get(gugun_name, "")


def parse_16(path=RAW_PATH):
    cand_cols = ["이회창", "노무현", "이한동", "권영길", "김영규", "김길수"]
    raw = pd.read_excel(path, header=0)

    raw["읍면동명"] = raw["읍면동명"].ffill()

    total_mask = raw["읍면동명"].astype(str).str.contains("합계", na=False)
    totals_raw = raw[total_mask].copy()
    totals_raw["투표수"] = _clean_num(totals_raw["투표수"])
    totals = []
    for _, row in totals_raw.iterrows():
        committee = str(row["위원회명"])
        sido = _lookup_sido(committee)
        gugun_raw = committee.strip("[] ")
        gugun = re.sub(r"\([^)]*\)", "", gugun_raw).strip()
        if sido and "합계" not in gugun:
            totals.append({"시도": sido, "구시군": gugun, "투표수": row["투표수"]})

    remove_mask = raw["읍면동명"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= raw["투표구명"].astype(str).str.contains("소계", na=False)
    data = raw[~remove_mask].copy()

    for col in ["선거인수", "투표수", "무표투표수", "기권수"] + cand_cols:
        if col in data.columns:
            data[col] = _clean_num(data[col])

    rows = []
    for _, row in data.iterrows():
        committee = str(row["위원회명"])
        sido = _lookup_sido(committee)
        gugun_raw = committee.strip("[] ")
        gugun = re.sub(r"\([^)]*\)", "", gugun_raw).strip()
        eupmyeong = str(row["읍면동명"]) if pd.notna(row["읍면동명"]) else ""
        tpgu = str(row["투표구명"]) if pd.notna(row["투표구명"]) else ""

        for cand in cand_cols:
            rows.append({
                "선거_회차": ROUND,
                "선거일": "2002-12-19",
                "시도": sido,
                "구시군": gugun,
                "읍면동": eupmyeong,
                "투표구": tpgu,
                "선거인수": row.get("선거인수"),
                "투표수": row.get("투표수"),
                "후보자": cand,
                "정당": PARTY_MAP.get(cand, ""),
                "득표수": row.get(cand),
                "무효투표수": row.get("무표투표수"),
                "기권수": row.get("기권수"),
                "level": normalize_level(tpgu),
            })
    return rows, totals
