"""Repo-level context selection (minimal for week 1-2; retrieval module comes week 3).

For SWE-bench instances the agent needs code context under a strict token
budget. This module provides deterministic building blocks: file reading with
char budget and simple keyword grep. The embedding/BM25 retriever will build
on top of these primitives.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".tox", "venv", ".venv"}
_MAX_FILE_BYTES = 500_000


def read_file(path: str | Path, max_chars: int = 8000) -> str:
    """Read a file with a char budget (head kept, tail marker appended)."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return f"(无法读取文件: {p})"
    if len(text) > max_chars:
        return text[:max_chars] + f"\n...[文件过长，已截断，共 {len(text)} 字符]..."
    return text


def grep_repo(
    root: str | Path,
    pattern: str,
    max_results: int = 20,
    file_suffixes: tuple = (".py",),
) -> list[dict]:
    """Naive keyword search over a repo. Returns {file, line, text} matches."""
    root = Path(root)
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error:
        rx = re.compile(re.escape(pattern), re.IGNORECASE)
    matches: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(file_suffixes):
                continue
            fp = Path(dirpath) / fn
            try:
                if fp.stat().st_size > _MAX_FILE_BYTES:
                    continue
                for lineno, line in enumerate(
                    fp.read_text(encoding="utf-8", errors="replace").splitlines(), 1
                ):
                    if rx.search(line):
                        matches.append(
                            {
                                "file": str(fp.relative_to(root)),
                                "line": lineno,
                                "text": line.strip()[:200],
                            }
                        )
                        if len(matches) >= max_results:
                            return matches
            except OSError:
                continue
    return matches
