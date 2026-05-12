"""Shared validation helpers for FloodLens Airflow utilities."""

from __future__ import annotations


def validate_state_fips(state_fips: str) -> None:
    """Raises ValueError unless state_fips is a two-digit FIPS code."""
    if len(state_fips) != 2 or not state_fips.isdigit():
        raise ValueError(f"state_fips must be a two-digit FIPS code: {state_fips}")
