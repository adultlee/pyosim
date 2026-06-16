"""17대(2007) 대통령선거 파서. 시도별 xls 파일 처리."""

import os
import re
import pandas as pd

from etl.pres.schema import normalize_level

RAW_DIR = "data_raw/대통령선거 개표결과(제14대~제18대)/제17대 대통령선거 개표자료"
ROUND = 17

SIDO_FROM_FILENAME = {
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


def _parse_cand_col(col_name):
    col_name = col_name.strip()
    if "\n" in col_name:
        parts = col_name.split("\n", 1)
        return parts[0].strip(), parts[1].strip()
    tokens = col_name.split()
    if len(tokens) >= 2:
        return " ".join(tokens[:-1]), tokens[-1]
    return col_name, ""


def _parse_file(filepath, sido_name):
    raw = pd.read_excel(filepath, header=None)
    parties = raw.iloc[1, 6:].tolist()
    names   = raw.iloc[2, 6:].tolist()

    cand_labels = []
    for party, name in zip(parties, names):
        party_str = str(party).strip()
        name_str  = str(name).strip()
        if party_str in ("nan", "계", "무효\n투표수", "기권수", "무효투표수") or name_str in ("nan",):
            continue
        if "무효" in party_str or "기권" in party_str or party_str == "계":
            continue
        cand_labels.append(f"{party_str}\n{name_str}")

    data = raw.iloc[3:].copy()
    base_cols = ["구시군", "읍면동", "투표구", "선거인수", "투표용지교부수", "투표수"]
    all_cols = base_cols + [
        str(raw.iloc[1, 6 + i]) + "\n" + str(raw.iloc[2, 6 + i])
        for i in range(raw.shape[1] - 6)
    ]
    data.columns = all_cols[: data.shape[1]]

    data["구시군"] = data["구시군"].ffill()
    data["읍면동"] = data["읍면동"].ffill()

    # totals: 읍면동 합계행 (구시군별 집계)
    total_mask = data["읍면동"].astype(str).str.contains("합계", na=False)
    totals_raw = data[total_mask].copy()
    totals_raw["투표수"] = _clean_num(totals_raw["투표수"])
    totals = [
        {"시도": sido_name, "구시군": row["구시군"], "투표수": row["투표수"]}
        for _, row in totals_raw.iterrows()
        if pd.notna(row["구시군"]) and "합계" not in str(row["구시군"])
    ]

    remove_mask = data["읍면동"].astype(str).str.contains("합계", na=False)
    remove_mask |= data["구시군"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= data["투표구"].astype(str).str.contains("소계", na=False)
    data = data[~remove_mask].copy()

    invalid_col = next((c for c in data.columns if "무효" in str(c)), None)
    abstain_col = next((c for c in data.columns if "기권" in str(c)), None)

    for col in ["선거인수", "투표수"] + cand_labels:
        if col in data.columns:
            data[col] = _clean_num(data[col])
    if invalid_col:
        data[invalid_col] = _clean_num(data[invalid_col])
    if abstain_col:
        data[abstain_col] = _clean_num(data[abstain_col])

    rows = []
    for _, row in data.iterrows():
        tpgu = str(row["투표구"]) if pd.notna(row["투표구"]) else ""
        for label in cand_labels:
            party, name = _parse_cand_col(label)
            rows.append({
                "선거_회차": ROUND,
                "선거일": "2007-12-19",
                "시도": sido_name,
                "구시군": row["구시군"],
                "읍면동": row["읍면동"],
                "투표구": tpgu,
                "선거인수": row["선거인수"],
                "투표수": row["투표수"],
                "후보자": name,
                "정당": party,
                "득표수": row.get(label),
                "무효투표수": row[invalid_col] if invalid_col else None,
                "기권수": row[abstain_col] if abstain_col else None,
                "level": normalize_level(tpgu),
            })
    return rows, totals


def parse_17(raw_dir=RAW_DIR):
    all_rows, all_totals = [], []
    for filename in sorted(os.listdir(raw_dir)):
        if not filename.endswith(".xls"):
            continue
        match = re.search(r"_([가-힣]+)\.xls$", filename)
        if not match:
            continue
        sido_name = SIDO_FROM_FILENAME.get(match.group(1), "")
        if not sido_name:
            continue
        filepath = os.path.join(raw_dir, filename)
        rows, totals = _parse_file(filepath, sido_name)
        all_rows.extend(rows)
        all_totals.extend(totals)
    return all_rows, all_totals
