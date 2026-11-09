# AGENTS.md

This repository is fable-migrate-check, a small MIT-licensed Python CLI that
scans a tree for Messages API usage that breaks or changes when moving to
`claude-fable-5-2`.

## Layout

- `fable_migrate_check/cli.py` — patterns and CLI
- `tests/test_fable_migrate_check.py` — behavior tests
- `README.md` — install, a real quick-start example, limits

## How to work here

1. `pip install -e ".[dev]"` and `python3 -m pytest -q`.
2. Patterns must not flag `claude-fable-5-2` or `claude-mythos-5-2` as old.
3. Forced `tool_choice` of `auto` or `none` must stay clean.
4. This is a regex/heuristic scan across common source extensions. Do not
   pretend it is a full AST migration.
5. Exit codes: `0` clean (infos only are still 0), `1` warnings, `2` errors.

## Do not

- Do not publish, force-push, or change repository visibility.
- Do not call the Anthropic API from this tool.
- Do not copy Anthropic's `claude-api` skill source.

## Checks before you finish

```bash
python3 -m pytest -q
fable-migrate-check --version
```
