from etl.pres.build import ELECTION_DATES, PARSERS


def test_election_dates_cover_14_to_21():
    assert ELECTION_DATES[14] == "1992-12-18"
    assert ELECTION_DATES[21] == "2025-06-03"
    assert set(ELECTION_DATES) == {14, 15, 16, 17, 18, 19, 20, 21}


def test_parsers_cover_all_rounds():
    rounds = [round_num for round_num, _ in PARSERS]
    assert rounds == [14, 15, 16, 17, 18, 19, 20, 21]
