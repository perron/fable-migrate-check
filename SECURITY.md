# Security Policy

This project is a small local command-line tool. It does not phone home and does not require an API key.

## Reporting a vulnerability

Please open a [GitHub issue](https://github.com/perron/fable-migrate-check/issues) and mention that it is a security report. Do not include secrets, tokens, or private file contents in the issue.

If the report includes a working exploit against this tool, describe the impact and a minimal reproduction without pasting live credentials.

## Notes for this tool

fable-migrate-check only reads the files you point it at. It does not rewrite them and it does not call the Anthropic API. A pattern match can be a false positive (for example the word 'prefill' in an unrelated function). Review each finding against the official migration guide before changing production traffic.

## Supported versions

The `master` branch and the latest tagged release, when one exists, are supported.
