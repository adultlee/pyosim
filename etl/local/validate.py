"""검증 게이트. 파서가 원본을 그대로 옮겼는지 검사한다.

각 check는 위반 리스트 [(check_name, detail), ...]를 반환. 빈 리스트 = 통과.
원본은 항상 옳다. 위반 = 파서 버그.
"""

import pandas as pd

KEY_COLS = ["선거_회차", "선거종류", "시도", "구시군", "읍면동", "level", "후보자", "정당"]


def check_no_duplicate_rows(df):
    """같은 (회차,선거종류,시도,구시군,읍면동,level,후보자)가 두 번 나오면 위반."""
    dup_mask = df.duplicated(subset=KEY_COLS, keep=False)
    if not dup_mask.any():
        return []
    errors = []
    dups = df[dup_mask].groupby(KEY_COLS, dropna=False).size()
    for key, count in dups.items():
        errors.append(("duplicate_rows", f"{key} → {count}건 중복"))
    return errors


def check_value_ranges(df):
    """득표 ≤ 투표수 ≤ 선거인수 위반 검사. 잘못투입 행은 선거인수가 없으므로 제외."""
    valid = df[df["level"] != "잘못투입"]
    errors = []
    votes = valid["득표수"].fillna(0)
    turnout = valid["투표수"].fillna(0)
    over_votes = valid[votes > turnout]
    for _, row in over_votes.iterrows():
        errors.append((
            "value_range",
            f"{row['시도']} {row['구시군']} {row['읍면동']} "
            f"{row['후보자']} 득표 {row['득표수']} > 투표수 {row['투표수']}",
        ))
    electorate = pd.to_numeric(valid["선거인수"], errors="coerce")
    # tolerance=2: 선관위 원본에서 투표수가 선거인수를 1~2 초과하는 경우가 있음 (원본 데이터 오류)
    over_turnout = valid[electorate.notna() & (turnout > electorate + 2)]
    for _, row in over_turnout.iterrows():
        errors.append((
            "value_range",
            f"{row['시도']} {row['구시군']} {row['읍면동']} "
            f"{row['후보자']} 투표수 {row['투표수']} > 선거인수 {row['선거인수']}",
        ))
    return errors


SIDO_SCOPED_TYPES = {"시도지사", "교육감"}


def check_sido_candidate_consistency(df):
    """시도 단위 선거(시도지사·교육감)에서 후보 집합이 시도마다 서로 달라야 한다.
    두 시도의 후보 집합이 완전히 같으면 파서가 한 시도 헤더를 다른 시도에
    잘못 복사한 것. 광역비례는 정당이 식별자라 전국 동일이 정상이므로 제외."""
    errors = []
    scoped = df[df["선거종류"].isin(SIDO_SCOPED_TYPES)]
    for (회차, 선거종류), group in scoped.groupby(["선거_회차", "선거종류"]):
        # 시도별 식별자 집합 (후보자 없으면 정당)
        ident = group["후보자"].fillna(group["정당"])
        sido_sets = {}
        for sido, sub_idx in group.groupby("시도").groups.items():
            sido_sets[sido] = frozenset(ident.loc[sub_idx].dropna().unique())
        sidos = list(sido_sets)
        for i in range(len(sidos)):
            for j in range(i + 1, len(sidos)):
                sido_a, sido_b = sidos[i], sidos[j]
                if sido_sets[sido_a] and sido_sets[sido_a] == sido_sets[sido_b]:
                    errors.append((
                        "sido_candidate_collision",
                        f"{회차}회 {선거종류}: {sido_a} 후보집합 == {sido_b} "
                        f"{set(list(sido_sets[sido_a])[:4])} → 시도 헤더 복사 의심",
                    ))
    return errors


def _turnout_per_precinct(df, 선거종류, 시도, 구시군):
    """한 구시군의 세분 단위 투표수 합. 투표수는 (읍면동,level)당 한 번만
    세야 하므로 후보 행 중복을 제거하고 합산한다."""
    sub = df[
        (df["선거종류"] == 선거종류)
        & (df["시도"] == 시도)
        & (df["구시군"] == 구시군)
    ]
    per = sub.drop_duplicates(subset=["읍면동", "level"])
    return int(per["투표수"].fillna(0).sum())


def check_totals_match(df, totals):
    """파서가 넘긴 구시군 합계행 투표수 == 세분 단위 투표수 합."""
    errors = []
    for total in totals:
        actual = _turnout_per_precinct(
            df, total["선거종류"], total["시도"], total["구시군"]
        )
        expected = int(total["투표수"])
        if actual != expected:
            errors.append((
                "totals_mismatch",
                f"{total['선거종류']} {total['시도']} {total['구시군']}: "
                f"세분합 {actual} != 합계행 {expected} (차 {actual - expected})",
            ))
    return errors


def check_official_totals(df, official_top):
    """시도 단위 후보 득표 합이 공식 1위 득표와 일치하는지 대조.
    df에 해당 시도·후보 행이 없으면 건너뛴다 (데이터 미적재 ≠ 파서 버그)."""
    errors = []
    for (회차, 선거종류, 시도), (cand, votes) in official_top.items():
        sub = df[
            (df["선거_회차"] == 회차)
            & (df["선거종류"] == 선거종류)
            & (df["시도"] == 시도)
            & (df["후보자"] == cand)
        ]
        if sub.empty:
            continue
        actual = int(sub["득표수"].fillna(0).sum())
        if actual != votes:
            errors.append((
                "official_mismatch",
                f"{회차}회 {선거종류} {시도} {cand}: "
                f"집계 {actual} != 공식 {votes} (차 {actual - votes})",
            ))
    return errors


def run_all_checks(df, totals, official_top=None, skip_sido_consistency=False):
    """모든 검사를 실행하고 위반을 합쳐 반환."""
    errors = []
    errors += check_no_duplicate_rows(df)
    errors += check_value_ranges(df)
    if not skip_sido_consistency:
        errors += check_sido_candidate_consistency(df)
    errors += check_totals_match(df, totals)
    if official_top:
        errors += check_official_totals(df, official_top)
    return errors
