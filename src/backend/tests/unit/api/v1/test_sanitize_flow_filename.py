"""A7 characterization tests for _sanitize_flow_filename."""

import pytest
from langflow.api.v1.flows_helpers import _sanitize_flow_filename


def test_sanitize_flow_filename_when_name_is_plain_returns_it_unchanged():
    assert _sanitize_flow_filename("My Flow") == "My Flow"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("a/b", "a_b"),
        ("a\\b", "a_b"),
        ("../etc/passwd", "__etc_passwd"),
        ("bad\x00name", "badname"),
    ],
)
def test_sanitize_flow_filename_when_name_has_path_characters_replaces_them(raw, expected):
    assert _sanitize_flow_filename(raw) == expected


@pytest.mark.parametrize(("raw", "expected"), [("CON", "_CON"), ("nul.json", "_nul.json"), ("COM1", "_COM1")])
def test_sanitize_flow_filename_when_windows_device_name_prefixes_underscore(raw, expected):
    assert _sanitize_flow_filename(raw) == expected


def test_sanitize_flow_filename_when_name_is_only_whitespace_returns_fallback():
    assert _sanitize_flow_filename("   ", fallback_id="abc-123") == "abc-123"


def test_sanitize_flow_filename_when_name_is_none_returns_string_none():
    # Current behavior: str(None) -> "None"; it does not use the fallback.
    assert _sanitize_flow_filename(None, fallback_id="abc-123") == "None"  # type: ignore[arg-type]


def test_sanitize_flow_filename_when_different_names_collide_returns_same_filename():
    # Characterization: sanitizing is many-to-one. Callers must not assume uniqueness.
    assert _sanitize_flow_filename("Q1/Q2") == _sanitize_flow_filename("Q1_Q2") == "Q1_Q2"
