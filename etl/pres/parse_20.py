# etl/pres/parse_20.py
"""20대(2022) 대통령선거 파서."""

import pandas as pd
from etl.pres.schema import normalize_level

RAW_PATH = "data_raw/개표단위별_개표결과_대통령선거_전체.xlsx"
ROUND = 20


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


def parse_20(path=RAW_PATH):
    raw = pd.read_excel(path, sheet_name="Data", header=0)

    fixed_cols = ["시도", "구시군", "읍면동명", "투표구명", "선거인수", "투표수"]
    all_cols = raw.columns.tolist()
    cand_end = all_cols.index("계")
    cand_labels = all_cols[len(fixed_cols):cand_end]

    raw["시도"] = raw["시도"].ffill()
    raw["구시군"] = raw["구시군"].ffill()
    raw["읍면동명"] = raw["읍면동명"].ffill()

    total_mask = raw["읍면동명"].astype(str).str.contains("합계", na=False)
    totals_raw = raw[total_mask].copy()
    totals_raw["투표수"] = _clean_num(totals_raw["투표수"])
    totals = [
        {"시도": row["시도"], "구시군": row["구시군"], "투표수": row["투표수"]}
        for _, row in totals_raw.iterrows()
        if pd.notna(row["구시군"]) and "합계" not in str(row["구시군"])
        and "전국" not in str(row["시도"])
    ]

    remove_mask = raw["읍면동명"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= raw["구시군"].astype(str).str.contains("합계|소계|합계\\(특별시\\)|합계\\(광역시\\)|합계\\(도\\)", na=False)
    remove_mask |= raw["시도"].astype(str).str.contains("전국", na=False)
    remove_mask |= raw["투표구명"].astype(str).str.contains("소계", na=False)
    data = raw[~remove_mask].copy()

    for col in ["선거인수", "투표수", "무효투표수", "기권수"] + cand_labels:
        if col in data.columns:
            data[col] = _clean_num(data[col])

    rows = []
    for _, row in data.iterrows():
        tpgu = str(row["투표구명"]) if pd.notna(row["투표구명"]) else ""
        for label in cand_labels:
            party, name = _parse_cand_col(label)
            rows.append({
                "선거_회차": ROUND,
                "선거일": "2022-03-09",
                "시도": row["시도"],
                "구시군": row["구시군"],
                "읍면동": row["읍면동명"],
                "투표구": tpgu,
                "선거인수": row["선거인수"],
                "투표수": row["투표수"],
                "후보자": name,
                "정당": party,
                "득표수": row[label],
                "무효투표수": row.get("무효투표수"),
                "기권수": row.get("기권수"),
                "level": normalize_level(tpgu),
            })
    return rows, totals
