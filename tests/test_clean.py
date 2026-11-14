"""
Unit tests for the data-cleaning helpers.

These are pure functions, so they need no database or network - they are the
fastest safety net against a parser regression.

    .venv\\Scripts\\python -m pytest
"""

from datetime import date

from scraper import clean


class TestSplitName:
    def test_three_parts(self):
        assert clean.split_name("Abigail Elaine Adams") == ("Abigail", "Elaine", "Adams")

    def test_two_parts(self):
        assert clean.split_name("Amy Abbott") == ("Amy", None, "Abbott")

    def test_single_name(self):
        assert clean.split_name("Cher") == ("Cher", None, None)

    def test_suffix_is_dropped_from_last_name(self):
        assert clean.split_name("John A Smith Jr") == ("John", "A", "Smith")

    def test_empty(self):
        assert clean.split_name("") == (None, None, None)


class TestDisciplines:
    def test_multiple_codes_without_arrt(self):
        assert clean.parse_disciplines("R.T.(R)(CT)(ARRT)") == "R,CT"

    def test_single(self):
        assert clean.parse_disciplines("R.T.(MR)(ARRT)") == "MR"

    def test_none_input(self):
        assert clean.parse_disciplines(None) is None

    def test_no_codes(self):
        assert clean.parse_disciplines("R.T.(ARRT)") is None


class TestDates:
    def test_valid_thru_last_day_of_month(self):
        assert clean.parse_valid_thru("11/2026") == date(2026, 11, 30)

    def test_valid_thru_leap_february(self):
        assert clean.parse_valid_thru("2/2028") == date(2028, 2, 29)

    def test_valid_thru_bad_month_is_none(self):
        assert clean.parse_valid_thru("13/2026") is None

    def test_valid_thru_none(self):
        assert clean.parse_valid_thru(None) is None

    def test_us_date(self):
        assert clean.parse_us_date("1/5/2025") == date(2025, 1, 5)

    def test_us_date_invalid(self):
        assert clean.parse_us_date("not a date") is None

    def test_date_range(self):
        assert clean.parse_date_range("11/1/2025 to 10/31/2027") == (date(2025, 11, 1), date(2027, 10, 31))

    def test_date_range_incomplete(self):
        assert clean.parse_date_range("11/1/2025") == (None, None)


class TestCqr:
    def test_single_period(self):
        out = clean.parse_cqr("Radiography 11/1/2032 - 10/31/2035")
        assert out == [{"discipline": "Radiography", "start": "2032-11-01", "end": "2035-10-31"}]

    def test_two_periods(self):
        out = clean.parse_cqr("Radiography 11/1/2032 - 10/31/2035 Computed Tomography 1/1/2030 - 12/31/2032")
        assert len(out) == 2
        assert out[1]["discipline"] == "Computed Tomography"

    def test_none(self):
        assert clean.parse_cqr(None) is None


class TestDescription:
    def test_codes_and_names(self):
        out = clean.parse_description(["(R) Radiography", "(CT) Computed Tomography"])
        assert out == [{"code": "R", "name": "Radiography"}, {"code": "CT", "name": "Computed Tomography"}]

    def test_empty(self):
        assert clean.parse_description([]) is None
