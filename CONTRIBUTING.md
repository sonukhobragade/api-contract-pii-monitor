# Contributing

Thanks for taking a look. This is a small project, so the process is short.

## Getting set up

```bash
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

Analysing a spec needs no database:

```bash
python main.py --spec examples/sample-openapi.json
```

The monitoring mode (history, change detection, Slack) needs Postgres. The tests
do not.

## Before you open a pull request

```bash
bash tools/local_gate.sh
```

Lint, unit tests, and a collection smoke check. CI runs the same script, so a
green gate locally means a green gate on GitHub. If it is red, fix the code —
never loosen a check to make it pass.

## The rule that matters most here

**A false negative is the worst thing this project can produce.**

A false positive costs a reviewer ten minutes. A false negative means an API
ships with personal data in it and a report saying it is clean, and nobody looks
again. Several tests in `tests/test_pii_detector.py` exist because exactly that
happened: `government_id` matched no pattern, `format: email` was ignored,
`allOf` branches were never walked, and everything behind a `$ref` went
unexamined.

So a change to detection needs a test for the case that was missed, not only for
the case that works. And it needs the counterweight: a schema with no personal
data in it must still come back empty. Detection that flags everything is as
useless as detection that flags nothing, just louder.

Two more rules that follow from the same principle:

- **Fail closed.** If analysis of an endpoint raises, the result must say it
  failed. `PIIDetectionResult.failed()` exists because a bare result reads as
  "0 findings, compliance 100", so an exception used to look like a clean bill
  of health.
- **Say when the analysis is incomplete.** An unresolvable `$ref` or a
  truncated traversal must be reported. Silence there turns "I could not read
  this" into "there is nothing here".

## Adding a pattern

`core/pii_detector.py` holds the patterns. Keep them specific: a generic `id`
pattern matches half of every API, and the suppression list in `NON_PII_FIELDS`
is matched as **exact names** rather than regexes for the same reason — a loose
`id` entry would hide `national_id` and `tax_id`.

## What not to send

**Never include a real PII analysis report.** It is a target list: it names
exactly which endpoints expose which personal data and which are still unfixed.
Do not put one in an issue, a fixture, or a screenshot.

The same goes for real OpenAPI specs from a private API, internal hostnames,
service names, and credentials. Use `examples/sample-openapi.json`, which is
synthetic, or write your own.

## Reporting bugs

Open an issue with the shape of the schema that misbehaved — reduced to the
smallest case, with the field names changed if they are sensitive — what the
tool reported, and what you expected.

A missed detection is worth reporting even if you are not sure. That is the
failure mode that matters.
