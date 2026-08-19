"""Sandboxed test execution.

Security policy (see README):
- Environment variables containing KEY/TOKEN/SECRET/PASSWORD/CREDENTIAL/ACCESS
  are stripped before any model-generated code runs.
- subprocess backend: hard timeout, cwd restricted to the task workdir.
- docker backend: --network none --memory 1g --cpus 1, only the task workdir
  is mounted.
- We only ever run `pytest` on self-built tasks, never arbitrary shell.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_ENV_BLOCKLIST = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "ACCESS")


def _safe_env() -> dict:
    return {
        k: v
        for k, v in os.environ.items()
        if not any(word in k.upper() for word in _ENV_BLOCKLIST)
    }


@dataclass
class SandboxResult:
    passed: bool
    output: str
    returncode: int
    timed_out: bool

    @property
    def status(self) -> str:
        if self.timed_out:
            return "timeout"
        return "passed" if self.passed else "failed"


def run_pytest(
    workdir: str | Path,
    timeout_sec: int = 60,
    backend: str = "subprocess",
    docker_image: str = "python:3.11-slim",
    verbose: bool = False,
) -> SandboxResult:
    """Run test_solution.py in the given workdir under sandbox constraints.

    verbose=True switches -q to -v so per-case PASSED/FAILED names are
    available for structured/contrastive feedback (same oracle, same tests).
    """
    workdir = str(Path(workdir).resolve())
    verbosity = "-v" if verbose else "-q"
    if backend == "subprocess":
        cmd = [
            sys.executable, "-m", "pytest", "test_solution.py",
            verbosity, "--tb=short", "-p", "no:cacheprovider", "--no-header",
        ]
        try:
            proc = subprocess.run(
                cmd, cwd=workdir, capture_output=True, text=True,
                timeout=timeout_sec, env=_safe_env(),
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(False, f"(测试超时，超过 {timeout_sec}s)", -1, True)
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return SandboxResult(proc.returncode == 0, output, proc.returncode, False)

    if backend == "docker":
        cmd = [
            "docker", "run", "--rm",
            "--network", "none", "--memory", "1g", "--cpus", "1",
            "-v", f"{workdir}:/work", "-w", "/work",
            docker_image,
            "python", "-m", "pytest", "test_solution.py",
            verbosity, "--tb=short", "-p", "no:cacheprovider", "--no-header",
        ]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout_sec + 60, env=_safe_env(),
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(False, f"(测试超时，超过 {timeout_sec}s)", -1, True)
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return SandboxResult(proc.returncode == 0, output, proc.returncode, False)

    raise ValueError(f"unknown sandbox backend: {backend}")


def run_script(script_path: str | Path, timeout_sec: int = 30) -> SandboxResult:
    """Run a single python script (used by HumanEval smoke test)."""
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=timeout_sec,
            env=_safe_env(), cwd=str(Path(script_path).parent),
        )
    except subprocess.TimeoutExpired:
        return SandboxResult(False, "(timeout)", -1, True)
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return SandboxResult(proc.returncode == 0, output, proc.returncode, False)
