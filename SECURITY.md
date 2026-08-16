# Security policy

## Reporting a vulnerability

Please do not open a public issue for a security problem.

Use GitHub's private vulnerability reporting on this repository:
**Security → Report a vulnerability**. That opens a private thread with the
maintainer.

Include what you found, how to reproduce it, and what an attacker gets. Expect a
first reply within a week. This is a personal project maintained in spare time.

## Supported versions

The latest commit on the default branch. There are no maintained release
branches.

## Scope

In scope: credential handling, anything that transmits an analysed spec or its
findings somewhere unintended, SQL injection in the monitoring path, and **any
case where the tool reports an endpoint as clean while personal data is
present**.

That last one is a security issue here, not merely a bug. The purpose of this
tool is to tell you where personal data sits in your API. A missed detection
means someone reviews a report, sees nothing, and ships.

Out of scope: the design limits stated in the README. Detection works from field
names, declared formats and descriptions, so a field named `x1` holding an email
address will not be found. That is a documented boundary, not a defect.

## Handling the output safely

**A PII analysis report is a target list.** It states which endpoints expose
which personal data, at which path, and which findings are still open. Treat a
generated report as sensitive:

- Do not commit it. `.gitignore` blocks the report filenames by pattern, but
  that only helps for the names it knows.
- Do not paste one into an issue, a chat, or a ticket that is broadly readable.
- Store it wherever your own security findings already live.

## What the tool touches

- **`python main.py --spec ...` reads a local file.** No database, no network,
  no call to the API being described.
- **The monitoring mode connects to PostgreSQL** and fetches specs over HTTP
  when given a URL.
- **`src/contract_tester.py` issues real HTTP requests** to whatever base URL
  you configure. It is opt-in, but it is there — do not point it at production
  and expect a read-only tool.

## If you leak a credential

Rotating is the fix. Deleting the key from a file, or rewriting git history,
does not revoke anything: assume any key that was ever committed is compromised
and issue a new one.
