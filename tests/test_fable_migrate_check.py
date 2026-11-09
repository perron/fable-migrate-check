from __future__ import annotations

import json
from pathlib import Path

import pytest

import fable_migrate_check.cli as mc


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def codes(path: Path, *args: str) -> set[str]:
    import io, contextlib
    # run via scan_path for easier assertions
    findings = mc.scan_path(path, broad="--broad" in args)
    return {f.code for f in findings}


def test_help_and_version():
    with pytest.raises(SystemExit) as exc:
        mc.main(["--help"])
    assert exc.value.code == 0
    with pytest.raises(SystemExit) as exc:
        mc.main(["--version"])
    assert exc.value.code == 0


def test_old_model_id(tmp_path, capsys):
    path = write(tmp_path / "app.py", 'model = "claude-fable-5-1"\n')
    assert mc.main([str(path)]) == 1
    out = capsys.readouterr().out
    assert "model-id-old" in out
    assert "claude-fable-5-1" in out


def test_current_model_id_is_clean(tmp_path, capsys):
    path = write(tmp_path / "app.py", 'model = "claude-fable-5-2"\nclient = Anthropic()\n')
    assert mc.main([str(path)]) == 0
    assert "model-id-old" not in capsys.readouterr().out


def test_mythos_and_bedrock_ids(tmp_path):
    path = write(
        tmp_path / "cfg.json",
        '{"model": "anthropic.claude-fable-5-1", "other": "claude-mythos-5"}\n',
    )
    found = codes(path)
    assert "model-id-old" in found


def test_does_not_flag_fable_5_2_beside_old(tmp_path):
    path = write(
        tmp_path / "app.py",
        'before = "claude-fable-5-1"\nafter = "claude-fable-5-2"\n',
    )
    findings = [f for f in mc.scan_path(path, broad=False) if f.code == "model-id-old"]
    excerpts = " ".join(f.excerpt for f in findings)
    assert "claude-fable-5-1" in excerpts
    assert "after =" not in excerpts


def test_forced_tool_choice(tmp_path, capsys):
    path = write(tmp_path / "app.py", 'payload = {"tool_choice": {"type": "any"}}\n')
    assert mc.main([str(path)]) == 1
    assert "forced-tool-choice" in capsys.readouterr().out


def test_tool_choice_auto_is_clean(tmp_path, capsys):
    path = write(tmp_path / "app.py", 'payload = {"tool_choice": {"type": "auto"}}\nclient = Anthropic()\n')
    assert mc.main([str(path)]) == 0
    assert "forced-tool-choice" not in capsys.readouterr().out


def test_manual_thinking(tmp_path):
    path = write(
        tmp_path / "app.py",
        'thinking = {"type": "enabled", "budget_tokens": 8000}\n',
    )
    found = codes(path)
    assert "manual-thinking" in found


def test_thinking_disabled(tmp_path):
    path = write(tmp_path / "app.py", 'opts = {"thinking": {"type": "disabled"}}\n')
    assert "manual-thinking" in codes(path)


def test_computer_old_tool(tmp_path, capsys):
    path = write(tmp_path / "agent.ts", 'type: "computer_20251124"\n')
    assert mc.main([str(path)]) == 1
    assert "computer-tool-old" in capsys.readouterr().out


def test_content_index_and_small_max_tokens(tmp_path):
    path = write(
        tmp_path / "app.py",
        "from anthropic import Anthropic\n"
        "text = response.content[0].text\n"
        "client.messages.create(model='claude-fable-5-2', max_tokens=256)\n",
    )
    found = codes(path)
    assert "content-index-text" in found
    assert "small-max-tokens" in found
    assert "model-id-old" not in found


def test_prefill(tmp_path):
    path = write(tmp_path / "app.py", "def build(prefill: str):\n    return prefill\n")
    assert "prefill" in codes(path)


def test_speed_fast(tmp_path):
    path = write(tmp_path / "cfg.json", '{"speed": "fast"}\n')
    assert "speed-fast" in codes(path)


def test_sampling_near_anthropic(tmp_path):
    path = write(tmp_path / "app.py", "from anthropic import Anthropic\nkwargs = dict(temperature=0.2, top_p=0.9)\n")
    assert "sampling-param" in codes(path)


def test_sampling_unrelated_is_clean(tmp_path, capsys):
    path = write(tmp_path / "train.py", "temperature = 0.2\ntop_p = 0.9\n")
    assert mc.main([str(path)]) == 0


def test_skips_node_modules(tmp_path, capsys):
    write(tmp_path / "node_modules" / "sdk" / "index.js", 'model = "claude-fable-5-1"\n')
    write(tmp_path / "app.py", "print('ok')\n")
    assert mc.main([str(tmp_path)]) == 0
    assert "model-id-old" not in capsys.readouterr().out


def test_json_output(tmp_path, capsys):
    path = write(tmp_path / "app.py", 'model = "claude-fable-5"\n')
    assert mc.main([str(path), "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["warnings"] >= 1
    assert data["guide"] == mc.GUIDE_URL


def test_broad_flags_opus(tmp_path, capsys):
    path = write(tmp_path / "app.py", 'model = "claude-opus-5-5"\n')
    assert mc.main([str(path)]) == 0
    capsys.readouterr()
    assert mc.main([str(path), "--broad"]) == 0
    out = capsys.readouterr().out
    assert "model-id-predecessor" in out


def test_missing_path(tmp_path, capsys):
    assert mc.main([str(tmp_path / "missing.py")]) == 1
    assert "path not found" in capsys.readouterr().err


def test_empty_repo(tmp_path, capsys):
    assert mc.main([str(tmp_path)]) == 0
    assert "no Fable 5.2 API migration hits" in capsys.readouterr().out


def test_json_max_tokens(tmp_path):
    path = write(tmp_path / "app.py", "from anthropic import Anthropic\npayload = {\"max_tokens\": 256}\n")
    assert "small-max-tokens" in codes(path)
