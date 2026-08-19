"""Test-driven repair loop state machine.

States per attempt:
    build_prompt -> llm_generate -> extract_code -> run_tests ->
        {passed: stop | failed: build_feedback -> next attempt}

Modes (E0 arms):
    direct            : single attempt, no feedback (baseline a)
    repair            : full reflection with compressed pytest feedback (arm b)
    random_reflection : control -- feedback replaced by non-diagnostic text (c)
    no_feedback       : only "tests failed", no diagnostic info (d)

Comparing (b) vs (c) vs (d) answers the central question: does the gain come
from *informative feedback* rather than from extra attempts alone?
"""
from __future__ import annotations

import random
import tempfile
import time
from pathlib import Path
from typing import Optional

from agent.feedback import (
    DIVERSITY_NUDGE,
    NO_FEEDBACK_TEXT,
    RANDOM_FEEDBACKS,
    WEAK_NUDGE,
    compress_test_output,
    contrastive_feedback,
    structured_feedback,
)
from agent.llm import LLMClient
from agent.prompts import (
    build_direct_messages,
    build_multifile_repair_messages,
    build_repair_messages,
)
from agent.trajectory import TrajectoryLogger
from tools.patch_utils import extract_code_block, extract_named_blocks
from tools.sandbox import run_pytest

MODES = (
    "direct",
    "repair",
    "random_reflection",
    "no_feedback",
    # E1 actionable-feedback arms: same loop, same budget, same first-attempt
    # prompt as `repair`; only the feedback formatting differs.
    "repair_structured",
    "repair_contrast",
    # E3 lock-breaking arms: identical to repair_structured until the model
    # repeats its previous candidate verbatim; then the intervention fires
    # (instruction nudge vs sampling-temperature bump).
    "repair_diverse",
    "repair_tempbump",
    # E4 ablation: weak nudge (repetition awareness + generic retry).
    "repair_nudge_weak",
)

# Arms built on the structured feedback format (run pytest -v).
_STRUCTURED_ARMS = ("repair_structured", "repair_contrast",
                    "repair_diverse", "repair_tempbump", "repair_nudge_weak")
# E3: temperature used for the attempt right after a verbatim repetition.
TEMPBUMP_TEMPERATURE = 0.9


class RepairLoop:
    def __init__(self, cfg: dict, llm: LLMClient, logger: TrajectoryLogger) -> None:
        self.cfg = cfg
        self.llm = llm
        self.logger = logger
        self.budget = cfg["budget"]
        self.sandbox_cfg = cfg.get("sandbox", {})

    def run(self, task: dict, mode: str) -> dict:
        """Run one task under one mode; return per-instance metrics."""
        assert mode in MODES, f"unknown mode: {mode}"
        if "files" in task:
            return self._run_multifile(task, mode)
        return self._run_single(task, mode)

    def _build_feedback(self, mode: str, output: str, feedback_chars: int,
                        repetition: bool = False) -> Optional[str]:
        if mode == "repair":
            return compress_test_output(output, feedback_chars)
        if mode == "repair_structured" or mode == "repair_tempbump":
            return structured_feedback(output, feedback_chars)
        if mode == "repair_diverse":
            fb = structured_feedback(output, feedback_chars)
            if repetition:
                # E3 intervention: nudge only after a verbatim repeat failed.
                return DIVERSITY_NUDGE + "\n\n" + fb
            return fb
        if mode == "repair_nudge_weak":
            fb = structured_feedback(output, feedback_chars)
            if repetition:
                # E4 ablation control: same observation, generic directive.
                return WEAK_NUDGE + "\n\n" + fb
            return fb
        if mode == "repair_contrast":
            return contrastive_feedback(output, feedback_chars)
        if mode == "no_feedback":
            return NO_FEEDBACK_TEXT
        if mode == "random_reflection":
            return random.choice(RANDOM_FEEDBACKS)
        return None

    def _run_multifile(self, task: dict, mode: str) -> dict:
        """v3 multi-file tasks: model must localize which file has the bug."""
        max_iter = 1 if mode == "direct" else self.budget["max_iterations"]
        token_budget = self.budget["max_tokens_per_instance"]
        feedback_chars = self.budget.get("feedback_max_chars", 6000)

        instance_id = task["task_id"]
        files = dict(task["files"])
        bug_file = task["bug_file"]
        workdir = Path(tempfile.mkdtemp(prefix=f"v3_{instance_id}_{mode}_"))
        for name, content in files.items():
            (workdir / name).write_text(content, encoding="utf-8")
        (workdir / "test_solution.py").write_text(task["test_code"], encoding="utf-8")

        t_start = time.time()
        step = 0
        tokens_used = 0
        prompt_tokens = completion_tokens = 0
        extract_failures = 0
        llm_calls = 0
        success = False
        feedback: Optional[str] = None
        error_type: Optional[str] = None
        files_changed: set[str] = set()
        # E3 lock-breaking state: repetition = previous candidate was a
        # verbatim repeat that still failed; drives the intervention.
        prev_candidate = None
        repetition = False
        repetition_events = 0
        interventions = 0

        for attempt in range(1, max_iter + 1):
            if tokens_used > token_budget:
                error_type = "budget_exceeded"
                break

            messages = build_multifile_repair_messages(
                task["description"], files, feedback, attempt
            )
            temp = (TEMPBUMP_TEMPERATURE
                    if mode == "repair_tempbump" and repetition else None)
            resp = self.llm.generate(messages, temperature=temp)
            llm_calls += 1
            tokens_used += resp.total_tokens
            prompt_tokens += resp.prompt_tokens
            completion_tokens += resp.completion_tokens
            step += 1

            # Apply only blocks whose filename matches a known project file;
            # hallucinated filenames are ignored (counted as failures only if
            # nothing valid was produced).
            named = extract_named_blocks(resp.text)
            valid = {n: c for n, c in named.items() if n in files and n != "test_solution.py"}
            patch_applied = bool(valid)
            candidate = tuple(sorted(valid.items())) if valid else resp.text
            repetition = prev_candidate is not None and candidate == prev_candidate
            if repetition:
                repetition_events += 1
                if mode in ("repair_diverse", "repair_tempbump",
                            "repair_nudge_weak"):
                    interventions += 1
            prev_candidate = candidate
            if patch_applied:
                files.update(valid)
                files_changed.update(valid)
                for name, content in valid.items():
                    (workdir / name).write_text(content, encoding="utf-8")
            else:
                extract_failures += 1
            self.logger.log(
                instance_id=instance_id, step=step, role="coder",
                prompt_tokens=resp.prompt_tokens,
                completion_tokens=resp.completion_tokens,
                wall_time=resp.wall_time,
                patch_applied=patch_applied,
                error_type=None if patch_applied else "extract_failed",
                response_excerpt=resp.text[:2000],
                extra_files=list(valid.keys()),
            )

            result = run_pytest(
                workdir,
                timeout_sec=self.sandbox_cfg.get("timeout_sec", 60),
                backend=self.sandbox_cfg.get("backend", "subprocess"),
                docker_image=self.sandbox_cfg.get("docker_image", "python:3.11-slim"),
                verbose=mode in _STRUCTURED_ARMS,
            )
            step += 1
            self.logger.log(
                instance_id=instance_id, step=step, role="executor",
                tool_call="run_pytest", test_result=result.status,
            )
            if result.passed:
                success = True
                break

            feedback = self._build_feedback(
                mode, result.output, feedback_chars, repetition=repetition
            )
            if mode == "direct":
                break

        if not success and error_type is None and extract_failures > 0:
            error_type = "extract_failed"

        return {
            "instance_id": instance_id,
            "mode": mode,
            "success": success,
            "iterations": llm_calls,
            "llm_calls": llm_calls,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "wall_time": time.time() - t_start,
            "patch_applied_count": llm_calls - extract_failures,
            "extract_failures": extract_failures,
            "error_type": error_type,
            # v3 localization metrics
            "files_changed": sorted(files_changed),
            "n_files_changed": len(files_changed),
            "localized_bug_file": bug_file in files_changed,
            # E3 lock-breaking metrics
            "repetition_events": repetition_events,
            "interventions": interventions,
        }

    def _install_candidate(self, task: dict, new_code: str) -> str:
        """Hook: transform an extracted candidate before installation and
        repetition comparison. Default is identity; the HumanEval adapter
        (E8) overrides this with the frozen signature-prepend guard."""
        return new_code

    def _run_single(self, task: dict, mode: str) -> dict:
        """Run one single-file task under one mode (v1/v2)."""
        max_iter = 1 if mode == "direct" else self.budget["max_iterations"]
        token_budget = self.budget["max_tokens_per_instance"]
        feedback_chars = self.budget.get("feedback_max_chars", 6000)

        instance_id = task["task_id"]
        solution = task["buggy_code"]
        workdir = Path(tempfile.mkdtemp(prefix=f"e0_{instance_id}_{mode}_"))
        (workdir / "test_solution.py").write_text(task["test_code"], encoding="utf-8")

        t_start = time.time()
        step = 0
        tokens_used = 0
        prompt_tokens = completion_tokens = 0
        extract_failures = 0
        llm_calls = 0
        success = False
        feedback: Optional[str] = None
        error_type: Optional[str] = None
        # E3 lock-breaking state (see _run_multifile).
        prev_candidate = None
        repetition = False
        repetition_events = 0
        interventions = 0

        for attempt in range(1, max_iter + 1):
            if tokens_used > token_budget:
                error_type = "budget_exceeded"
                break

            # 1) generate a candidate fix
            if mode == "direct":
                messages = build_direct_messages(task["description"], solution)
            else:
                messages = build_repair_messages(
                    task["description"], solution, feedback, attempt
                )
            temp = (TEMPBUMP_TEMPERATURE
                    if mode == "repair_tempbump" and repetition else None)
            resp = self.llm.generate(messages, temperature=temp)
            llm_calls += 1
            tokens_used += resp.total_tokens
            prompt_tokens += resp.prompt_tokens
            completion_tokens += resp.completion_tokens
            step += 1

            # 2) extract & apply
            new_code = extract_code_block(resp.text)
            patch_applied = new_code is not None
            if patch_applied:
                new_code = self._install_candidate(task, new_code)
            candidate = new_code if new_code is not None else resp.text
            repetition = prev_candidate is not None and candidate == prev_candidate
            if repetition:
                repetition_events += 1
                if mode in ("repair_diverse", "repair_tempbump",
                            "repair_nudge_weak"):
                    interventions += 1
            prev_candidate = candidate
            if patch_applied:
                solution = new_code
            else:
                extract_failures += 1
            (workdir / "solution.py").write_text(solution, encoding="utf-8")
            self.logger.log(
                instance_id=instance_id, step=step, role="coder",
                prompt_tokens=resp.prompt_tokens,
                completion_tokens=resp.completion_tokens,
                wall_time=resp.wall_time,
                patch_applied=patch_applied,
                error_type=None if patch_applied else "extract_failed",
                response_excerpt=resp.text[:2000],
            )

            # 3) execute tests in sandbox
            result = run_pytest(
                workdir,
                timeout_sec=self.sandbox_cfg.get("timeout_sec", 60),
                backend=self.sandbox_cfg.get("backend", "subprocess"),
                docker_image=self.sandbox_cfg.get("docker_image", "python:3.11-slim"),
                verbose=mode in _STRUCTURED_ARMS,
            )
            step += 1
            self.logger.log(
                instance_id=instance_id, step=step, role="executor",
                tool_call="run_pytest", test_result=result.status,
            )
            if result.passed:
                success = True
                break

            # 4) build feedback for the next attempt (mode-dependent)
            feedback = self._build_feedback(
                mode, result.output, feedback_chars, repetition=repetition
            )
            if mode == "direct":
                break

        if not success and error_type is None and extract_failures > 0:
            error_type = "extract_failed"

        return {
            "instance_id": instance_id,
            "mode": mode,
            "success": success,
            "iterations": llm_calls,
            "llm_calls": llm_calls,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "wall_time": time.time() - t_start,
            "patch_applied_count": llm_calls - extract_failures,
            "extract_failures": extract_failures,
            "error_type": error_type,
            # E3 lock-breaking metrics
            "repetition_events": repetition_events,
            "interventions": interventions,
        }
