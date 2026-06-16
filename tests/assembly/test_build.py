from etl.assembly.build import ELECTION_DATES, PARSERS


def test_election_dates_cover_16_to_22():
    assert ELECTION_DATES["제16대"] == "2000-04-13"
    assert ELECTION_DATES["제22대"] == "2024-04-10"
    assert set(ELECTION_DATES) == {"제16대", "제17대", "제18대", "제19대", "제20대", "제21대", "제22대"}


def test_parsers_count():
    assert len(PARSERS) == 7
