"""검증 게이트. 파서가 원본을 그대로 옮겼는지 검사한다."""

import pandas as pd

KEY_COLS = ["선거_회차", "선거구분", "시도", "구시군", "읍면동", "투표구", "선거구명", "후보자", "정당", "level"]


def check_no_duplicate_rows(df):
    dup_mask = df.duplicated(subset=KEY_COLS, keep=False)
    if not dup_mask.any():
        return []
    errors = []
    dups = df[dup_mask].groupby(KEY_COLS, dropna=False).size()
    for key, count in dups.items():
        errors.append(("duplicate_rows", f"{key} → {count}건 중복"))
    return errors


def check_value_ranges(df):
    """득표 ≤ 투표수 ≤ 선거인수 위반 검사."""
    errors = []
    votes = df["득표수"].fillna(0)
    turnout = df["투표수"].fillna(0)
    over_votes = df[votes > turnout]
    for _, row in over_votes.iterrows():
        errors.append((
            "value_range",
            f"{row['시도']} {row['선거구명']} {row['읍면동']} {row['투표구']} "
            f"{row['후보자']} 득표 {row['득표수']} > 투표수 {row['투표수']}",
        ))
    electorate = pd.to_numeric(df["선거인수"], errors="coerce")
    zero_electorate_mask = electorate.fillna(0) == 0
    presub_mask = df["level"].isin({"사전투표", "관외사전투표"})
    over_turnout = df[
        ~zero_electorate_mask & ~presub_mask
        & electorate.notna() & (turnout > electorate)
    ]
    for _, row in over_turnout.iterrows():
        errors.append((
            "value_range",
            f"{row['시도']} {row['선거구명']} {row['읍면동']} {row['투표구']} "
            f"{row['후보자']} 투표수 {row['투표수']} > 선거인수 {row['선거인수']}",
        ))
    return errors


def _turnout_per_precinct(df, 선거구분, 시도, 선거구명):
    """한 선거구의 세분 단위 투표수 합."""
    sub = df[
        (df["선거구분"] == 선거구분)
        & (df["시도"] == 시도)
        & (df["선거구명"] == 선거구명)
    ]
    per = sub.drop_duplicates(subset=["구시군", "읍면동", "투표구", "level"])
    return int(per["투표수"].fillna(0).sum())


def check_totals_match(df, totals):
    """파서가 넘긴 선거구 합계행 투표수 == 세분 단위 투표수 합."""
    errors = []
    for total in totals:
        actual = _turnout_per_precinct(df, total["선거구분"], total["시도"], total["선거구명"])
        expected = int(total["투표수"])
        if actual != expected:
            errors.append((
                "totals_mismatch",
                f"{total['선거구분']} {total['시도']} {total['선거구명']}: "
                f"세분합 {actual} != 합계행 {expected} (차 {actual - expected})",
            ))
    return errors


def check_official_totals(df, official_top):
    """시도 단위 후보 득표 합이 공식 득표와 일치하는지 대조."""
    errors = []
    for (회차, 선거구분, 시도), (cand, votes) in official_top.items():
        sub = df[
            (df["선거_회차"] == 회차)
            & (df["선거구분"] == 선거구분)
            & (df["시도"] == 시도)
            & (df["후보자"] == cand)
        ]
        if sub.empty:
            continue
        actual = int(sub["득표수"].fillna(0).sum())
        if actual != votes:
            errors.append((
                "official_mismatch",
                f"{회차} {선거구분} {시도} {cand}: "
                f"집계 {actual} != 공식 {votes} (차 {actual - votes})",
            ))
    return errors


def run_all_checks(df, totals, official_top=None):
    """모든 검사를 실행하고 위반을 합쳐 반환."""
    errors = []
    errors += check_no_duplicate_rows(df)
    errors += check_value_ranges(df)
    errors += check_totals_match(df, totals)
    if official_top:
        errors += check_official_totals(df, official_top)
    return errors
