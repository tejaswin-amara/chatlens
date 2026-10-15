#!/usr/bin/env python3
"""Awesome Dev Pipeline v2.0.0 Motion Accessibility Linter (motion-a11y-audit).

Verifies:
1. globals.css contains `@media (prefers-reduced-motion: reduce)`.
2. `@keyframes` only animate compositor-safe properties (transform, opacity,
   filter, background-position) and flags layout-thrashing properties.
"""

import re
import sys
from pathlib import Path

LAYOUT_THRASHING_PROPERTIES = [
    re.compile(r"\b(top|left|right|bottom)\s*:", re.IGNORECASE),
    re.compile(r"\b(width|height|min-width|min-height|max-width|max-height)\s*:", re.IGNORECASE),
    re.compile(r"\b(margin|margin-\w+|padding|padding-\w+)\s*:", re.IGNORECASE),
]


def scan_motion(frontend_dir: Path) -> list[str]:
    violations = []
    globals_css = frontend_dir / "src" / "app" / "globals.css"

    if not globals_css.exists():
        violations.append(f"globals.css not found at {globals_css}")
        return violations

    css_text = globals_css.read_text(encoding="utf-8")

    # 1. Verify prefers-reduced-motion is defined
    if "prefers-reduced-motion: reduce" not in css_text:
        violations.append(
            "globals.css is missing mandatory '@media (prefers-reduced-motion: reduce)' reset rule"
        )

    # 2. Extract @keyframes blocks and scan for layout properties
    keyframe_blocks = re.findall(
        r"@keyframes\s+([a-zA-Z0-9_-]+)\s*\{([^}]+(?:\{[^}]+\}[^}]*)*)\}", css_text
    )

    for name, body in keyframe_blocks:
        for prop_re in LAYOUT_THRASHING_PROPERTIES:
            match = prop_re.search(body)
            if match:
                violations.append(
                    f"@keyframes '{name}' animates layout-thrashing property '{match.group(1)}'. "
                    "Use transform or opacity instead."
                )

    return violations


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent
    frontend_dir = base_dir / "chatlens-v2" / "frontend"

    violations = scan_motion(frontend_dir)
    if violations:
        print("❌ Motion Accessibility (motion-a11y-audit) Violations Detected:", file=sys.stderr)
        for v in violations:
            print(f"  • {v}", file=sys.stderr)
        return 1

    print("✓ Motion accessibility audit passed: prefers-reduced-motion verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
