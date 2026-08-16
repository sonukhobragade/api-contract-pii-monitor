"""
Tests for the standalone CLI.

This is the path most people will meet first, and it is the one that needs no
database, so it is the one that has to work from a clean checkout.

The exit code matters as much as the output: `--fail-on` is meant for CI, where
a wrong exit code either blocks every release or blocks none of them.
"""

import json

import pytest

import main


@pytest.fixture
def spec_file(tmp_path):
    """A small spec that exercises the paths the detector cares about."""
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/orders": {
                "parameters": [
                    {"name": "customer_email", "in": "query",
                     "schema": {"type": "string", "format": "email"}}
                ],
                "get": {
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/Customer"}}},
                        }
                    }
                },
            },
            "/health": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {"application/json": {"schema": {
                                "type": "object",
                                "properties": {"status": {"type": "string"}}}}},
                        }
                    }
                }
            },
        },
        "components": {"schemas": {"Customer": {
            "type": "object",
            "properties": {"national_id": {"type": "string"},
                           "order_ref": {"type": "string"}}}}},
    }
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec))
    return path


class TestExitCodes:
    def test_a_clean_run_reports_success(self, spec_file, capsys):
        assert main.main(["--spec", str(spec_file)]) == 0

    def test_fail_on_critical_blocks_when_critical_pii_is_present(self, spec_file):
        # national_id is CRITICAL, so a release gate set to critical must stop.
        assert main.main(["--spec", str(spec_file), "--fail-on", "critical"]) == 1

    def test_fail_on_never_is_the_default(self, spec_file):
        """Findings alone must not fail the command. Someone running this to
        look at their API should not get a non-zero exit for doing so."""
        assert main.main(["--spec", str(spec_file)]) == 0

    def test_a_missing_file_is_an_error_not_an_empty_report(self, tmp_path, capsys):
        # Returning 0 here would let a CI step that typo'd the path report
        # "no PII found" forever.
        assert main.main(["--spec", str(tmp_path / "nope.json")]) == 2

    def test_a_file_that_is_not_a_spec_is_rejected(self, tmp_path):
        path = tmp_path / "notaspec.json"
        path.write_text('{"hello": "world"}')
        assert main.main(["--spec", str(path)]) == 2

    def test_fail_on_high_also_trips_on_critical(self, spec_file):
        """Critical is above high. A gate set to high that ignored critical
        findings would be the exact inversion of what it promises."""
        assert main.main(["--spec", str(spec_file), "--fail-on", "high"]) == 1


class TestJsonOutput:
    def test_json_report_is_machine_readable(self, spec_file, tmp_path):
        out = tmp_path / "findings.json"
        main.main(["--spec", str(spec_file), "--format", "json", "--out", str(out)])
        payload = json.loads(out.read_text())

        assert payload["endpoints_analysed"] == 2
        fields = {m["field"] for f in payload["findings"] for m in f["matches"]}
        assert any("national_id" in f for f in fields)

    def test_the_clean_endpoint_produces_no_findings(self, spec_file, tmp_path):
        out = tmp_path / "findings.json"
        main.main(["--spec", str(spec_file), "--format", "json", "--out", str(out)])
        payload = json.loads(out.read_text())
        assert "/health" not in {f["path"] for f in payload["findings"]}


class TestAnalysis:
    def test_path_level_parameters_reach_the_report(self, spec_file, tmp_path):
        """Declared once on the path, inherited by the operation. These were
        dropped before reaching detection."""
        out = tmp_path / "f.json"
        main.main(["--spec", str(spec_file), "--format", "json", "--out", str(out)])
        fields = {m["field"] for f in json.loads(out.read_text())["findings"]
                  for m in f["matches"]}
        assert any("customer_email" in f for f in fields)

    def test_unresolved_references_are_reported(self, tmp_path, capsys):
        """An analysis that could not read part of the spec must say so, or
        "no PII found" is a claim about something never examined."""
        spec = {
            "openapi": "3.0.3",
            "info": {"title": "T", "version": "1"},
            "paths": {"/x": {"get": {"responses": {"200": {
                "description": "ok",
                "content": {"application/json": {
                    "schema": {"$ref": "#/components/schemas/Absent"}}}}}}}},
        }
        path = tmp_path / "s.json"
        path.write_text(json.dumps(spec))

        main.main(["--spec", str(path)])
        assert "unresolved $ref" in capsys.readouterr().out
