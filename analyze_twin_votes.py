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
    """투표구명 "청운동제1투"에서 동명 "청운동" 추출. 실패하면 투표구 그대로 반환."""
    matched = re.match(r"^([가-힣0-9?·]+?)(?:제\s*\d+|제\s*[가-힣]|\d+)\s*투", precinct)
    if matched:
        return matched.group(1).strip()
    return precinct


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

    sido_group_map = _build_sido_groups(df)

    precinct_cols = ["선거_회차", "선거종류", "시도", "구시군", "읍면동", "level"]
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
        # 기호순(CSV 행 순서) 유지 — 정렬 없이 그대로
        cands = [
            (identifier_list[i], int(votes_list[i]))
            for i in range(group_start, row_index)
            if identifier_list[i] == identifier_list[i]
        ]
        cleaned_eupmd = _clean_eupmd_local(읍면동, 시도, 구시군, 선거종류)
        location_entry = {"구시군": 구시군, "읍면동": cleaned_eupmd}
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
        cands = [
            (identifier_list[i], int(votes_list[i]))
            for i in range(group_start, row_index)
            if identifier_list[i] == identifier_list[i]
        ]
        location_entry = {"구시군": 구시군, "읍면동": _restore_middot(읍면동)}
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
    df["구시군"] = df["구시군"].fillna("")
    print(f"  {len(df):,}행")

    precinct_cols = ["선거_회차", "시도", "구시군", "읍면동", "level"]
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
        cands = [
            (identifier_list[i], int(votes_list[i]))
            for i in range(group_start, row_index)
            if identifier_list[i] == identifier_list[i]
        ]
        location_entry = {"시도": 시도, "구시군": 구시군, "읍면동": _restore_middot(읍면동)}
        prefix = (int(회차), level)
        _rank_pair_buckets(cands, prefix, location_entry, buckets)
        group_start = row_index

    twins = []
    for bucket_key, locations in buckets.items():
        if len(locations) < 2:
            continue
        candidates = bucket_key[-2:]
        rank = bucket_key[-3]
        회차, level = bucket_key[:2]
        votes_map = {cand: score for cand, score in candidates}
        total = sum(score for _, score in candidates)
        twins.append({
            "category": f"대선_{level}",
            "group": {"선거_회차": 회차},
            "locations": locations,
            "votes": votes_map,
            "total_votes": total,
            "count": len(locations),
            "rank_pair": [rank, rank + 1],
        })
    twins.sort(key=lambda twin: (-twin["count"], -twin["total_votes"]))
    print(f"  쌍둥이 그룹 {len(twins):,}개")
    return twins


def _write_election(election_key, round_field, twins):
    by_round = defaultdict(list)
    for twin in twins:
        by_round[twin["group"][round_field]].append(twin)

    rounds = sorted(by_round.keys(), key=lambda r: str(r))
    counts = {str(r): len(by_round[r]) for r in rounds}
    round_labels = {}
    for r in rounds:
        if election_key == "지방선거":
            round_labels[str(r)] = f"{r}회"
        elif election_key == "총선":
            round_labels[str(r)] = str(r)
        else:
            round_labels[str(r)] = f"제{r}대"

    for r in rounds:
        safe_r = str(r).replace(" ", "_")
        path = f"{OUT_DIR}/twin_votes_{election_key}_{safe_r}.json"
        with open(path, "w", encoding="utf-8") as out_file:
            json.dump({"twins": by_round[r]}, out_file, ensure_ascii=False)
        print(f"  → {path} ({len(by_round[r]):,}개)")

    return {"rounds": [str(r) for r in rounds], "counts": counts, "roundLabels": round_labels}


def main():
    local_twins = _analyze_local()
    assembly_twins = _analyze_assembly()
    pres_twins = _analyze_presidential()

    print("\n파일 출력 중...")
    elections = {}
    elections["지방선거"] = _write_election("지방선거", "선거_회차", local_twins)
    elections["총선"] = _write_election("총선", "선거_회차", assembly_twins)
    elections["대선"] = _write_election("대선", "선거_회차", pres_twins)

    index_path = f"{OUT_DIR}/twin_votes_index.json"
    with open(index_path, "w", encoding="utf-8") as out_file:
        json.dump({"elections": elections}, out_file, ensure_ascii=False)
    print(f"  → {index_path}")
    print("\n완료")


if __name__ == "__main__":
    main()
