"""split_votes_csv 의 회차별 gzip 굽기 검증."""
import gzip
import io
import os

import pandas as pd

from split_votes_csv import ELECTION_NAME_MAP, round_key, write_round_gzip, split_one


def test_election_name_map():
    assert ELECTION_NAME_MAP["국회의원선거"] == "총선"
    assert ELECTION_NAME_MAP["대통령선거"] == "대선"
    assert ELECTION_NAME_MAP["지방선거"] == "지방선거"


def test_round_key_replaces_space():
    assert round_key("제22대") == "제22대"
    assert round_key("9") == "9"
    assert round_key("관내 사전") == "관내_사전"


def test_write_round_gzip_roundtrip(tmp_path):
    df = pd.DataFrame({"시도": ["서울", "부산"], "득표수": ["10", "20"]})
    out_path = tmp_path / "votes_대선_14.csv.gz"
    size = write_round_gzip(df, str(out_path))
    assert size > 0
    assert out_path.stat().st_size == size
    with gzip.open(out_path, "rt", encoding="utf-8-sig") as handle:
        restored = pd.read_csv(io.StringIO(handle.read()), dtype=str)
    assert list(restored.columns) == ["시도", "득표수"]
    assert len(restored) == 2
    assert restored.iloc[0]["시도"] == "서울"


def test_write_round_gzip_has_bom(tmp_path):
    df = pd.DataFrame({"시도": ["서울"]})
    out_path = tmp_path / "x.csv.gz"
    write_round_gzip(df, str(out_path))
    with gzip.open(out_path, "rb") as handle:
        raw = handle.read()
    assert raw.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM


def test_split_one_groups_by_round(tmp_path):
    source = tmp_path / "대통령선거.csv"
    pd.DataFrame({
        "선거_회차": ["14", "14", "15"],
        "시도": ["서울", "부산", "서울"],
        "득표수": ["10", "20", "30"],
    }).to_csv(source, index=False)

    manifest = split_one("대통령선거", str(source), str(tmp_path))

    assert set(manifest.keys()) == {"14", "15"}
    assert manifest["14"]["file"] == "votes_대선_14.csv.gz"
    assert manifest["14"]["rows"] == 2
    assert manifest["15"]["rows"] == 1
    assert manifest["14"]["bytes"] > 0
    assert os.path.exists(os.path.join(str(tmp_path), "votes_대선_14.csv.gz"))


def test_split_one_assembly_round_label(tmp_path):
    source = tmp_path / "국회의원선거.csv"
    pd.DataFrame({
        "선거_회차": ["제22대", "제21대"],
        "시도": ["서울", "부산"],
    }).to_csv(source, index=False)

    manifest = split_one("국회의원선거", str(source), str(tmp_path))

    assert manifest["제22대"]["file"] == "votes_총선_제22대.csv.gz"
    assert manifest["제21대"]["rows"] == 1
