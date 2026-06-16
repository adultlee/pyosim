"""18대(2012) 대통령선거 파서."""

import pandas as pd

from etl.pres.schema import normalize_level

RAW_PATH = "data_raw/대통령선거 개표결과(제14대~제18대)/제18대 대통령선거 개표자료.xls"
ROUND = 18


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


def parse_18(path=RAW_PATH):
    raw = pd.read_excel(path, header=None)
    # row4: 후보자별 컬럼명 (col7~12)
    parties_row = raw.iloc[4, 7:13].tolist()
    cand_labels = [
        str(party).strip()
        for party in parties_row
        if str(party).strip() not in ("nan", "계", "NaN")
    ]

    data = raw.iloc[5:].copy()
    data.columns = [
        "_", "시도", "구시군", "읍면동", "투표구", "선거인수", "투표수",
        *cand_labels, "계", "무효투표수", "기권수",
    ]
    data["시도"] = data["시도"].ffill()
    data["구시군"] = data["구시군"].ffill()
    data["읍면동"] = data["읍면동"].ffill()

    # 구시군별 합계: 읍면동='소계' + 투표구=NaN인 행.
    # 18대 원본에는 구시군마다 소계 행이 두 개 있음:
    #   첫 번째 = 재외·부재자 포함 전체 합계 (이것이 실제 구시군 합계)
    #   두 번째 = 현장투표(당일투표)만의 합계
    # 같은 (시도, 구시군)에서 첫 번째 소계만 totals에 사용한다.
    sogyae_mask = (
        data["읍면동"].astype(str).str.strip() == "소계"
    ) & data["투표구"].isna()
    totals_raw = data[sogyae_mask].copy()
    totals_raw["투표수"] = _clean_num(totals_raw["투표수"])
    # 같은 구시군에서 첫 번째만 유지
    totals_raw = totals_raw[
        pd.notna(totals_raw["구시군"])
        & ~totals_raw["구시군"].astype(str).str.contains("합계", na=False)
        & ~totals_raw["시도"].astype(str).str.contains("전국", na=False)
    ]
    totals_raw = totals_raw.groupby(["시도", "구시군"], sort=False).first().reset_index()
    totals = [
        {"시도": row["시도"], "구시군": row["구시군"], "투표수": row["투표수"]}
        for _, row in totals_raw.iterrows()
    ]

    remove_mask = data["읍면동"].astype(str).str.contains("합계|소계", na=False)
    remove_mask |= data["구시군"].astype(str).str.contains("합계|소계", na=False)
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
                "선거일": "2012-12-19",
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
