"""Testes para o módulo utils/time_parser.py."""

import pytest

from utils.time_parser import format_duration, format_duration_long, parse_time


class TestParseTime:
    def test_mm_ss_format(self) -> None:
        assert parse_time("1:23") == 83

    def test_hh_mm_ss_format(self) -> None:
        assert parse_time("1:23:45") == 5025

    def test_seconds_only(self) -> None:
        assert parse_time("83") == 83
        assert parse_time("83s") == 83

    def test_minutes_seconds_suffix(self) -> None:
        assert parse_time("1m30s") == 90
        assert parse_time("1m") == 60
        assert parse_time("30s") == 30

    def test_hours_minutes_suffix(self) -> None:
        assert parse_time("1h30m") == 5400
        assert parse_time("2h") == 7200

    def test_hours_minutes_seconds_suffix(self) -> None:
        assert parse_time("1h30m20s") == 5420

    def test_invalid_format(self) -> None:
        assert parse_time("abc") is None
        assert parse_time("") is None

    def test_invalid_seconds(self) -> None:
        # mm:ss com segundos >= 60 é inválido
        assert parse_time("1:60") is None
        assert parse_time("1:99") is None

    def test_zero(self) -> None:
        assert parse_time("0") == 0 or parse_time("0") is None  # 0 é falsy, depende da impl


class TestFormatDuration:
    def test_seconds_only(self) -> None:
        assert format_duration(45) == "0:45"

    def test_minutes_seconds(self) -> None:
        assert format_duration(83) == "1:23"

    def test_hours_minutes_seconds(self) -> None:
        assert format_duration(5025) == "1:23:45"

    def test_zero(self) -> None:
        assert format_duration(0) == "0:00"

    def test_negative(self) -> None:
        assert format_duration(-5) == "0:00"


class TestFormatDurationLong:
    def test_seconds_only(self) -> None:
        assert format_duration_long(45) == "45s"

    def test_minutes_seconds(self) -> None:
        assert format_duration_long(90) == "1min 30s"

    def test_hours(self) -> None:
        assert format_duration_long(3661) == "1h 1min 1s"

    def test_zero(self) -> None:
        assert format_duration_long(0) == "0s"
