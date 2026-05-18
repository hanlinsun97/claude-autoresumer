from unittest.mock import patch, MagicMock
from claude_bridge.probe import probe, ProbeError

def _mock_run(stdout="hello", stderr="", returncode=0):
    result = MagicMock()
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result

def test_probe_returns_true_when_output_is_normal():
    with patch("claude_bridge.probe.subprocess.run", return_value=_mock_run(stdout="ok")):
        assert probe() is True

def test_probe_returns_false_on_usage_limit():
    with patch("claude_bridge.probe.subprocess.run",
               return_value=_mock_run(stdout="", stderr="You have reached your usage limit")):
        assert probe() is False

def test_probe_returns_false_on_rate_limit():
    with patch("claude_bridge.probe.subprocess.run",
               return_value=_mock_run(stderr="rate limit exceeded")):
        assert probe() is False

def test_probe_raises_on_timeout():
    import subprocess
    with patch("claude_bridge.probe.subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 30)):
        try:
            probe()
            assert False, "should have raised"
        except ProbeError:
            pass

def test_probe_raises_when_claude_not_found():
    with patch("claude_bridge.probe.subprocess.run", side_effect=FileNotFoundError()):
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
    with patch("claude_bridge.probe.subprocess.run",
               return_value=_mock_run(stdout="", stderr="error: unknown option '--max-tokens'", returncode=1)):
        with pytest.raises(ProbeError, match="unknown option"):
            probe()

def test_probe_command_does_not_use_max_tokens_flag():
    """Hard-pin against re-introducing the non-existent --max-tokens flag."""
    captured = {}
    def fake_run(args, **kwargs):
        captured["args"] = args
        return _mock_run(stdout="ok")
    with patch("claude_bridge.probe.subprocess.run", side_effect=fake_run):
        probe()
    assert "--max-tokens" not in captured["args"]
