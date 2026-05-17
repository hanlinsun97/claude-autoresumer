import pytest
from pathlib import Path

@pytest.fixture
def bridge_home(tmp_path, monkeypatch):
    """Redirect ~/.claude-bridge to a temp dir for all tests."""
    home = tmp_path / ".claude-bridge"
    home.mkdir()
    monkeypatch.setenv("CLAUDE_BRIDGE_HOME", str(home))
    return home
