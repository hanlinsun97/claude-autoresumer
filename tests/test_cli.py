from pathlib import Path
from click.testing import CliRunner
from claude_autoresumer.cli import cli
from claude_autoresumer import queue as q_mod
from claude_autoresumer import sandbox


def test_queue_add_basic(bridge_home):
    (bridge_home / "src").mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, [
        "queue", "add",
        "--prompt", "do something",
        "--cwd", str(bridge_home),
        "--file", "src/",
    ])
    assert result.exit_code == 0, result.output
    queue = q_mod.load()
    assert len(queue.jobs) == 1
    assert queue.jobs[0].prompt == "do something"


def test_queue_add_accepts_repeated_file_options(bridge_home):
    (bridge_home / "src").mkdir()
    (bridge_home / "test.py").write_text("x")
    runner = CliRunner()
    result = runner.invoke(cli, [
        "queue", "add",
        "--prompt", "do something",
        "--cwd", str(bridge_home),
        "--file", "src/",
        "--file", "test.py",
    ])
    assert result.exit_code == 0, result.output
    job = q_mod.load().jobs[0]
    assert job.source_files == ["src/", "test.py"]


def test_queue_add_rejects_paths_outside_cwd(bridge_home):
    runner = CliRunner()
    result = runner.invoke(cli, [
        "queue", "add",
        "--prompt", "do something",
        "--cwd", str(bridge_home),
        "--file", "../secret.py",
    ])
    assert result.exit_code != 0
    assert "must stay inside cwd" in result.output


def test_queue_add_accepts_max_retry_hours(bridge_home):
    (bridge_home / "src").mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, [
        "queue", "add",
        "--prompt", "do something",
        "--cwd", str(bridge_home),
        "--file", "src/",
        "--max-retry-hours", "12",
    ])
    assert result.exit_code == 0, result.output
    job = q_mod.load().jobs[0]
    assert job.max_retry_hours == 12.0


def test_queue_add_defaults_max_retry_hours_to_24(bridge_home):
    (bridge_home / "src").mkdir()
    runner = CliRunner()
    runner.invoke(cli, [
        "queue", "add",
        "--prompt", "do something",
        "--cwd", str(bridge_home),
        "--file", "src/",
    ])
    job = q_mod.load().jobs[0]
    assert job.max_retry_hours == 24.0


def test_queue_list_shows_jobs(bridge_home):
    from claude_autoresumer.models import Job
    q_mod.add(Job(prompt="list me", cwd="/tmp"))
    runner = CliRunner()
    result = runner.invoke(cli, ["queue", "list"])
    assert "list me" in result.output


def test_queue_clear_removes_pending(bridge_home):
    from claude_autoresumer.models import Job
    q_mod.add(Job(prompt="clear me", cwd="/tmp"))
    runner = CliRunner()
    runner.invoke(cli, ["queue", "clear"])
    assert q_mod.load().jobs == []


def test_status_shows_queue_summary(bridge_home):
    from claude_autoresumer.models import Job
    q_mod.add(Job(prompt="p1", cwd="/tmp"))
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert "pending" in result.output.lower() or "1" in result.output


def test_probe_command_exits_0_when_available(bridge_home):
    from unittest.mock import patch
    runner = CliRunner()
    with patch("claude_autoresumer.cli._probe_fn", return_value=True):
        result = runner.invoke(cli, ["probe"])
    assert result.exit_code == 0


def test_workspaces_list_empty(bridge_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["workspaces", "list"])
    assert result.exit_code == 0


def test_start_command_rejects_unknown_self_heal_flag(bridge_home):
    """The start command should not accept --self-heal (removed in the pivot)."""
    runner = CliRunner()
    result = runner.invoke(cli, ["start", "--self-heal", "8h"])
    assert result.exit_code != 0


def test_queue_add_rejects_unknown_workflow_flag(bridge_home):
    """--workflow was removed in the pivot."""
    (bridge_home / "src").mkdir()
    runner = CliRunner()
    result = runner.invoke(cli, [
        "queue", "add",
        "--prompt", "x",
        "--cwd", str(bridge_home),
        "--file", "src/",
        "--workflow", "tdd",
    ])
    assert result.exit_code != 0


def test_discard_command(bridge_home, tmp_path):
    src = tmp_path / "p"
    src.mkdir()
    (src / "f.py").write_text("x")
    sandbox.create("my-job", str(src), ["f.py"])
    runner = CliRunner()
    result = runner.invoke(cli, ["workspaces", "discard", "my-job"])
    assert result.exit_code == 0
    assert not sandbox.workspace_path("my-job").exists()
