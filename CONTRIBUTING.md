# Contributing to fable-migrate-check

Thanks for helping. This is a static pattern scanner, not a full language
parser and not a substitute for Anthropic's own `/claude-api migrate` skill.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
fable-migrate-check --help
```

Add a fixture file for each new check: one case that should fire, and one
nearby case that should stay clean (for example `claude-fable-5-2` must not
be flagged as an old ID).

## Rules

- Link to the official migration guide. Do not copy long passages from it.
- Keep the default scan focused on Fable / Mythos predecessor IDs and hard
  400s. Put noisier predecessor IDs such as `claude-opus-5-5` behind `--broad`.
- Skip `node_modules`, virtualenvs, and build directories.

## What not to do

- Do not add network calls or rewrite the user's code automatically.
- Do not commit credentials or private API logs.
- Do not change repository visibility or publish to PyPI unless the
  maintainer asks for that exact action.

## Pull requests

Cite the migration-guide section you used and the date you fetched it.
