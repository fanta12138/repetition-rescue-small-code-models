"""Minimal end-to-end check: hit the local vLLM OpenAI API."""
from openai import OpenAI

c = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
r = c.chat.completions.create(
    model="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
    messages=[{"role": "user", "content": "用一句话回答：1+1等于几？"}],
    max_tokens=64,
    temperature=0.0,
)
print("REPLY:", r.choices[0].message.content)
print("USAGE:", r.usage.prompt_tokens, "->", r.usage.completion_tokens)
