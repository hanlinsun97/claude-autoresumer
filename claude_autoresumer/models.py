from __future__ import annotations
import uuid
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    prompt: str
    cwd: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "task"
    status: str = "pending"
    created_at: str = field(default_factory=_now)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    model: str = "claude-sonnet-4-6"
    workspace: str = ""
    source_files: list[str] = field(default_factory=list)
    max_retry_hours: float = 24.0
    error: Optional[str] = None
    session_id: Optional[str] = None
    next_eligible_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Job:
        # Tolerate legacy fields (workflow, self_healing) from older queue.json files.
        d = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**d)


@dataclass
class Queue:
    schema_version: str = "2.0"
    jobs: list[Job] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(
            {"schema_version": self.schema_version, "jobs": [j.to_dict() for j in self.jobs]},
            indent=2,
        )

    @classmethod
    def from_json(cls, raw: str) -> Queue:
        d = json.loads(raw)
        jobs = [Job.from_dict(j) for j in d.get("jobs", [])]
        return cls(schema_version=d.get("schema_version", "2.0"), jobs=jobs)
