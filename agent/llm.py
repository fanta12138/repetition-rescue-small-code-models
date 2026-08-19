"""OpenAI-compatible LLM client wrapper (targets vLLM serve endpoint).

Tracks token usage and wall time per call; supports vLLM guided decoding
(JSON-schema constrained generation) which is critical for stabilizing
tool-call / patch-format output of small models.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

from openai import OpenAI


@dataclass
class LLMResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    wall_time: float
    raw: Any = None

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMClient:
    """Thin wrapper over an OpenAI-compatible chat endpoint (vLLM)."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        seed: Optional[int] = None,
    ) -> None:
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.seed = seed

    def generate(
        self,
        messages: list[dict],
        guided_json: Optional[dict] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = dict(
            model=self.model,
            messages=messages,
            temperature=self.temperature if temperature is None else temperature,
            max_tokens=self.max_tokens if max_tokens is None else max_tokens,
        )
        if self.seed is not None:
            # vLLM honors seed for reproducible sampling across replicates.
            kwargs["seed"] = self.seed
        if guided_json is not None:
            # vLLM guided decoding: forces schema-conformant output, greatly
            # reducing format failures for 3B-7B models.
            kwargs["extra_body"] = {"guided_json": guided_json}
        t0 = time.time()
        resp = self.client.chat.completions.create(**kwargs)
        wall = time.time() - t0
        usage = resp.usage
        return LLMResponse(
            text=resp.choices[0].message.content or "",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            wall_time=wall,
            raw=resp,
        )
