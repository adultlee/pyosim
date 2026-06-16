"""14대(1992) 대통령선거 파서."""

import pandas as pd

from etl.pres.schema import normalize_level

RAW_PATH = "data_raw/대통령선거 개표결과(제14대~제18대)/제14대 대통령선거 개표자료.xls"
ROUND = 14


def _clean_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )


def _parse_cand_col(col_name):
    col_name = col_name.strip()
    if "\n" in col_name:
        parts = col_name.split("\n", 1)
        return parts[0].strip(), parts[1].strip()
    tokens = col_name.split()
    if len(tokens) >= 2:
        return " ".join(tokens[:-1]), tokens[-1]
    return col_name, ""


def parse_14(path=RAW_PATH):
    raw = pd.read_excel(path, header=None)
    parties = raw.iloc[2, 7:15].tolist()
    names   = raw.iloc[3, 7:15].tolist()
    cand_labels = [f"{p}\n{n}" for p, n in zip(parties, names)]

    data = raw.iloc[4:].copy()
    data.columns = [
        "시도", "구시군", "읍면동",
        "선거인수", "부재자수", "투표자수", "부재자투표자수",
        *cand_labels, "계", "무효투표수", "기권수",
    ]
    data["시도"] = data["시도"].ffill()
    data["구시군"] = data["구시군"].ffill()

    # 구시군별 합계: 읍면동='소계' + 구시군이 실제 구시군명인 행
    sogyae_mask = data["읍면동"].astype(str).str.strip() == "소계"
    totals_raw = data[sogyae_mask].copy()
    totals_raw["투표자수"] = _clean_num(totals_raw["투표자수"])
    totals = [
        {"시도": row["시도"], "구시군": row["구시군"], "투표수": row["투표자수"]}
        for _, row in totals_raw.iterrows()
        if pd.notna(row["구시군"]) and "합계" not in str(row["구시군"])
        and "전국" not in str(row["시도"])
    ]

    # '소계동' 같은 실제 읍면동명이 '소계' 패턴에 걸리지 않도록 정확히 일치 검사
    remove_mask = data["읍면동"].astype(str).str.strip().isin(["소계", "합계"])
    remove_mask |= data["구시군"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= data["시도"].astype(str).str.contains("전국", na=False)
    data = data[~remove_mask].copy()

    num_cols = ["선거인수", "투표자수", "무효투표수", "기권수"] + cand_labels
    for col in num_cols:
        if col in data.columns:
            data[col] = _clean_num(data[col])

    rows = []
    for _, row in data.iterrows():
        for label in cand_labels:
            party, name = _parse_cand_col(label)
            rows.append({
                "선거_회차": ROUND,
                "선거일": "1992-12-18",
                "시도": row["시도"],
                "구시군": row["구시군"],
                "읍면동": row["읍면동"],
                "투표구": "",
                "선거인수": row["선거인수"],
                "투표수": row["투표자수"],
                "후보자": name,
                "정당": party,
                "득표수": row[label],
                "무효투표수": row["무효투표수"],
                "기권수": row["기권수"],
                "level": normalize_level(row["읍면동"]),
            })
    return rows, totals
