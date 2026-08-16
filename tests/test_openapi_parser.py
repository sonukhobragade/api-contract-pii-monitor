"""
Tests for OpenAPI parsing rules that affect what reaches PII detection.

A parameter the parser drops is a parameter the detector never sees, so a
parsing gap and a detection gap have exactly the same consequence: a field
holding personal data, reported clean.
"""

import pytest

from core.openapi_parser import PostgreSQLOpenAPIParser

merge = PostgreSQLOpenAPIParser._merge_path_parameters


SHARED = [
    {"name": "email", "in": "query"},
    {"name": "trace_id", "in": "header"},
]


class TestPathLevelParameters:
    """OpenAPI allows `parameters` on the Path Item; every operation under that
    path inherits them. They were skipped, so a path-level `email` or
    `national_id` never reached detection."""

    def test_inherited_parameters_are_added(self):
        details = {"parameters": [{"name": "limit", "in": "query"}]}
        names = [p["name"] for p in merge(details, SHARED)["parameters"]]
        assert names == ["email", "trace_id", "limit"]

    def test_an_operation_with_no_parameters_still_inherits(self):
        names = [p["name"] for p in merge({}, SHARED)["parameters"]]
        assert names == ["email", "trace_id"]

    def test_the_operation_wins_when_both_define_the_same_parameter(self):
        """The specification says an operation-level parameter overrides an
        inherited one with the same name and location."""
        details = {"parameters": [{"name": "email", "in": "query", "required": True}]}
        merged = merge(details, SHARED)["parameters"]
        emails = [p for p in merged if p["name"] == "email"]
        assert len(emails) == 1
        assert emails[0]["required"] is True

    def test_same_name_different_location_is_not_an_override(self):
        # `id` in the path and `id` in a header are two parameters.
        details = {"parameters": [{"name": "email", "in": "header"}]}
        merged = merge(details, SHARED)["parameters"]
        assert sum(1 for p in merged if p["name"] == "email") == 2

    def test_the_operation_dict_is_not_mutated(self):
        """Mutating it would leak one operation's parameters into its siblings
        under the same path, since they share the parent dict."""
        details = {"parameters": [{"name": "limit", "in": "query"}]}
        merge(details, SHARED)
        assert [p["name"] for p in details["parameters"]] == ["limit"]

    def test_nothing_to_inherit_returns_the_original(self):
        details = {"parameters": [{"name": "limit", "in": "query"}]}
        assert merge(details, []) is details

    @pytest.mark.parametrize("bad", [None, "parameters", 42, {"name": "x"}])
    def test_malformed_operation_parameters_do_not_crash_the_parse(self, bad):
        # One malformed operation in a large spec must not abort the run; the
        # rest of the spec still needs analysing.
        merged = merge({"parameters": bad}, SHARED)
        assert [p["name"] for p in merged["parameters"]] == ["email", "trace_id"]

    def test_non_dict_details_are_returned_untouched(self):
        assert merge(None, SHARED) is None
