"""Tests for dags/utils/validation.py::validate_state_fips."""

import pytest

from utils.validation import validate_state_fips


def test_accepts_two_digit_fips():
    # Should not raise.
    validate_state_fips("12")
    validate_state_fips("06")


@pytest.mark.parametrize(
    "bad",
    ["1", "123", "ab", "", " 2", "1a", "12 "],
)
def test_rejects_anything_that_is_not_two_digits(bad):
    with pytest.raises(ValueError):
        validate_state_fips(bad)
