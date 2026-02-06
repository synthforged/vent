# Security Policy

## Supported versions

Only the latest release is supported.

| Version | Supported |
|---------|-----------|
| latest  | Yes       |
| older   | No        |

## Reporting a vulnerability

**Do not open a public issue.**

Email [synthforged@proton.me](mailto:synthforged@proton.me) with:
- Description of the vulnerability
- Steps to reproduce
- Impact assessment if you have one

You'll get a response within a reasonable timeframe. If the report is valid, a fix will be released and you'll be credited (unless you prefer otherwise).

## Scope

vent runs locally, captures audio from your mic, and calls `wl-copy`/`wtype`. It makes no network requests except when downloading the Whisper model on first run (via `faster-whisper`/`huggingface_hub`). There's no telemetry, no phoning home, no analytics.

If you find otherwise, that's a bug.
