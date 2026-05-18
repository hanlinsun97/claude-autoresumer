import subprocess
import re

USAGE_LIMIT_PATTERNS = [
    r"usage limit",
    r"rate.?limit",
    r"quota exceeded",
    r"exceeded.*usage",
    r"plan.*limit",
]


class ProbeError(Exception):
    pass


def probe() -> bool:
    """Return True if Claude Code usage is currently available.

    Returns False only when the response clearly indicates a usage/rate/quota
    limit. Other non-zero exits (auth errors, network failures, bad flags)
    raise ProbeError so the caller can surface the real cause instead of
    silently treating every failure as "usage limit."
    """
    try:
        result = subprocess.run(
            ["claude", "-p", "."],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as e:
        raise ProbeError("claude probe timed out") from e
    except FileNotFoundError as e:
        raise ProbeError("claude CLI not found — is Claude Code installed?") from e

    combined = result.stdout + result.stderr
    if any(re.search(p, combined, re.IGNORECASE) for p in USAGE_LIMIT_PATTERNS):
        return False
    if result.returncode != 0:
        snippet = (result.stderr or result.stdout or "").strip().splitlines()
        head = snippet[0] if snippet else f"exit status {result.returncode}"
        raise ProbeError(f"claude -p exited {result.returncode}: {head}")
    return True
