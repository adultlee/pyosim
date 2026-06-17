"""data_processed/*.csv 를 선거×회차 단위 gzip CSV + 매니페스트로 분할한다.

analyze_twin_votes.py 다음 단계. 산출물은 web/public 에 떨어지며 배포에 포함된다.
"""
import gzip
import json
import os

import pandas as pd

OUT_DIR = "web/public"
MANIFEST_PATH = f"{OUT_DIR}/votes_csv_index.json"

ELECTION_NAME_MAP = {
    "국회의원선거": "총선",
    "대통령선거": "대선",
    "지방선거": "지방선거",
}

SOURCE_FILES = {
    "국회의원선거": "data_processed/국회의원선거.csv",
    "대통령선거": "data_processed/대통령선거.csv",
    "지방선거": "data_processed/지방선거.csv",
}

SIZE_LIMIT_BYTES = 100 * 1024 * 1024  # GitHub 단일 파일 한계


def round_key(round_value):
    """회차 컬럼값을 파일명용 키로. 공백은 _ 로 치환 (App.tsx fetch 규칙과 동일)."""
    return str(round_value).replace(" ", "_")


def write_round_gzip(df_round, out_path):
    """한 회차 DataFrame 을 utf-8-sig CSV 로 직렬화해 gzip 으로 out_path 에 쓴다.
    압축 후 바이트 수를 반환."""
    csv_bytes = df_round.to_csv(index=False).encode("utf-8-sig")
    with gzip.open(out_path, "wb") as handle:
        handle.write(csv_bytes)
    return os.path.getsize(out_path)


def split_one(source_csv_name, source_path, out_dir):
    """한 소스 CSV 를 회차별 gz 로 굽고 매니페스트 조각을 반환."""
    election_label = ELECTION_NAME_MAP[source_csv_name]
    df = pd.read_csv(source_path, dtype=str)
    df["선거_회차"] = df["선거_회차"].astype(str)
    manifest = {}
    for round_value, df_round in df.groupby("선거_회차"):
        key = round_key(round_value)
        file_name = f"votes_{election_label}_{key}.csv.gz"
        out_path = os.path.join(out_dir, file_name)
        size = write_round_gzip(df_round, out_path)
        if size >= SIZE_LIMIT_BYTES:
            print(f"  ⚠️ {file_name}: {size / 1024 / 1024:.1f}MB (100MB 초과!)")
        manifest[key] = {"file": file_name, "rows": int(len(df_round)), "bytes": int(size)}
    return manifest


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    full_manifest = {}
    for source_csv_name, source_path in SOURCE_FILES.items():
        if not os.path.exists(source_path):
            print(f"건너뜀 (원본 없음): {source_path}")
            continue
        election_label = ELECTION_NAME_MAP[source_csv_name]
        print(f"분할: {source_path} → {election_label}")
        full_manifest[election_label] = split_one(source_csv_name, source_path, OUT_DIR)
        for key, meta in sorted(full_manifest[election_label].items()):
            print(f"  {key}: {meta['rows']:,}행 → {meta['bytes'] / 1024 / 1024:.1f}MB")
    with open(MANIFEST_PATH, "w", encoding="utf-8") as handle:
        json.dump(full_manifest, handle, ensure_ascii=False, indent=1)
    print(f"매니페스트: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
