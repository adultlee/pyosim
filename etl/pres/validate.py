"""검증 게이트. 파서가 원본을 그대로 옮겼는지 검사한다.

각 check는 위반 리스트 [(check_name, detail), ...]를 반환. 빈 리스트 = 통과.
원본은 항상 옳다. 위반 = 파서 버그.
"""

import pandas as pd

KEY_COLS = ["선거_회차", "시도", "구시군", "읍면동", "투표구", "level", "후보자", "정당"]


def check_no_duplicate_rows(df):
    """같은 (회차,시도,구시군,읍면동,level,후보자)가 두 번 나오면 위반."""
    dup_mask = df.duplicated(subset=KEY_COLS, keep=False)
    if not dup_mask.any():
        return []
    errors = []
    dups = df[dup_mask].groupby(KEY_COLS, dropna=False).size()
    for key, count in dups.items():
        errors.append(("duplicate_rows", f"{key} → {count}건 중복"))
    return errors


_SPECIAL_UMYEONDONG = ("잘못 투입",)  # 선거인수=0이 정상인 특수 행


def check_value_ranges(df):
    """득표 ≤ 투표수 ≤ 선거인수 위반 검사.

    '잘못 투입·구분된 투표지' 행은 선관위가 별도 집계한 특수 행으로
    선거인수=0이더라도 투표수>0일 수 있으므로 선거인수 비교에서 제외한다.
    """
    errors = []
    votes = df["득표수"].fillna(0)
    turnout = df["투표수"].fillna(0)
    over_votes = df[votes > turnout]
    for _, row in over_votes.iterrows():
        errors.append((
            "value_range",
            f"{row['시도']} {row['구시군']} {row['읍면동']} "
            f"{row['후보자']} 득표 {row['득표수']} > 투표수 {row['투표수']}",
        ))
    special_mask = df["읍면동"].astype(str).str.contains(
        "|".join(_SPECIAL_UMYEONDONG), na=False
    )
    electorate = pd.to_numeric(df["선거인수"], errors="coerce")
    # 선거인수=0인 행은 재외투표·잘못투입 등 특수 집계 단위로 원본상 정상
    zero_electorate_mask = electorate.fillna(0) == 0
    # 사전투표는 관외 사전투표자가 포함되어 투표수>선거인수가 소규모 발생할 수 있음 (원본 특성)
    presub_mask = df["level"].isin({"사전투표", "관외사전투표"})
    # 기권수가 음수인 행은 원본 데이터 자체의 인쇄/집계 오류 (예: 14대 경남 의령군 낙서면)
    absten = pd.to_numeric(df.get("기권수", pd.Series(dtype=float)), errors="coerce")
    raw_error_mask = absten.fillna(0) < 0
    over_turnout = df[
        ~special_mask & ~zero_electorate_mask & ~presub_mask & ~raw_error_mask
        & electorate.notna() & (turnout > electorate)
    ]
    for _, row in over_turnout.iterrows():
        errors.append((
            "value_range",
            f"{row['시도']} {row['구시군']} {row['읍면동']} "
            f"{row['후보자']} 투표수 {row['투표수']} > 선거인수 {row['선거인수']}",
        ))
    return errors


def _turnout_per_gugun(df, 시도, 구시군):
    """한 구시군의 세분 단위 투표수 합. 투표수는 (읍면동,투표구,level)당 한 번만
    세야 하므로 후보 행 중복을 제거하고 합산한다."""
    sub = df[(df["시도"] == 시도) & (df["구시군"] == 구시군)]
    per = sub.drop_duplicates(subset=["읍면동", "투표구", "level"])
    return int(per["투표수"].fillna(0).sum())


def check_totals_match(df, totals):
    """파서가 넘긴 구시군 합계행 투표수 == 세분 단위 투표수 합."""
    errors = []
    for total in totals:
        actual = _turnout_per_gugun(df, total["시도"], total["구시군"])
        expected = int(total["투표수"])
        if actual != expected:
            errors.append((
                "totals_mismatch",
                f"{total['시도']} {total['구시군']}: "
                f"세분합 {actual} != 합계행 {expected} (차 {actual - expected})",
            ))
    return errors


def check_official_totals(df, official_top):
    """시도 단위 후보 득표 합이 공식 득표와 일치하는지 대조.
    df에 해당 시도·후보 행이 없으면 건너뛴다 (데이터 미적재 ≠ 파서 버그)."""
    errors = []
    for (회차, 시도), (cand, votes) in official_top.items():
        sub = df[
            (df["선거_회차"] == 회차)
            & (df["시도"] == 시도)
            & (df["후보자"] == cand)
        ]
        if sub.empty:
            continue
        actual = int(sub["득표수"].fillna(0).sum())
        if actual != votes:
            errors.append((
                "official_mismatch",
                f"{회차}대 {시도} {cand}: "
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
