"""쌍둥이 득표 분석.

기준: 같은 '비교 단위' 안에서, 서로 다른 두 읍면동에 인접 순위 두 후보의
(이름, 득표수)가 동시에 일치하면 쌍둥이.

비교 단위 (선거별 group key):
  - 대선            : (회차, level) — 전국 단위
  - 총선 지역구      : (회차, 선거구분, 선거구명, level)
  - 총선 비례        : (회차, 선거구분, level) — 전국 단위
  - 지방선거 시도지사·교육감·광역비례 : (회차, 선거종류, 시도그룹, level)
    시도그룹 = 같은 후보 집합을 가진 시도들을 하나의 선거로 묶음
    (예: 광주+전남 통합 시도지사 → '광주광역시·전라남도')
  - 지방선거 나머지  : (회차, 선거종류, 시도, 구시군, level)

순위 쌍 기준:
  투표구 내 득표 내림차순으로 인접한 두 후보(1·2위, 2·3위, …)를 각각
  독립 버킷으로 집계. 동점 시 CSV 행 순서(원본 기호순) 유지.
  중복 허용: 같은 투표구가 여러 순위 쌍 버킷에 동시 등장 가능.

잘못투입 계열 level은 분석 대상에서 제외한다.

출력:
  web/public/twin_votes_index.json
  web/public/twin_votes_지방선거_{N}.json
  web/public/twin_votes_총선_{회차}.json
  web/public/twin_votes_대선_{N}.json
"""

import json
import re
from collections import defaultdict

import pandas as pd

JUNK_LEVELS = {"잘못투입", "잘못 투입·구분된 투표지"}

SIDO_WIDE_RACES = {"시도지사", "광역비례", "교육감"}

OUT_DIR = "web/public"

# 최소 일치 투표구 수: 2개 = 서로 다른 두 투표소에서 반복되면 쌍둥이(정의 그대로).
# (과거 3으로 올렸던 건 0표 노이즈로 파일이 컸기 때문 — 이제 MIN_VOTE_THRESHOLD로 걸러 2로 둔다.)
MIN_TWIN_COUNT = 2

# 최소 득표 임계값: 두 후보 모두 이 값 이상인 동률만 쌍둥이로 인정.
# 1~9표 군소후보 저득표 동률은 노이즈이므로 제외 (CLAUDE.md 핵심 품질 기준).
MIN_VOTE_THRESHOLD = 10


def _rank_pair_buckets(cands: list, prefix: tuple, location_entry: dict,
                       buckets: defaultdict) -> None:
    """투표구 후보 목록에서 인접 순위 쌍을 뽑아 버킷에 추가.

    cands: [(식별자, 득표수), ...] — CSV 행 순서 그대로(기호순).
    동점 시 원본 순서(기호순) 유지를 위해 stable sort.
    버킷 키: prefix + (rank,) + (cand1, vote1) + (cand2, vote2)
    """
    if len(cands) < 2:
        return
    ranked = sorted(enumerate(cands), key=lambda idx_pair: -idx_pair[1][1])
    ranked_cands = [cand_vote for _, cand_vote in ranked]
    for rank in range(len(ranked_cands) - 1):
        pair = (ranked_cands[rank], ranked_cands[rank + 1])
        bucket_key = prefix + (rank + 1,) + pair  # rank 1-based
        buckets[bucket_key].append(location_entry)


def _build_party_map(df: pd.DataFrame) -> dict:
    """식별자(후보자 또는 정당) → 정당명 매핑. 인물 후보는 소속 정당, 비례는 정당=식별자.

    동명이인이 다른 정당이면 마지막 값으로 덮어쓰나, 동률 쌍 표시용이라 실무상 충분하다.
    """
    party_map: dict = {}
    sub = df.dropna(subset=["식별자"])
    for identifier, party in zip(sub["식별자"].tolist(), sub["정당"].tolist()):
        if isinstance(party, str) and party:
            party_map[identifier] = party
        else:
            party_map.setdefault(identifier, identifier)
    return party_map


def _parties_for(candidates: tuple, party_map: dict) -> dict:
    """동률 두 후보의 {후보: 정당} 맵. 매핑 없으면 생략."""
    result = {}
    for cand, _ in candidates:
        party = party_map.get(cand)
        if party:
            result[cand] = party
    return result


def _build_sido_groups(df: pd.DataFrame) -> dict:
    """시도 전체 선거에서 같은 후보 집합을 가진 시도들을 하나의 그룹 키로 묶는다.

    반환: {(회차, 선거종류, 시도): group_key_string}
    예: 광주·전남 통합 → '광주광역시·전라남도'
    """
    sido_to_cands: dict = {}
    sido_wide = df[df["선거종류"].isin(SIDO_WIDE_RACES)]
    for (회차, 선거종류, 시도), grp in sido_wide.groupby(["선거_회차", "선거종류", "시도"]):
        cands = frozenset(grp["식별자"].dropna().unique())
        sido_to_cands[(int(회차), 선거종류, 시도)] = cands

    seen: dict = {}
    for (회차, 선거종류, 시도), cands in sido_to_cands.items():
        group_id = (회차, 선거종류, cands)
        seen.setdefault(group_id, []).append(시도)

    group_map: dict = {}
    for (회차, 선거종류, _), sidos in seen.items():
        key = "·".join(sorted(sidos))
        for 시도 in sidos:
            group_map[(회차, 선거종류, 시도)] = key
    return group_map


def _restore_middot(eupmd):
    return re.sub(r"(?<=[가-힣0-9])\?(?=[가-힣])", "·", eupmd)


def _clean_eupmd_local(eupmd, sido, gu, race_type):
    cleaned = re.sub(r"^.*?선거구\s+", "", eupmd)
    if cleaned and cleaned != eupmd:
        return _restore_middot(cleaned)
    space_pos = eupmd.find(" ")
    if space_pos > 0:
        head = eupmd[:space_pos].lstrip("_")
        after = eupmd[space_pos + 1:]
        is_prefix = (
            head.startswith(sido)
            or (gu and head.startswith(gu))
            or (race_type and head == race_type)
        )
        if is_prefix and after:
            return _restore_middot(after)
    return _restore_middot(eupmd)


def _emd_from_precinct(precinct):
    """투표구명 "청운동제1투"에서 동명 "청운동" 추출. 실패하면 투표구 그대로 반환.

    처리 형태:
      청운동제1투 / 종로1.2.3.4가동제1투 → 동명 + 제N투
      중앙동투                          → 제N 없이 투로 끝남
      연기군 장기면제1투                 → 구시군 접두(공백) + 동명 + 제N투
    """
    # 마지막 토큰이 '투'로 끝나는 투표구면 구시군 접두(공백)를 떼고 본다
    if " " in precinct and precinct.split()[-1].endswith("투"):
        precinct = precinct.split()[-1]
    matched = re.match(r"^([가-힣0-9?·.]+?)(?:제\s*\d+|제\s*[가-힣]|\d+)\s*투$", precinct)
    if matched:
        return matched.group(1).strip()
    # 제N 없이 동명 바로 뒤에 '투'만 붙은 경우 (예: 중앙동투)
    matched = re.match(r"^([가-힣0-9?·.]+동)투$", precinct)
    if matched:
        return matched.group(1).strip()
    return precinct


def _normalize_emd_local(eupmd):
    """지방선거 그룹핑 키용 읍면동 정규화.

    3회 원본의 투표구 단위(`동면제1투`)·동명 중복(`가평읍 가평읍`)을
    실제 읍면동으로 합산해 같은 동이 한 키로 묶이게 한다.
    4~9회의 정상 읍면동명은 변형하지 않는다.
    """
    name = str(eupmd)
    # `동면제1투` → `동면`
    name = _emd_from_precinct(name)
    # `가평읍 가평읍` → `가평읍` (같은 단어 두 번 반복인 경우만)
    parts = name.split()
    if len(parts) == 2 and parts[0] == parts[1]:
        name = parts[0]
    return name


def _enrich_location(location_entry, vote_by_id, turnout):
    """location에 그 투표소의 1위 후보·투표수·선거인수를 채운다.

    vote_by_id: {식별자: 합산득표} — 1위는 최다 득표(동점 시 첫 등장 유지).
    turnout: {"투표수": int, "선거인수": int} 또는 None.
    """
    if vote_by_id:
        top = max(vote_by_id.items(), key=lambda kv: kv[1])
        location_entry["1위"] = top[0]
        location_entry["1위득표"] = top[1]
    if turnout:
        location_entry["투표수"] = turnout["투표수"]
        if "선거인수" in turnout:
            location_entry["선거인수"] = turnout["선거인수"]


def _emd_turnout_map(df, group_keys, dedup_col):
    """정규화 읍면동별 총 투표수·선거인수 매핑.

    group_keys: 읍면동을 식별하는 컬럼 목록 (예: [회차, 선거종류, 시도, 구시군, _emd_norm, level]).
    dedup_col: 같은 투표구를 식별하는 원본 컬럼(예: 읍면동/투표구). 후보 행마다
      투표수가 중복되므로, 투표구별로 한 행만 남긴 뒤 group_keys로 합산한다.
    반환: {tuple(group_keys 값): {"투표수": int, "선거인수": int}}
    """
    cols = list(group_keys) + [dedup_col]
    has_voters = "선거인수" in df.columns
    agg_cols = ["투표수"] + (["선거인수"] if has_voters else [])
    sub = df[cols + agg_cols].copy()
    for col in agg_cols:
        sub[col] = pd.to_numeric(sub[col], errors="coerce")
    # 투표구 단위로 한 행만 (후보 행 중복 제거) → group_keys로 합산
    per_precinct = sub.drop_duplicates(subset=cols)
    grouped = per_precinct.groupby(list(group_keys))[agg_cols].sum()
    result: dict = {}
    for key, row in grouped.iterrows():
        key_tuple = key if isinstance(key, tuple) else (key,)
        entry = {"투표수": int(row["투표수"])}
        if has_voters:
            entry["선거인수"] = int(row["선거인수"])
        result[key_tuple] = entry
    return result


def _analyze_local():
    print("\n[지방선거] 읽는 중...")
    df = pd.read_csv("data_processed/지방선거.csv", low_memory=False)
    df = df.dropna(subset=["시도", "구시군", "읍면동"])
    df["득표수"] = pd.to_numeric(df["득표수"], errors="coerce")
    df = df.dropna(subset=["득표수"])
    df = df[~df["level"].isin(JUNK_LEVELS)]
    df["식별자"] = df["후보자"].fillna(df["정당"])
    df = df.dropna(subset=["식별자"])
    print(f"  {len(df):,}행")

    party_map = _build_party_map(df)
    sido_group_map = _build_sido_groups(df)

    # 읍면동 정규화: 투표구(`동면제1투`)·동명중복(`가평읍 가평읍`)을 실제 읍면동으로
    # 통일한다. 그래야 같은 동의 투표구들이 한 투표소로 합산되어 가짜 "투표소 간
    # 반복"이 생기지 않는다 (3회 지선이 이 문제로 후보쌍이 폭증했었다).
    df = df.copy()
    df["_emd_norm"] = [
        _normalize_emd_local(_clean_eupmd_local(eupmd, sido, gu, race))
        for eupmd, sido, gu, race in zip(
            df["읍면동"], df["시도"], df["구시군"], df["선거종류"]
        )
    ]

    # 정규화 읍면동별 총 투표수: 원본 읍면동(=투표구)별 투표수를 한 번씩만 더한다.
    # (같은 투표구의 여러 후보 행은 투표수가 동일하므로 중복을 제거해 합산.)
    turnout_map = _emd_turnout_map(
        df, ["선거_회차", "선거종류", "시도", "구시군", "_emd_norm", "level"], "읍면동"
    )

    precinct_cols = ["선거_회차", "선거종류", "시도", "구시군", "_emd_norm", "level"]
    sorted_df = df.sort_values(precinct_cols, kind="stable")
    key_columns = [sorted_df[col].tolist() for col in precinct_cols]
    identifier_list = sorted_df["식별자"].tolist()
    votes_list = sorted_df["득표수"].tolist()
    key_tuples = list(zip(*key_columns))
    num_rows = len(key_tuples)

    print("  버킷 집계 중...")
    buckets: defaultdict = defaultdict(list)
    group_start = 0
    for row_index in range(1, num_rows + 1):
        if row_index < num_rows and key_tuples[row_index] == key_tuples[group_start]:
            continue
        회차, 선거종류, 시도, 구시군, 읍면동, level = key_tuples[group_start]
        # 같은 정규화 읍면동 안에서 정당(식별자)별 득표를 합산 — 투표구가
        # 여럿이면 한 투표소로 합쳐진다. 첫 등장 순서(기호순)를 유지한다.
        vote_by_id: dict = {}
        for i in range(group_start, row_index):
            identifier = identifier_list[i]
            if identifier != identifier:  # NaN 방어
                continue
            vote_by_id[identifier] = vote_by_id.get(identifier, 0) + int(votes_list[i])
        cands = list(vote_by_id.items())
        location_entry = {"구시군": 구시군, "읍면동": 읍면동}
        _enrich_location(location_entry, vote_by_id,
                         turnout_map.get(key_tuples[group_start]))
        if 선거종류 in SIDO_WIDE_RACES:
            sido_key = sido_group_map.get((int(회차), 선거종류, 시도), 시도)
            prefix = (int(회차), 선거종류, sido_key, level)
        else:
            prefix = (int(회차), 선거종류, 시도, 구시군, level)
        _rank_pair_buckets(cands, prefix, location_entry, buckets)
        group_start = row_index

    twins = []
    for bucket_key, locations in buckets.items():
        if len(locations) < 2:
            continue
        candidates = bucket_key[-2:]
        # 두 후보 중 하나라도 임계값 미만이면 저득표 노이즈이므로 제외
        if any(score < MIN_VOTE_THRESHOLD for _, score in candidates):
            continue
        rank = bucket_key[-3]
        prefix_part = bucket_key[:-3]
        선거종류 = prefix_part[1]
        level = prefix_part[-1]
        if len(prefix_part) == 4:  # 시도 단위: (회차, 종류, sido_key, level)
            회차, _, sido_key, _ = prefix_part
            gu = None
        else:  # 구시군 단위: (회차, 종류, 시도, 구시군, level)
            회차, _, sido_key, gu, _ = prefix_part
        votes_map = {cand: score for cand, score in candidates}
        total = sum(score for _, score in candidates)
        twins.append({
            "category": f"지방선거_{선거종류}_{level}",
            "group": {"선거_회차": 회차, "시도": sido_key, "구시군": gu},
            "locations": locations,
            "votes": votes_map,
            "parties": _parties_for(candidates, party_map),
            "total_votes": total,
            "count": len(locations),
            "rank_pair": [rank, rank + 1],
        })
    twins.sort(key=lambda twin: (-twin["count"], -twin["total_votes"]))
    print(f"  쌍둥이 그룹 {len(twins):,}개")
    return twins


def _analyze_assembly():
    print("\n[총선] 읽는 중...")
    df = pd.read_csv("data_processed/국회의원선거.csv", low_memory=False)
    df = df.dropna(subset=["시도"])
    df["득표수"] = pd.to_numeric(df["득표수"], errors="coerce")
    df = df.dropna(subset=["득표수"])
    df = df[~df["level"].isin(JUNK_LEVELS)]
    df["식별자"] = df["후보자"].fillna(df["정당"])
    df = df.dropna(subset=["식별자"])
    party_map = _build_party_map(df)
    df["구시군"] = df["구시군"].fillna("")
    df["선거구명"] = df["선거구명"].fillna("")
    # 18대·19대는 읍면동이 없고 투표구에 "청운동제1투" 형태로 들어 있음
    emd_null = df["읍면동"].isna()
    df.loc[emd_null, "읍면동"] = df.loc[emd_null, "투표구"].apply(
        lambda v: _emd_from_precinct(str(v)) if pd.notna(v) else ""
    )
    df["읍면동"] = df["읍면동"].fillna("")
    print(f"  {len(df):,}행")

    precinct_cols = ["선거_회차", "선거구분", "선거구명", "시도", "구시군", "읍면동", "level"]
    dedup_col = "투표구" if "투표구" in df.columns else "읍면동"
    turnout_map = _emd_turnout_map(df, precinct_cols, dedup_col)
    sorted_df = df.sort_values(precinct_cols, kind="stable")
    key_columns = [sorted_df[col].tolist() for col in precinct_cols]
    identifier_list = sorted_df["식별자"].tolist()
    votes_list = sorted_df["득표수"].tolist()
    key_tuples = list(zip(*key_columns))
    num_rows = len(key_tuples)

    print("  버킷 집계 중...")
    buckets: defaultdict = defaultdict(list)
    group_start = 0
    for row_index in range(1, num_rows + 1):
        if row_index < num_rows and key_tuples[row_index] == key_tuples[group_start]:
            continue
        회차, 선거구분, 선거구명, 시도, 구시군, 읍면동, level = key_tuples[group_start]
        # 같은 읍면동 안 투표구가 여러 행으로 들어오므로 후보(식별자)별
        # 득표를 합산해 한 투표소로 통일한다. 첫 등장 순서 유지.
        vote_by_id: dict = {}
        for i in range(group_start, row_index):
            identifier = identifier_list[i]
            if identifier != identifier:  # NaN 방어
                continue
            vote_by_id[identifier] = vote_by_id.get(identifier, 0) + int(votes_list[i])
        cands = list(vote_by_id.items())
        location_entry = {"구시군": 구시군, "읍면동": _restore_middot(읍면동)}
        _enrich_location(location_entry, vote_by_id,
                         turnout_map.get(key_tuples[group_start]))
        if 선거구분 == "지역구":
            prefix = (회차, 선거구분, 선거구명, level)
        else:
            prefix = (회차, 선거구분, level)
        _rank_pair_buckets(cands, prefix, location_entry, buckets)
        group_start = row_index

    twins = []
    for bucket_key, locations in buckets.items():
        if len(locations) < 2:
            continue
        candidates = bucket_key[-2:]
        # 두 후보 중 하나라도 임계값 미만이면 저득표 노이즈이므로 제외
        if any(score < MIN_VOTE_THRESHOLD for _, score in candidates):
            continue
        rank = bucket_key[-3]
        prefix_part = bucket_key[:-3]
        선거구분 = prefix_part[1]
        level = prefix_part[-1]
        if 선거구분 == "지역구":
            회차, _, 선거구명, _ = prefix_part
            group_info = {"선거_회차": 회차, "선거구명": 선거구명}
        else:
            회차, _, _ = prefix_part
            group_info = {"선거_회차": 회차}
        votes_map = {cand: score for cand, score in candidates}
        total = sum(score for _, score in candidates)
        twins.append({
            "category": f"총선_{선거구분}_{level}",
            "group": group_info,
            "locations": locations,
            "votes": votes_map,
            "parties": _parties_for(candidates, party_map),
            "total_votes": total,
            "count": len(locations),
            "rank_pair": [rank, rank + 1],
        })
    twins.sort(key=lambda twin: (-twin["count"], -twin["total_votes"]))
    print(f"  쌍둥이 그룹 {len(twins):,}개")
    return twins


def _analyze_presidential():
    print("\n[대선] 읽는 중...")
    df = pd.read_csv("data_processed/대통령선거.csv", low_memory=False)
    df = df.dropna(subset=["시도", "읍면동"])
    df["득표수"] = pd.to_numeric(df["득표수"], errors="coerce")
    df = df.dropna(subset=["득표수"])
    df = df[~df["level"].isin(JUNK_LEVELS)]
    df["식별자"] = df["후보자"].fillna(df["정당"])
    df = df.dropna(subset=["식별자"])
    party_map = _build_party_map(df)
    df["구시군"] = df["구시군"].fillna("")
    print(f"  {len(df):,}행")

    precinct_cols = ["선거_회차", "시도", "구시군", "읍면동", "level"]
    dedup_col = "투표구" if "투표구" in df.columns else "읍면동"
    turnout_map = _emd_turnout_map(df, precinct_cols, dedup_col)
    sorted_df = df.sort_values(precinct_cols, kind="stable")
    key_columns = [sorted_df[col].tolist() for col in precinct_cols]
    identifier_list = sorted_df["식별자"].tolist()
    votes_list = sorted_df["득표수"].tolist()
    key_tuples = list(zip(*key_columns))
    num_rows = len(key_tuples)

    print("  버킷 집계 중...")
    buckets: defaultdict = defaultdict(list)
    group_start = 0
    for row_index in range(1, num_rows + 1):
        if row_index < num_rows and key_tuples[row_index] == key_tuples[group_start]:
            continue
        회차, 시도, 구시군, 읍면동, level = key_tuples[group_start]
        # 같은 읍면동 안 투표구(`북부동제1투`…)가 여러 행으로 들어오므로
        # 후보(식별자)별 득표를 합산해 한 투표소로 통일한다. 첫 등장 순서 유지.
        vote_by_id: dict = {}
        for i in range(group_start, row_index):
            identifier = identifier_list[i]
            if identifier != identifier:  # NaN 방어
                continue
            vote_by_id[identifier] = vote_by_id.get(identifier, 0) + int(votes_list[i])
        cands = list(vote_by_id.items())
        location_entry = {"시도": 시도, "구시군": 구시군, "읍면동": _restore_middot(읍면동)}
        _enrich_location(location_entry, vote_by_id,
                         turnout_map.get(key_tuples[group_start]))
        prefix = (int(회차), level)
        _rank_pair_buckets(cands, prefix, location_entry, buckets)
        group_start = row_index

    twins = []
    for bucket_key, locations in buckets.items():
        if len(locations) < 2:
            continue
        candidates = bucket_key[-2:]
        # 두 후보 중 하나라도 임계값 미만이면 저득표 노이즈이므로 제외
        if any(score < MIN_VOTE_THRESHOLD for _, score in candidates):
            continue
        rank = bucket_key[-3]
        회차, level = bucket_key[:2]
        votes_map = {cand: score for cand, score in candidates}
        total = sum(score for _, score in candidates)
        twins.append({
            "category": f"대선_{level}",
            "group": {"선거_회차": 회차},
            "locations": locations,
            "votes": votes_map,
            "parties": _parties_for(candidates, party_map),
            "total_votes": total,
            "count": len(locations),
            "rank_pair": [rank, rank + 1],
        })
    twins.sort(key=lambda twin: (-twin["count"], -twin["total_votes"]))
    print(f"  쌍둥이 그룹 {len(twins):,}개")
    return twins


def _round_meta(twins):
    """한 회차의 (필터링된) 쌍둥이 그룹 리스트 → hero용 집계.

    web/src/twinStats.ts computeRoundStats 와 동일 규칙:
      묶음 키 = category | json(group) | rank_pair join '-' | 정렬한 후보쌍 join '='
      pairCount       = 서로 다른 후보쌍 수
      totalLocations  = 모든 사례의 일치 투표소(count) 합
      groupCount      = 쌍둥이 그룹 수
      topPair         = 합산 투표소 최다 후보쌍 (동률이면 먼저 만난 쌍)
    """
    by_key = {}
    key_order = []
    total_locations = 0

    for group in twins:
        names = [cand for cand, _ in sorted(
            group["votes"].items(), key=lambda item: -item[1])]
        if len(names) < 2:
            continue
        first, second = names[0], names[1]

        total_locations += group["count"]
        sorted_pair = sorted([first, second])
        key = "|".join([
            str(group["category"]),
            json.dumps(group["group"], ensure_ascii=False, sort_keys=True),
            "-".join(str(rank) for rank in group["rank_pair"]),
            "=".join(sorted_pair),
        ])
        entry = by_key.get(key)
        if entry:
            entry["locations"] += group["count"]
        else:
            parties = group.get("parties") or {}
            by_key[key] = {
                "names": [first, second],
                "parties": [parties.get(first), parties.get(second)],
                "locations": group["count"],
            }
            key_order.append(key)

    top_pair = None
    for key in key_order:
        entry = by_key[key]
        if top_pair is None or entry["locations"] > top_pair["locations"]:
            top_pair = entry

    return {
        "pairCount": len(by_key),
        "totalLocations": total_locations,
        "groupCount": len(twins),
        "topPair": top_pair,
    }


def _write_election(election_key, round_field, twins):
    by_round = defaultdict(list)
    for twin in twins:
        by_round[twin["group"][round_field]].append(twin)

    rounds = sorted(by_round.keys(), key=lambda r: str(r))
    round_labels = {}
    for r in rounds:
        if election_key == "지방선거":
            round_labels[str(r)] = f"{r}회"
        elif election_key == "총선":
            round_labels[str(r)] = str(r)
        else:
            round_labels[str(r)] = f"제{r}대"

    counts = {}
    rounds_meta = {}
    for r in rounds:
        filtered = [t for t in by_round[r] if t["count"] >= MIN_TWIN_COUNT]
        counts[str(r)] = len(filtered)
        rounds_meta[str(r)] = _round_meta(filtered)
        safe_r = str(r).replace(" ", "_")
        path = f"{OUT_DIR}/twin_votes_{election_key}_{safe_r}.json"
        with open(path, "w", encoding="utf-8") as out_file:
            json.dump({"twins": filtered}, out_file, ensure_ascii=False)
        total = len(by_round[r])
        print(f"  → {path} ({len(filtered):,}개 / 전체 {total:,}개)")

    return {
        "rounds": [str(r) for r in rounds],
        "counts": counts,
        "roundLabels": round_labels,
        "rounds_meta": rounds_meta,
    }


def main():
    local_twins = _analyze_local()
    assembly_twins = _analyze_assembly()
    pres_twins = _analyze_presidential()

    print("\n파일 출력 중...")
    elections = {}
    elections["지방선거"] = _write_election("지방선거", "선거_회차", local_twins)
    elections["총선"] = _write_election("총선", "선거_회차", assembly_twins)
    elections["대선"] = _write_election("대선", "선거_회차", pres_twins)

    # 선거종류별·전체 누적 합계 (회차별 rounds_meta 합산)
    totals = {}
    all_total = {"pairCount": 0, "totalLocations": 0, "groupCount": 0}
    for election_key, election in elections.items():
        agg = {"pairCount": 0, "totalLocations": 0, "groupCount": 0}
        for meta in election["rounds_meta"].values():
            for field in agg:
                agg[field] += meta[field]
        totals[election_key] = agg
        for field in all_total:
            all_total[field] += agg[field]
    totals["all"] = all_total

    index_path = f"{OUT_DIR}/twin_votes_index.json"
    with open(index_path, "w", encoding="utf-8") as out_file:
        json.dump({"elections": elections, "totals": totals}, out_file, ensure_ascii=False)
    print(f"  → {index_path}")
    print("\n완료")


if __name__ == "__main__":
    main()
