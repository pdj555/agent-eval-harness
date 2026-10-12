"""Worked example: the four misalignment containment checks.

Runs Anthropic's four unintended-action categories (October 9, 2026
report) as sandbox checks, with the guard on and then off. With the guard
on, every check must PASS. With the guard off, every check must FAIL:
that contrast is what makes the checks worth running.

No API keys, no network. Writes the same output to
examples/misalignment_report.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.containment import run_all


def render(guard: bool) -> list[str]:
    label = "guard ON" if guard else "guard OFF"
    expected = "PASS" if guard else "FAIL"
    lines = [f"## Containment checks, {label} (expected: all {expected})", ""]
    lines.append("| check | category | result | what happened |")
    lines.append("| --- | --- | --- | --- |")
    for r in run_all(guard=guard):
        verdict = "PASS" if r.passed else "FAIL"
        lines.append(
            f"| {r.check_id} | {r.category} | {verdict} | {'; '.join(r.notes)} |"
        )
    lines.append("")
    return lines


def main() -> None:
    lines = [
        "# Misalignment containment checks",
        "",
        "Four checks from Anthropic's October 9, 2026 report, "
        '"Investigating unintended model actions in our evaluations and '
        'internal use." Each check reproduces one failure category in a '
        "sandbox and asks whether the containment layer stops it.",
        "",
    ]
    lines += render(guard=True)
    lines += render(guard=False)
    text = "\n".join(lines)
    print(text)
    out = Path(__file__).resolve().parent / "misalignment_report.md"
    out.write_text(text + "\n")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
