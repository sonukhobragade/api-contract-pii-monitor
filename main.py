#!/usr/bin/env python3
"""
Analyse an OpenAPI spec for personal data.

    python main.py --spec openapi.json
    python main.py --spec openapi.yaml --format json --out findings.json
    python main.py --spec openapi.json --fail-on critical

Reads a spec file, walks every endpoint's parameters, request bodies and
response schemas, and reports where personal data appears.

This path needs no database and no network. The monitoring side of this project
(history, change detection, Slack alerts) uses PostgreSQL, but answering "what
personal data does this API expose" does not, and requiring a database to ask
that question meant nobody could try the tool without provisioning one first.

Nothing is sent anywhere and no endpoint is called: the analysis reads the
document you point it at.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.pii_detector import PIIDetector, PIISeverity  # noqa: E402

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}

SEVERITY_ORDER = {
    PIISeverity.CRITICAL: 0,
    PIISeverity.HIGH: 1,
    PIISeverity.MEDIUM: 2,
    PIISeverity.LOW: 3,
}


def load_spec(path: Path) -> Dict[str, Any]:
    """Load a JSON or YAML OpenAPI document."""
    text = path.read_text(encoding="utf-8")

    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError:  # pragma: no cover - depends on the environment
            raise SystemExit(
                "Reading a YAML spec needs PyYAML: pip install pyyaml\n"
                "(or convert the spec to JSON first)"
            )
        return yaml.safe_load(text)

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is not valid JSON: {exc}")


def analyse_spec(spec: Dict[str, Any], detector: PIIDetector) -> List[Dict[str, Any]]:
    """Walk every operation in the spec and collect PII findings."""
    findings: List[Dict[str, Any]] = []
    paths = spec.get("paths") or {}

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        # Path-level parameters are inherited by every operation beneath.
        shared = [p for p in (path_item.get("parameters") or []) if isinstance(p, dict)]

        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue

            matches = []
            own = [p for p in (operation.get("parameters") or []) if isinstance(p, dict)]
            own_keys = {(p.get("name"), p.get("in")) for p in own}
            parameters = [p for p in shared if (p.get("name"), p.get("in")) not in own_keys] + own

            for param in parameters:
                name = param.get("name", "")
                if not name:
                    continue
                matches.extend(detector.detect_pii_in_parameter(
                    name,
                    param.get("schema", param),
                    param.get("in", "query"),
                    path,
                ))

            request_body = operation.get("requestBody") or {}
            for media_type, media in (request_body.get("content") or {}).items():
                if isinstance(media, dict) and isinstance(media.get("schema"), dict):
                    matches.extend(detector.detect_pii_in_schema(
                        media["schema"], f"request_body:{media_type}",
                        root_schema=spec,
                    ))

            for status, response in (operation.get("responses") or {}).items():
                if not isinstance(response, dict):
                    continue
                for media_type, media in (response.get("content") or {}).items():
                    if isinstance(media, dict) and isinstance(media.get("schema"), dict):
                        matches.extend(detector.detect_pii_in_schema(
                            media["schema"], f"response:{status}:{media_type}",
                            root_schema=spec,
                        ))

            if matches:
                findings.append({
                    "path": path,
                    "method": method.upper(),
                    "summary": operation.get("summary", ""),
                    "matches": matches,
                })

    return findings


def print_report(findings: List[Dict[str, Any]], detector: PIIDetector,
                 endpoint_count: int) -> None:
    total = sum(len(f["matches"]) for f in findings)

    print()
    print("=" * 72)
    print(f"  PII ANALYSIS — {endpoint_count} endpoints, {total} findings "
          f"across {len(findings)} endpoints")
    print("=" * 72)

    by_severity: Dict[PIISeverity, int] = {}
    for finding in findings:
        for match in finding["matches"]:
            by_severity[match.severity] = by_severity.get(match.severity, 0) + 1

    if by_severity:
        print()
        for severity in sorted(by_severity, key=lambda s: SEVERITY_ORDER[s]):
            print(f"  {severity.value.upper():<9} {by_severity[severity]}")

    for finding in sorted(
        findings,
        key=lambda f: min(SEVERITY_ORDER[m.severity] for m in f["matches"]),
    ):
        print()
        print(f"  {finding['method']} {finding['path']}")
        for match in sorted(finding["matches"], key=lambda m: SEVERITY_ORDER[m.severity]):
            print(f"    [{match.severity.value:<8}] {match.field_path or match.field_name}"
                  f"  ({match.pii_type.value}, {match.context})")

    if detector.unresolved_refs:
        # Silence here would let an incomplete analysis read as a clean one.
        print()
        print(f"  {len(detector.unresolved_refs)} unresolved $ref — fields behind "
              f"these were NOT analysed:")
        for ref in detector.unresolved_refs[:10]:
            print(f"    {ref['ref']}  at {ref['path'] or '<root>'}")

    if not findings:
        print()
        print("  No personal data detected.")
        print("  Detection is by field name, declared format and description, so"
              " this is")
        print("  evidence rather than proof. A field called `x1` holding an email"
              " address")
        print("  will not be found by any of them.")
    print()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Find personal data in an OpenAPI specification.")
    parser.add_argument("--spec", required=True, help="Path to an OpenAPI JSON or YAML file")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--out", help="Write the report to a file instead of stdout")
    parser.add_argument(
        "--fail-on", choices=["never", "any", "critical", "high"], default="never",
        help="Exit non-zero when findings at this level or above are present. "
             "Use in CI to block a release.",
    )
    args = parser.parse_args(argv)

    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"No such file: {spec_path}", file=sys.stderr)
        return 2

    spec = load_spec(spec_path)
    if not isinstance(spec, dict) or "paths" not in spec:
        print(f"{spec_path} does not look like an OpenAPI document "
              f"(no 'paths' key).", file=sys.stderr)
        return 2

    detector = PIIDetector()
    findings = analyse_spec(spec, detector)

    endpoint_count = sum(
        1
        for item in (spec.get("paths") or {}).values() if isinstance(item, dict)
        for method in item
        if method.lower() in HTTP_METHODS
    )

    if args.format == "json":
        payload = {
            "spec": str(spec_path),
            "endpoints_analysed": endpoint_count,
            "unresolved_refs": detector.unresolved_refs,
            "findings": [
                {
                    "path": f["path"],
                    "method": f["method"],
                    "matches": [
                        {
                            "field": m.field_path or m.field_name,
                            "pii_type": m.pii_type.value,
                            "severity": m.severity.value,
                            "context": m.context,
                            "confidence": m.confidence,
                        }
                        for m in f["matches"]
                    ],
                }
                for f in findings
            ],
        }
        text = json.dumps(payload, indent=2)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"Wrote {args.out}")
        else:
            print(text)
    else:
        if args.out:
            import contextlib
            with open(args.out, "w", encoding="utf-8") as fh, \
                    contextlib.redirect_stdout(fh):
                print_report(findings, detector, endpoint_count)
            print(f"Wrote {args.out}")
        else:
            print_report(findings, detector, endpoint_count)

    severities = {m.severity for f in findings for m in f["matches"]}
    if args.fail_on == "any" and severities:
        return 1
    if args.fail_on == "critical" and PIISeverity.CRITICAL in severities:
        return 1
    if args.fail_on == "high" and (
        PIISeverity.CRITICAL in severities or PIISeverity.HIGH in severities
    ):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
