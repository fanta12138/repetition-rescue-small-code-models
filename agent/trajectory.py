"""Trajectory JSONL logger.

Schema (fixed at project start; extend only by appending new optional fields):
    instance_id, step, role, prompt_tokens, completion_tokens, wall_time,
    tool_call, test_result, patch_applied, error_type

Every experiment arm writes one trajectories.jsonl; all downstream failure
analysis and trajectory replay depends on this file being complete.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

SCHEMA_FIELDS = [
    "instance_id",
    "step",
    "role",            # coder | executor | critic | controller
    "prompt_tokens",
    "completion_tokens",
    "wall_time",
    "tool_call",       # e.g. "run_pytest", "apply_code"
    "test_result",     # "passed" | "failed" | "error" | "timeout" | None
    "patch_applied",   # bool: did we successfully extract & write new code
    "error_type",      # failure taxonomy label, see analysis/failure_taxonomy.md
]


class TrajectoryLogger:
    """Append-only JSONL writer, one instance per log() call."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a", encoding="utf-8")

    def log(
        self,
        instance_id: str,
        step: int,
        role: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        wall_time: float = 0.0,
        tool_call: Optional[str] = None,
        test_result: Optional[str] = None,
        patch_applied: Optional[bool] = None,
        error_type: Optional[str] = None,
        **extra: Any,
    ) -> None:
        record = {
            "instance_id": instance_id,
            "step": step,
            "role": role,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "wall_time": wall_time,
            "tool_call": tool_call,
            "test_result": test_result,
            "patch_applied": patch_applied,
            "error_type": error_type,
        }
        # Extra context for human reading (prompt/response excerpts). Keep it
        # truncated so trajectory files stay manageable.
        if extra:
            record["extra"] = {k: _truncate(v) for k, v in extra.items()}
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> "TrajectoryLogger":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _truncate(value: Any, max_chars: int = 4000) -> Any:
    if isinstance(value, str) and len(value) > max_chars:
        return value[: max_chars // 2] + "\n...[truncated]...\n" + value[-max_chars // 2:]
    return value
