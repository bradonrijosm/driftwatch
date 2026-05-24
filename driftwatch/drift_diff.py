"""Compute and format unified diffs between local and remote config content."""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DiffResult:
    target_name: str
    local_lines: list[str]
    remote_lines: list[str]
    unified_diff: str
    has_diff: bool

    @property
    def line_count(self) -> int:
        """Number of changed/added/removed lines in the diff (excluding headers)."""
        return sum(
            1
            for line in self.unified_diff.splitlines()
            if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))
        )


def _to_lines(content: bytes) -> list[str]:
    """Decode bytes to a list of lines suitable for difflib."""
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'
    return lines


def compute_diff(
    target_name: str,
    local_content: bytes,
    remote_content: bytes,
    context_lines: int = 3,
) -> DiffResult:
    """Return a DiffResult comparing local vs remote content."""
    local_lines = _to_lines(local_content)
    remote_lines = _to_lines(remote_content)

    diff_lines = list(
        difflib.unified_diff(
            local_lines,
            remote_lines,
            fromfile=f"{target_name} (local)",
            tofile=f"{target_name} (remote)",
            n=context_lines,
        )
    )
    unified = ''.join(diff_lines)
    return DiffResult(
        target_name=target_name,
        local_lines=local_lines,
        remote_lines=remote_lines,
        unified_diff=unified,
        has_diff=bool(diff_lines),
    )


def format_diff_report(result: DiffResult, max_lines: Optional[int] = 50) -> str:
    """Return a human-readable string summarising the diff."""
    if not result.has_diff:
        return f"[{result.target_name}] No differences found."

    lines = result.unified_diff.splitlines()
    truncated = False
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True

    body = '\n'.join(lines)
    suffix = f"\n... ({result.line_count} changed lines total, output truncated)" if truncated else ""
    return f"[{result.target_name}] Drift diff ({result.line_count} changed lines):\n{body}{suffix}"
