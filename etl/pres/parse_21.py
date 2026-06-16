# etl/pres/parse_21.py
"""21대(2025) 대통령선거 파서."""

import pandas as pd
from etl.pres.schema import normalize_level

RAW_PATH = "data_raw/제21대_대통령선거_개표결과.xlsx"
ROUND = 21


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


def parse_21(path=RAW_PATH):
    raw = pd.read_excel(path, header=None)

    cand_labels = []
    for val in raw.iloc[4, 6:].tolist():
        v = str(val).strip()
        if v in ("nan", "계", "NaN", ""):
            continue
        cand_labels.append(v)

    data = raw.iloc[6:].copy()
    data.columns = ["시도", "구시군", "읍면동", "투표구", "선거인수", "투표수",
                    *cand_labels, "계", "무효투표수", "기권수"]
    data["시도"] = data["시도"].ffill()
    data["구시군"] = data["구시군"].ffill()
    data["읍면동"] = data["읍면동"].ffill()

    total_mask = data["읍면동"].astype(str).str.contains("합계", na=False)
    totals_raw = data[total_mask].copy()
    totals_raw["투표수"] = _clean_num(totals_raw["투표수"])
    totals = [
        {"시도": row["시도"], "구시군": row["구시군"], "투표수": row["투표수"]}
        for _, row in totals_raw.iterrows()
        if pd.notna(row["구시군"]) and "합계" not in str(row["구시군"])
        and "전국" not in str(row["시도"])
    ]

    remove_mask = data["읍면동"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= data["구시군"].astype(str).str.contains("합계|소계|합계\\(특별시\\)|합계\\(광역시\\)|합계\\(도\\)", na=False)
    remove_mask |= data["시도"].astype(str).str.contains("전국", na=False)
    remove_mask |= data["투표구"].astype(str).str.contains("소계", na=False)
    data = data[~remove_mask].copy()

    for col in ["선거인수", "투표수", "무효투표수", "기권수"] + cand_labels:
        if col in data.columns:
            data[col] = _clean_num(data[col])

    rows = []
    for _, row in data.iterrows():
        tpgu = str(row["투표구"]) if pd.notna(row["투표구"]) else ""
        for label in cand_labels:
            party, name = _parse_cand_col(label)
            rows.append({
                "선거_회차": ROUND,
                "선거일": "2025-06-03",
                "시도": row["시도"],
                "구시군": row["구시군"],
                "읍면동": row["읍면동"],
                "투표구": tpgu,
                "선거인수": row["선거인수"],
                "투표수": row["투표수"],
                "후보자": name,
                "정당": party,
                "득표수": row[label],
                "무효투표수": row["무효투표수"],
                "기권수": row["기권수"],
                "level": normalize_level(tpgu),
            })
    return rows, totals
