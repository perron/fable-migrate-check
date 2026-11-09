"""Scan a repo for Messages API usage that breaks or changes on Claude Fable 5.2.

This is a static pattern scan, not a full language parser. It does not call the
API and it does not rewrite your code. Findings point at Anthropic's public
migration guide.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

__version__ = "0.1.0"

GUIDE_URL = "https://platform.claude.com/docs/en/models/fable-5-2/migration-guide"

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".tox",
    "vendor",
    ".mypy_cache",
    ".pytest_cache",
    ".eggs",
    ".tox",
}
CODE_SUFFIXES = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".mjs",
    ".cjs",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".rb",
    ".go",
    ".java",
    ".kt",
    ".cs",
    ".php",
    ".md",
}

# Predecessor Fable / Mythos IDs (not 5-2). Word boundaries avoid matching 5-2.
FABLE_OLD_RE = re.compile(
    r"""(?:anthropic\.)?claude-(?:fable|mythos)-5(?:-1)?(?![.\w-])""",
    re.IGNORECASE,
)
# Broader predecessor IDs people migrate from. Off by default unless --broad.
BROAD_MODEL_RE = re.compile(
    r"""(?:anthropic\.)?claude-(?:opus-5-5|opus-5|opus-4-8|opus-4-7|sonnet-5-5|sonnet-4-6)(?![.\w-])""",
    re.IGNORECASE,
)
# Confirm we do not treat 5-2 as old.
CURRENT_MODEL_RE = re.compile(
    r"""(?:anthropic\.)?claude-(?:fable|mythos)-5-2(?![.\w-])""",
    re.IGNORECASE,
)

# tool_choice of type any or tool (not auto / none).
TOOL_CHOICE_RE = re.compile(
    r"""tool_choice\s*[=:]\s*(?:\{\s*['"]type['"]\s*:\s*['"](?:any|tool)['"]|['"](?:any|tool)['"])""",
    re.IGNORECASE,
)
TOOL_CHOICE_JSON_RE = re.compile(
    r"""['"]tool_choice['"]\s*:\s*\{\s*['"]type['"]\s*:\s*['"](?:any|tool)['"]""",
    re.IGNORECASE,
)
TOOL_CHOICE_ENUM_RE = re.compile(
    r"""\bToolChoice(?:Any|Tool)\b|\btool_choice\s*=\s*ToolChoice\.(?:ANY|TOOL)\b""",
)

THINKING_DISABLED_RE = re.compile(
    r"""['"]?thinking['"]?\s*[=:]\s*\{?\s*['"]type['"]\s*:\s*['"]disabled['"]""",
    re.IGNORECASE,
)
THINKING_DISABLED_ALT_RE = re.compile(
    r"""['"]type['"]\s*:\s*['"]disabled['"]""",
    re.IGNORECASE,
)
BUDGET_TOKENS_RE = re.compile(r"""\bbudget_tokens\b""", re.IGNORECASE)
THINKING_ENABLED_RE = re.compile(
    r"""['"]?thinking['"]?\s*[=:]\s*\{?\s*['"]type['"]\s*:\s*['"]enabled['"]""",
    re.IGNORECASE,
)

COMPUTER_OLD_RE = re.compile(r"""computer_20251124""", re.IGNORECASE)
COMPUTER_NEW_RE = re.compile(r"""computer_toolset_20260801""", re.IGNORECASE)

PREFILL_RE = re.compile(r"""\bprefill\b""", re.IGNORECASE)

CONTENT_INDEX_RE = re.compile(
    r"""content\s*\[\s*0\s*\]\s*(?:\.\s*text|\s*\[\s*['"]text['"]\s*\])""",
    re.IGNORECASE,
)

SPEED_FAST_RE = re.compile(
    r"""['"]speed['"]\s*:\s*['"]fast['"]|\bspeed\s*=\s*['"]fast['"]""",
    re.IGNORECASE,
)

STRICT_RE = re.compile(r"""['"]strict['"]\s*:\s*true|\bstrict\s*=\s*True""", re.IGNORECASE)
OUTPUT_FORMAT_RE = re.compile(
    r"""output_config\s*\.\s*format|['"]output_config['"]\s*:\s*\{[^}]{0,200}format""",
    re.IGNORECASE,
)
OUTPUT_FORMAT_FIELD_RE = re.compile(r"""\boutput_format\b""", re.IGNORECASE)

MAX_TOKENS_RE = re.compile(
    r"""['"]?max_tokens['"]?\s*[=:]\s*(\d+)""",
    re.IGNORECASE,
)

TEMPERATURE_RE = re.compile(r"""['"]?temperature['"]?\s*[=:]""", re.IGNORECASE)
TOP_P_RE = re.compile(r"""['"]?top_p['"]?\s*[=:]""", re.IGNORECASE)
TOP_K_RE = re.compile(r"""['"]?top_k['"]?\s*[=:]""", re.IGNORECASE)

ADVISOR_OLD_RE = re.compile(
    r"""advisor[^.\n]{0,80}(?:claude-fable-5(?:-1)?|claude-mythos-5(?:-1)?|claude-opus-5(?:-5)?)(?!-2)""",
    re.IGNORECASE,
)

CLAUDE_NEAR_RE = re.compile(
    r"""\b(?:anthropic|claude|messages\.create|AsyncAnthropic|Anthropic)\b""",
    re.IGNORECASE,
)


@dataclass
class Finding:
    severity: str
    code: str
    title: str
    message: str
    suggest: str
    path: str
    line: int
    excerpt: str


def iter_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in CODE_SUFFIXES:
            files.append(path)
    return sorted(files)


def line_is_comment(line: str, suffix: str) -> bool:
    stripped = line.strip()
    if suffix == ".py" and stripped.startswith("#"):
        return True
    if suffix in {".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".go", ".java", ".kt", ".cs", ".php"} and stripped.startswith("//"):
        return True
    return False


def scan_text(text: str, path: Path, *, broad: bool) -> list[Finding]:
    findings: list[Finding] = []
    suffix = path.suffix.lower()
    lines = text.splitlines() or [""]
    looks_like_claude = bool(CLAUDE_NEAR_RE.search(text)) or suffix in {".json", ".yml", ".yaml", ".toml", ".md"}

    def add(severity: str, code: str, title: str, message: str, suggest: str, lineno: int, excerpt: str) -> None:
        findings.append(
            Finding(severity, code, title, message, suggest, str(path), lineno, excerpt.strip()[:240])
        )

    for i, line in enumerate(lines, 1):
        if line_is_comment(line, suffix):
            continue
        # Old Fable / Mythos IDs, but not 5-2.
        for match in FABLE_OLD_RE.finditer(line):
            token = match.group(0)
            if CURRENT_MODEL_RE.fullmatch(token):
                continue
            if re.search(r"5-2$", token, re.I):
                continue
            add(
                "warning",
                "model-id-old",
                "Predecessor Fable or Mythos model ID",
                (
                    f"Found {token!r}. Claude Fable 5.2 uses claude-fable-5-2 "
                    "(Bedrock: anthropic.claude-fable-5-2). Mythos 5.2 uses "
                    "claude-mythos-5-2 and is limited to verified organizations."
                ),
                "Update the model ID in new conversations, then re-run your effort sweep.",
                i,
                line,
            )
        if broad:
            for match in BROAD_MODEL_RE.finditer(line):
                add(
                    "info",
                    "model-id-predecessor",
                    "Other predecessor model ID",
                    (
                        f"Found {match.group(0)!r}. If this call is moving to "
                        "Claude Fable 5.2, the model ID needs to change, and "
                        "other request fields may need to change too."
                    ),
                    "See the migration guide section that matches the model you are coming from.",
                    i,
                    line,
                )
        if TOOL_CHOICE_RE.search(line) or TOOL_CHOICE_JSON_RE.search(line) or TOOL_CHOICE_ENUM_RE.search(line):
            add(
                "warning",
                "forced-tool-choice",
                "Forced tool choice",
                (
                    "tool_choice of type 'any' or a named tool returns HTTP 400 "
                    "on Claude Fable 5.2. Only 'auto' and 'none' are accepted."
                ),
                "Leave tool_choice at auto and name the tool in the instruction, or use a mid-conversation system message on platforms that support it.",
                i,
                line,
            )
        if THINKING_DISABLED_RE.search(line) or THINKING_ENABLED_RE.search(line) or BUDGET_TOKENS_RE.search(line):
            add(
                "warning",
                "manual-thinking",
                "Manual thinking budget or disabled thinking",
                (
                    "Adaptive thinking is always on for Claude Fable 5.2. "
                    "thinking type 'disabled' and type 'enabled' with "
                    "budget_tokens both return HTTP 400."
                ),
                "Remove the thinking field and control spend with the effort parameter. Raise max_tokens so thinking plus text still fits.",
                i,
                line,
            )
        elif looks_like_claude and THINKING_DISABLED_ALT_RE.search(line) and "thinking" in text.lower():
            # Loose 'type: disabled' only when the file already talks about thinking.
            if "thinking" in line.lower() or "disabled" in line.lower():
                add(
                    "warning",
                    "manual-thinking",
                    "Possible disabled thinking setting",
                    "A 'type: disabled' setting in a file that mentions thinking may be a manual thinking config, which returns HTTP 400 on Claude Fable 5.2.",
                    "Remove thinking: {type: 'disabled'} and lower effort instead.",
                    i,
                    line,
                )
        if COMPUTER_OLD_RE.search(line):
            add(
                "warning",
                "computer-tool-old",
                "Old computer-use tool type",
                (
                    "A tools entry of type computer_20251124 returns HTTP 400 "
                    "on Claude Fable 5.2 on every platform except Amazon Bedrock."
                ),
                "Declare computer_toolset_20260801 and update the agent loop. On Bedrock the earlier tool still works.",
                i,
                line,
            )
        if PREFILL_RE.search(line):
            add(
                "warning",
                "prefill",
                "Possible assistant prefill",
                "Prefilling the assistant message returns HTTP 400 on Claude Fable 5.2, as on Fable 5.1. This hit is a name match for 'prefill' and may be a false positive.",
                "Put starting instructions in the system prompt instead of a prefilled assistant turn.",
                i,
                line,
            )
        if CONTENT_INDEX_RE.search(line):
            add(
                "warning",
                "content-index-text",
                "Text read from content[0]",
                (
                    "Thinking blocks come first in a Claude Fable 5.2 response, "
                    "so content[0].text can be missing or wrong. A small "
                    "max_tokens value can also stop after thinking and before any text."
                ),
                "Select content blocks by type, not by position.",
                i,
                line,
            )
        if SPEED_FAST_RE.search(line):
            add(
                "warning",
                "speed-fast",
                "Fast mode setting",
                (
                    "speed: 'fast' is not valid in every Fable 5.2 hosting option. "
                    "Remove it in Claude Managed Agents. On Microsoft Foundry, "
                    "fast mode is a separate claude-fable-5-2-fast deployment."
                ),
                "Keep speed 'fast' only on a platform the migration guide lists for this model, and re-baseline cost.",
                i,
                line,
            )
        if looks_like_claude and STRICT_RE.search(line):
            add(
                "info",
                "strict-output",
                "strict: true",
                "In an organization with customer-managed encryption keys, structured outputs (including strict tool use) are not available on Claude Fable 5.2.",
                "If you are in a CMEK org, remove strict: true and validate the tool input or JSON in your code.",
                i,
                line,
            )
        if looks_like_claude and (OUTPUT_FORMAT_RE.search(line) or OUTPUT_FORMAT_FIELD_RE.search(line)):
            add(
                "info",
                "structured-output-format",
                "Structured output format field",
                "output_config.format / output_format is not available for Claude Fable 5.2 in CMEK organizations, and older output_format request fields may need to be removed.",
                "Check the migration guide for your previous model, and validate JSON in your code if you drop the field.",
                i,
                line,
            )
        if looks_like_claude:
            for match in MAX_TOKENS_RE.finditer(line):
                value = int(match.group(1))
                if value < 2048:
                    add(
                        "warning",
                        "small-max-tokens",
                        "Small max_tokens",
                        (
                            f"max_tokens is {value}. Thinking tokens count toward "
                            "max_tokens on Claude Fable 5.2, so a small cap can "
                            "end the turn after a thinking block and before any text."
                        ),
                        "Raise max_tokens to leave room for thinking, or lower the effort level.",
                        i,
                        line,
                    )
            if TEMPERATURE_RE.search(line) or TOP_P_RE.search(line) or TOP_K_RE.search(line):
                add(
                    "warning",
                    "sampling-param",
                    "Sampling parameter",
                    "The migration guide says to omit temperature, top_p, and top_k on Claude Fable 5.2, as on Fable 5.1. Some values return HTTP 400.",
                    "Remove these parameters from Fable 5.2 requests unless you have confirmed a supported value.",
                    i,
                    line,
                )
        if ADVISOR_OLD_RE.search(line):
            add(
                "warning",
                "advisor-old-model",
                "Advisor model may be too old",
                "A Claude Fable 5.2 or Mythos 5.2 executor accepts only Fable 5.2 or Mythos 5.2 as its advisor. An older advisor returns HTTP 400.",
                "Set the advisor's model to claude-fable-5-2 or claude-mythos-5-2 in a new conversation (changing tools mid-conversation can fail the prefix check).",
                i,
                line,
            )

    return findings


def scan_path(path: Path, *, broad: bool) -> list[Finding]:
    findings: list[Finding] = []
    for file in iter_files(path):
        text = file.read_text(encoding="utf-8", errors="replace")
        findings.extend(scan_text(text, file, broad=broad))
    return findings


def format_finding(f: Finding) -> str:
    loc = f"{f.path}:{f.line}" if f.line else f.path
    parts = [f"{f.severity}: {f.code}: {f.title} ({loc})"]
    parts.append(f"  {f.message}")
    if f.excerpt:
        parts.append(f"  excerpt: {f.excerpt}")
    parts.append(f"  suggest: {f.suggest}")
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fable-migrate-check",
        description=(
            "Scan source files for Messages API usage that breaks or changes "
            "when moving to claude-fable-5-2. Static patterns only; it does not "
            "rewrite code or call the API."
        ),
    )
    parser.add_argument("path", nargs="?", default=".", help="file or directory (default: current directory)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--broad",
        action="store_true",
        help="also flag other predecessor IDs such as claude-opus-5-5 (info)",
    )
    parser.add_argument("--version", action="version", version=f"fable-migrate-check {__version__}")
    args = parser.parse_args(argv)
    target = Path(args.path)
    if not target.exists():
        print(f"error: path not found: {target}", file=sys.stderr)
        return 1
    findings = scan_path(target, broad=args.broad)
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    infos = sum(1 for f in findings if f.severity == "info")
    if args.json:
        print(
            json.dumps(
                {
                    "findings": [asdict(f) for f in findings],
                    "errors": errors,
                    "warnings": warnings,
                    "infos": infos,
                    "guide": GUIDE_URL,
                },
                indent=2,
            )
        )
    else:
        if not findings:
            print(f"ok: no Fable 5.2 API migration hits in {target}")
        else:
            for f in findings:
                print(format_finding(f))
                print()
            print(f"{errors} error(s), {warnings} warning(s), {infos} info")
        print(f"review: {GUIDE_URL}")
    if errors:
        return 2
    if warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
