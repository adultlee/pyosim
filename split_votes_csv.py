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
