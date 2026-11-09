# fable-migrate-check

Scan a repository for Messages API usage that breaks or changes when you move
to [`claude-fable-5-2`](https://platform.claude.com/docs/en/models/fable-5-2/migration-guide).

This is a static pattern scan, not a full language parser and not a rewrite
tool. It complements (and does not replace) Anthropic's own `claude-api`
skill and `/claude-api migrate`. It is not an Anthropic product.

## Install

Python 3.10 or later.

```bash
python3 -m pip install .
python3 -m pip install -e ".[dev]"  # optional, for tests
fable-migrate-check --help
```

Or without installing:

```bash
PYTHONPATH=. python3 -m fable_migrate_check --help
```

## 30-second quick start

```bash
cat > app.py << 'EOF'
from anthropic import Anthropic

model = "claude-fable-5-1"
payload = {"tool_choice": {"type": "any"}, "max_tokens": 256}
thinking = {"type": "enabled", "budget_tokens": 8000}
tools = [{"type": "computer_20251124"}]
text = response.content[0].text
EOF

fable-migrate-check app.py
```

Real output from that file (9 Nov 2026, America/Los_Angeles):

```
warning: model-id-old: Predecessor Fable or Mythos model ID (app.py:3)
  Found 'claude-fable-5-1'. Claude Fable 5.2 uses claude-fable-5-2 (Bedrock: anthropic.claude-fable-5-2). Mythos 5.2 uses claude-mythos-5-2 and is limited to verified organizations.
  excerpt: model = "claude-fable-5-1"
  suggest: Update the model ID in new conversations, then re-run your effort sweep.

warning: forced-tool-choice: Forced tool choice (app.py:4)
  tool_choice of type 'any' or a named tool returns HTTP 400 on Claude Fable 5.2. Only 'auto' and 'none' are accepted.
  excerpt: payload = {"tool_choice": {"type": "any"}, "max_tokens": 256}
  suggest: Leave tool_choice at auto and name the tool in the instruction, or use a mid-conversation system message on platforms that support it.

warning: small-max-tokens: Small max_tokens (app.py:4)
  max_tokens is 256. Thinking tokens count toward max_tokens on Claude Fable 5.2, so a small cap can end the turn after a thinking block and before any text.
  excerpt: payload = {"tool_choice": {"type": "any"}, "max_tokens": 256}
  suggest: Raise max_tokens to leave room for thinking, or lower the effort level.

warning: manual-thinking: Manual thinking budget or disabled thinking (app.py:5)
  Adaptive thinking is always on for Claude Fable 5.2. thinking type 'disabled' and type 'enabled' with budget_tokens both return HTTP 400.
  excerpt: thinking = {"type": "enabled", "budget_tokens": 8000}
  suggest: Remove the thinking field and control spend with the effort parameter. Raise max_tokens so thinking plus text still fits.

warning: computer-tool-old: Old computer-use tool type (app.py:6)
  A tools entry of type computer_20251124 returns HTTP 400 on Claude Fable 5.2 on every platform except Amazon Bedrock.
  excerpt: tools = [{"type": "computer_20251124"}]
  suggest: Declare computer_toolset_20260801 and update the agent loop. On Bedrock the earlier tool still works.

warning: content-index-text: Text read from content[0] (app.py:7)
  Thinking blocks come first in a Claude Fable 5.2 response, so content[0].text can be missing or wrong. A small max_tokens value can also stop after thinking and before any text.
  excerpt: text = response.content[0].text
  suggest: Select content blocks by type, not by position.

0 error(s), 6 warning(s), 0 info
review: https://platform.claude.com/docs/en/models/fable-5-2/migration-guide
```

Exit codes: `0` clean or info-only, `1` warnings, `2` errors.

`--broad` also flags other predecessor model IDs such as `claude-opus-5-5`
(as info). `--json` prints a structured report. The scan skips `node_modules`
and virtualenvs.

## Use it with your agent

You can point a coding agent at this repository and ask it to scan your
project, explain a finding, or write a similar small CLI in the same style.

Sample prompt:

```
Use the fable-migrate-check tool in this repo. Install it in a fresh
virtualenv with `python3 -m pip install .`, run `python3 -m pytest -q`,
then scan this project (or the README example) for Claude Fable 5.2 API
footguns. Summarize what would return HTTP 400 versus what is only a
behavior change. Do not rewrite production code unless I ask, and do not
publish the package. If you want to build a similar tool, match this
repo's layout: a small MIT Python CLI, behavior tests, honest limits in
the README, and no secrets.
```

## How you can help

- Send a minimal file that was a false positive, or a real 400 that the
  scan missed, with the platform you were on (Claude API, Bedrock, Foundry).
- Add a test for a new pattern, plus a nearby clean case (`claude-fable-5-2`
  must never be flagged as an old ID).
- Note when the official guide changes.

See `CONTRIBUTING.md`. Do not paste API keys or private request logs into
issues.

## Credit

Motivated by Anthropic's public Claude Fable 5.2 migration guide (fetched
9 Nov 2026). Findings are original summaries with a link to that guide. No
guide text or official skill source was copied.

## Limits

- This is a pattern scan, not an AST migration and not a live API test. It can miss generated code, unusual wrappers, or values built at runtime.
- The word `prefill` in an unrelated function is flagged; review that finding before changing anything.
- Sampling-parameter hits only fire in files that already look like Claude / Anthropic client code.
- `computer_20251124` still works on Amazon Bedrock; the finding says so.
- Claude Mythos 5.2 is limited to verified organizations. This tool does not check whether you have access.
- Guidance was checked on 9 Nov 2026 and may change.

From GitHub you can also install with:

```bash
python3 -m pip install git+https://github.com/perron/fable-migrate-check.git
```

This package is not published to PyPI.

## License

MIT. See `LICENSE`. Please read `SECURITY.md` before filing a vulnerability report.
