from etl.local.build import ELECTION_DATES


def test_election_dates_cover_3_to_9():
    assert ELECTION_DATES[3] == "2002-06-13"
    assert ELECTION_DATES[8] == "2022-06-01"
    assert ELECTION_DATES[9] == "2026-06-03"
    assert set(ELECTION_DATES) == {3, 4, 5, 6, 7, 8, 9}
