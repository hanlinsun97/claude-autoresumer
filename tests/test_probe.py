from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from claude_autoresumer.probe import probe, ProbeError, parse_reset_at

def _mock_run(stdout="hello", stderr="", returncode=0):
    result = MagicMock()
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result

def test_probe_returns_true_when_output_is_normal():
    with patch("claude_autoresumer.probe.subprocess.run", return_value=_mock_run(stdout="ok")):
        assert probe() is True

def test_probe_returns_false_on_usage_limit():
    with patch("claude_autoresumer.probe.subprocess.run",
               return_value=_mock_run(stdout="", stderr="You have reached your usage limit")):
        assert probe() is False

def test_probe_returns_false_on_rate_limit():
    with patch("claude_autoresumer.probe.subprocess.run",
               return_value=_mock_run(stderr="rate limit exceeded")):
        assert probe() is False

def test_probe_raises_on_timeout():
    import subprocess
    with patch("claude_autoresumer.probe.subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 30)):
        try:
            probe()
            assert False, "should have raised"
        except ProbeError:
            pass

def test_probe_raises_when_claude_not_found():
    with patch("claude_autoresumer.probe.subprocess.run", side_effect=FileNotFoundError()):
        try:
            probe()
            assert False, "should have raised"
        except ProbeError:
            pass

def test_probe_raises_on_nonzero_exit_without_usage_pattern():
    """Non-zero exit with no usage-limit pattern (e.g. auth error, bad flag) → ProbeError.

    Regression: previously the probe used `--max-tokens 1` which doesn't exist;
    `claude` exited 1 with "unknown option" and probe falsely reported "usage limit."
    """
    import pytest
    with patch("claude_autoresumer.probe.subprocess.run",
               return_value=_mock_run(stdout="", stderr="error: unknown option '--max-tokens'", returncode=1)):
        with pytest.raises(ProbeError, match="unknown option"):
            probe()

def test_probe_command_does_not_use_max_tokens_flag():
    """Hard-pin against re-introducing the non-existent --max-tokens flag."""
    captured = {}
    def fake_run(args, **kwargs):
        captured["args"] = args
        return _mock_run(stdout="ok")
    with patch("claude_autoresumer.probe.subprocess.run", side_effect=fake_run):
        probe()
    assert "--max-tokens" not in captured["args"]


def test_parse_reset_at_pipe_epoch_seconds():
    """Format observed in claude-auto-resume: 'Claude AI usage limit reached|<unix_epoch>'."""
    target = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
    msg = f"Claude AI usage limit reached|{int(target.timestamp())}"
    parsed = parse_reset_at(msg)
    assert parsed == target


def test_parse_reset_at_pipe_epoch_milliseconds():
    target = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)
    msg = f"Claude AI usage limit reached|{int(target.timestamp() * 1000)}"
    parsed = parse_reset_at(msg)
    assert parsed == target


def test_parse_reset_at_reset_at_phrase():
    target = datetime(2026, 5, 18, 18, 0, 0, tzinfo=timezone.utc)
    msg = f"Usage limit reached. Reset at {int(target.timestamp())}."
    parsed = parse_reset_at(msg)
    assert parsed == target


def test_parse_reset_at_iso_timestamp():
    msg = "usage limit hit, will reset at 2026-05-18T18:00:00Z."
    parsed = parse_reset_at(msg)
    assert parsed == datetime(2026, 5, 18, 18, 0, 0, tzinfo=timezone.utc)


def test_parse_reset_at_returns_none_when_no_timestamp():
    assert parse_reset_at("you have hit your usage limit") is None
    assert parse_reset_at("") is None


def test_parse_reset_at_ignores_garbage_numbers():
    """A 4-digit number shouldn't be misread as an epoch second."""
    assert parse_reset_at("usage limit reached after 100 calls") is None
