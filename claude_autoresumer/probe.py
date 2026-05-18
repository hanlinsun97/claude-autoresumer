import subprocess
import re
from datetime import datetime, timezone
from typing import Optional

USAGE_LIMIT_PATTERNS = [
    r"usage limit",
    r"rate.?limit",
    r"quota exceeded",
    r"exceeded.*usage",
    r"plan.*limit",
]

# Claude's usage-limit error includes the reset moment in several observed forms.
# We try each in priority order; the first match wins.
_RESET_PATTERNS = [
    # Pipe-delimited unix epoch seconds: "Claude AI usage limit reached|1735689600"
    re.compile(r"usage limit reached\s*\|\s*(\d{10,13})", re.IGNORECASE),
    # Bare epoch seconds adjacent to the phrase
    re.compile(r"reset\s*(?:at|in)?[^0-9]{0,8}(\d{10,13})", re.IGNORECASE),
    # ISO 8601 timestamp anywhere in the message
    re.compile(r"reset[^0-9]{0,20}(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)",
               re.IGNORECASE),
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


def parse_reset_at(output: str) -> Optional[datetime]:
    """Extract the next usage-reset time from a Claude error message.

    Returns a timezone-aware UTC datetime if a reset moment can be parsed,
    or None if the output doesn't carry one. Callers should fall back to
    polling when this returns None.
    """
    for pattern in _RESET_PATTERNS:
        m = pattern.search(output)
        if not m:
            continue
        raw = m.group(1)
        # Unix epoch (seconds or milliseconds)
        if raw.isdigit():
            ts = int(raw)
            if ts > 10_000_000_000:  # ms precision
                ts = ts // 1000
            try:
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                continue
        # ISO 8601
        iso = raw.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(iso)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return None
