# fable-migrate-check proof

Captured 2026-11-09, afternoon America/Los_Angeles (PST).

Fresh-venv install: `pip install .` succeeded and `fable-migrate-check --version` printed `fable-migrate-check 0.1.0`.

Tests: 21 passed in 0.04s
Local pytest (same tree): 21 passed.

## version
```
fable-migrate-check 0.1.0
```

## output on /tmp/ai-tools-proof/fable-migrate-check/app.py
```
warning: model-id-old: Predecessor Fable or Mythos model ID (/tmp/ai-tools-proof/fable-migrate-check/app.py:3)
  Found 'claude-fable-5-1'. Claude Fable 5.2 uses claude-fable-5-2 (Bedrock: anthropic.claude-fable-5-2). Mythos 5.2 uses claude-mythos-5-2 and is limited to verified organizations.
  excerpt: model = "claude-fable-5-1"
  suggest: Update the model ID in new conversations, then re-run your effort sweep.

warning: forced-tool-choice: Forced tool choice (/tmp/ai-tools-proof/fable-migrate-check/app.py:4)
  tool_choice of type 'any' or a named tool returns HTTP 400 on Claude Fable 5.2. Only 'auto' and 'none' are accepted.
  excerpt: payload = {"tool_choice": {"type": "any"}, "max_tokens": 256}
  suggest: Leave tool_choice at auto and name the tool in the instruction, or use a mid-conversation system message on platforms that support it.

warning: small-max-tokens: Small max_tokens (/tmp/ai-tools-proof/fable-migrate-check/app.py:4)
  max_tokens is 256. Thinking tokens count toward max_tokens on Claude Fable 5.2, so a small cap can end the turn after a thinking block and before any text.
  excerpt: payload = {"tool_choice": {"type": "any"}, "max_tokens": 256}
  suggest: Raise max_tokens to leave room for thinking, or lower the effort level.

warning: manual-thinking: Manual thinking budget or disabled thinking (/tmp/ai-tools-proof/fable-migrate-check/app.py:5)
  Adaptive thinking is always on for Claude Fable 5.2. thinking type 'disabled' and type 'enabled' with budget_tokens both return HTTP 400.
  excerpt: thinking = {"type": "enabled", "budget_tokens": 8000}
  suggest: Remove the thinking field and control spend with the effort parameter. Raise max_tokens so thinking plus text still fits.

warning: computer-tool-old: Old computer-use tool type (/tmp/ai-tools-proof/fable-migrate-check/app.py:6)
  A tools entry of type computer_20251124 returns HTTP 400 on Claude Fable 5.2 on every platform except Amazon Bedrock.
  excerpt: tools = [{"type": "computer_20251124"}]
  suggest: Declare computer_toolset_20260801 and update the agent loop. On Bedrock the earlier tool still works.

warning: content-index-text: Text read from content[0] (/tmp/ai-tools-proof/fable-migrate-check/app.py:7)
  Thinking blocks come first in a Claude Fable 5.2 response, so content[0].text can be missing or wrong. A small max_tokens value can also stop after thinking and before any text.
  excerpt: text = response.content[0].text
  suggest: Select content blocks by type, not by position.

0 error(s), 6 warning(s), 0 info
review: https://platform.claude.com/docs/en/models/fable-5-2/migration-guide
```

Exit code: 1
