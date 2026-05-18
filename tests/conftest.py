import pytest
from pathlib import Path

@pytest.fixture
def bridge_home(tmp_path, monkeypatch):
    """Redirect ~/.claude-autoresumer to a temp dir for all tests."""
    home = tmp_path / ".claude-autoresumer"
    home.mkdir()
    monkeypatch.setenv("CLAUDE_AUTORESUMER_HOME", str(home))
    return home
