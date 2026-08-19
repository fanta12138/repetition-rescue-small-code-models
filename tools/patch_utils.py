"""Extract model outputs into usable artifacts (whole files / unified diffs).

For self-built debug tasks we ask for a WHOLE FILE in a python code block
(more reliable for 3B-7B models). For SWE-bench we will ask for unified diffs.
Extraction failure rate is itself a reported metric (patch format errors).
"""
from __future__ import annotations

import re
from typing import Optional

_CODE_BLOCK_RE = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.DOTALL)
_DIFF_BLOCK_RE = re.compile(r"```(?:diff|patch)?[ \t]*\n(diff --git.*?)```", re.DOTALL)
# v3 multi-file: fenced block annotated with a filename, e.g. ```python core.py
_NAMED_BLOCK_RE = re.compile(
    r"```(?:python|py)?[ \t]+([\w./-]+\.py)[ \t]*\n(.*?)```", re.DOTALL
)


def extract_named_blocks(text: str) -> dict[str, str]:
    """Return {filename: code} from filename-annotated code blocks (v3).

    Accepts ```python name.py fences; falls back to a leading "# name.py"
    comment line inside a plain python block. Later duplicates of the same
    filename win (the model's final version).
    """
    out: dict[str, str] = {}
    if not text:
        return out
    for name, code in _NAMED_BLOCK_RE.findall(text):
        code = code.strip()
        if code:
            out[name] = code + "\n"
    if not out:
        # Fallback: plain block whose first line is a "# name.py" comment.
        header = re.compile(r"^#\s*([\w./-]+\.py)\s*$")
        for code in _CODE_BLOCK_RE.findall(text):
            lines = code.strip().splitlines()
            if lines:
                m = header.match(lines[0].strip())
                if m:
                    body = "\n".join(lines[1:]).strip()
                    if body:
                        out[m.group(1)] = body + "\n"
    return out


def extract_code_block(text: str) -> Optional[str]:
    """Return the longest python code block in the response, or None."""
    if not text:
        return None
    blocks = _CODE_BLOCK_RE.findall(text)
    if blocks:
        code = max(blocks, key=len).strip()
        return code + "\n" if code else None
    # Fallback: the entire response is code (some models skip fences).
    stripped = text.strip()
    if stripped.startswith(("def ", "class ", "import ", "from ")):
        return stripped + "\n"
    return None


def extract_unified_diff(text: str) -> Optional[str]:
    """Return a unified diff (git style) from the response, or None."""
    if not text:
        return None
    blocks = _DIFF_BLOCK_RE.findall(text)
    if blocks:
        return max(blocks, key=len).strip() + "\n"
    if text.strip().startswith("diff --git"):
        return text.strip() + "\n"
    return None
