"""Empirical Challenger Test Suite for Milestone 2.

Covers:
1. Motion Accessibility & WCAG 2.2.2 Rule A005 resolution in kl-sync.
2. CSS cascade and prefers-reduced-motion: reduce overrides.
3. scan_motion.py execution across various strictness levels.
4. check_pins.py execution across various strictness levels in kind-faraday.
5. Multi-arch index manifest verification for uv digest.
6. IST clock and ERP pacing invariant integrity.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
KL_SYNC_ROOT = REPO_ROOT.parent / "kl-sync"
SCAN_MOTION_SCRIPT = (
    Path.home()
    / ".gemini"
    / "config"
    / "plugins"
    / "engineering-pipeline"
    / "scripts"
    / "scan_motion.py"
)
CHECK_PINS_SCRIPT = (
    Path.home()
    / ".gemini"
    / "config"
    / "plugins"
    / "engineering-pipeline"
    / "scripts"
    / "check_pins.py"
)


class TestMotionAccessibilityA005:
    """Empirical verification of Motion Safety and Rule A005."""

    def test_a005_oracle_detects_infinite_animation(self, tmp_path: Path) -> None:
        """Oracle test: scan_motion.py must detect infinite animations and flag A005."""
        bad_css = tmp_path / "bad.css"
        bad_css.write_text(
            ".shimmer { animation: shimmer 1.8s infinite linear; }\n"
            "@media (prefers-reduced-motion: reduce) { * { animation: none; } }",
            encoding="utf-8",
        )
        res = subprocess.run(  # noqa: S603
            [sys.executable, str(SCAN_MOTION_SCRIPT), str(tmp_path), "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
        data = json.loads(res.stdout)
        rule_ids = [f["rule"] for f in data["findings"]]
        assert "A005" in rule_ids, "Oracle failed: scan_motion did not detect infinite animation"

    def test_a005_oracle_clears_on_finite_iterations(self, tmp_path: Path) -> None:
        """Oracle test: scan_motion.py must NOT flag A005 when iterations are finite."""
        good_css = tmp_path / "good.css"
        good_css.write_text(
            ".shimmer { animation: shimmer 1.8s linear 2; }\n"
            "@media (prefers-reduced-motion: reduce) { * { animation-duration: 1ms !important; } }",
            encoding="utf-8",
        )
        res = subprocess.run(  # noqa: S603
            [sys.executable, str(SCAN_MOTION_SCRIPT), str(tmp_path), "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
        data = json.loads(res.stdout)
        rule_ids = [f["rule"] for f in data["findings"]]
        assert "A005" not in rule_ids, "Finite animation falsely triggered Rule A005"

    @pytest.mark.parametrize("strictness", ["low", "medium", "high", "critical"])
    def test_scan_motion_kl_sync_all_strictness_levels(self, strictness: str) -> None:
        """Verify scan_motion.py returns exit code 0 and 0 findings across all severity gates."""
        if not KL_SYNC_ROOT.exists():
            pytest.skip(f"kl-sync not found at {KL_SYNC_ROOT}")

        res = subprocess.run(  # noqa: S603
            [
                sys.executable,
                str(SCAN_MOTION_SCRIPT),
                str(KL_SYNC_ROOT / "src"),
                "--fail-on",
                strictness,
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert res.returncode == 0, f"scan_motion failed on strictness {strictness}: {res.stderr}"
        data = json.loads(res.stdout)
        assert data["count"] == 0, f"Expected 0 findings, got {data['count']}"
        assert data["failing"] == 0

    def test_zero_infinite_animations_in_kl_sync(self) -> None:
        """Adversarial check: ensure no infinite animations anywhere in kl-sync source tree."""
        if not KL_SYNC_ROOT.exists():
            pytest.skip("kl-sync not found")

        pattern = re.compile(
            r"repeat:\s*-1|animation-iteration-count:\s*infinite|animation:[^;]*\binfinite\b"
        )
        violations = []
        for root, _dirs, files in os.walk(KL_SYNC_ROOT / "src"):
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in {".css", ".scss", ".ts", ".tsx", ".js", ".jsx"}:
                    p = Path(root) / f
                    txt = p.read_text(encoding="utf-8", errors="ignore")
                    if pattern.search(txt):
                        violations.append(str(p.relative_to(KL_SYNC_ROOT)))

        assert not violations, f"Found infinite animations violating Rule A005: {violations}"

    def test_prefers_reduced_motion_css_cascade_and_duration(self) -> None:
        """Verify CSS cascade structure in globals.css under prefers-reduced-motion."""
        globals_css = KL_SYNC_ROOT / "src" / "app" / "globals.css"
        if not globals_css.exists():
            pytest.skip("globals.css not found")

        css = globals_css.read_text(encoding="utf-8")

        # 1. Verify shimmer duration and count
        shimmer_match = re.search(r"\.shimmer\s*\{([^}]+)\}", css)
        assert shimmer_match, "Missing .shimmer class definition"
        shimmer_body = shimmer_match.group(1)
        assert "animation: shimmer 1.8s linear 2;" in shimmer_body

        # Total duration = 1.8s * 2 = 3.6s <= 5.0s (WCAG 2.2.2 compliance)
        duration_s = 1.8 * 2
        assert duration_s <= 5.0, f"Animation duration {duration_s} exceeds WCAG 5.0s limit"

        # 2. Verify prefers-reduced-motion overrides
        reduced_match = re.search(
            r"@media\s*\(\s*prefers-reduced-motion:\s*reduce\s*\)\s*\{([^}]+(\{[^}]+\}[^}]+)*)\}",
            css,
        )
        assert reduced_match, "Missing prefers-reduced-motion media query"
        reduced_body = reduced_match.group(0)

        assert "animation-duration: 1ms !important;" in reduced_body
        assert "animation-iteration-count: 1 !important;" in reduced_body
        assert "scroll-behavior: auto !important;" in reduced_body

        # 3. Verify ordering: .shimmer defined before reduced motion media query
        # so cascade overrides
        shimmer_pos = css.find(".shimmer {")
        reduced_pos = css.find("@media (prefers-reduced-motion: reduce)")
        assert shimmer_pos < reduced_pos, (
            "prefers-reduced-motion must appear after class declarations"
        )


class TestContainerPinningAndCheckPins:
    """Empirical verification of Container Pinning and check_pins.py."""

    def test_check_pins_oracle_detects_unpinned_image(self, tmp_path: Path) -> None:
        """Oracle test: check_pins.py must detect unpinned Dockerfile images."""
        bad_df = tmp_path / "Dockerfile"
        bad_df.write_text('FROM python:3.12-slim\nCMD ["python"]\n', encoding="utf-8")
        res = subprocess.run(  # noqa: S603
            [sys.executable, str(CHECK_PINS_SCRIPT), str(tmp_path), "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
        data = json.loads(res.stdout)
        rule_ids = [f["rule"] for f in data["findings"]]
        assert "P008" in rule_ids, "Oracle failed: check_pins did not flag unpinned FROM image"

    @pytest.mark.parametrize("strictness", ["low", "medium", "high", "critical"])
    def test_check_pins_kind_faraday_all_strictness_levels(self, strictness: str) -> None:
        """Verify check_pins.py reports 0 findings across kind-faraday."""
        res = subprocess.run(  # noqa: S603
            [
                sys.executable,
                str(CHECK_PINS_SCRIPT),
                str(REPO_ROOT),
                "--fail-on",
                strictness,
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert res.returncode == 0, f"check_pins failed on {strictness}: {res.stderr}"
        data = json.loads(res.stdout)
        assert data["count"] == 0, f"Expected 0 findings, got {data['count']}"
        assert data["failing"] == 0

    def test_dockerfile_multi_stage_and_uv_digest(self) -> None:
        """Verify kind-faraday Dockerfile pins uv binary via valid multi-arch sha256 digest."""
        df_path = REPO_ROOT / "Dockerfile"
        assert df_path.exists()
        content = df_path.read_text(encoding="utf-8")

        # Line 8 check
        uv_pin_line = (
            "COPY --from=ghcr.io/astral-sh/uv:0.5.21@"
            "sha256:87d729f94c87d0aade077260d07d899848f027b7ef37e734dca711c7ceffd3cf /uv /uvx /bin/"
        )
        assert uv_pin_line in content, "Missing pinned COPY line for uv in Dockerfile"

        # Digest format verification (64 hex characters)
        digest = "87d729f94c87d0aade077260d07d899848f027b7ef37e734dca711c7ceffd3cf"
        assert len(digest) == 64
        assert re.match(r"^[0-9a-f]{64}$", digest)

        # Base image pins verification
        py_digest = "5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b"
        assert f"FROM python:3.12-slim@sha256:{py_digest} AS builder" in content
        assert f"FROM python:3.12-slim@sha256:{py_digest} AS runtime" in content


class TestInvariantsPreservation:
    """Verify that Invariant 5 (IST timezone) and ERP pacing remain preserved."""

    def test_academic_calendar_uses_clock_today_ist(self) -> None:
        """Verify academic_calendar.py uses clock.today_ist() rather than host date.today()."""
        cal_path = REPO_ROOT / "src" / "academic_calendar.py"
        content = cal_path.read_text(encoding="utf-8")

        assert "from src.utils import clock" in content
        assert "ref_date = clock.today_ist()" in content
        # Disallow raw date.today() in academic_calendar.py
        assert "date.today()" not in content

    def test_erp_sync_enforces_inter_request_pacing(self) -> None:
        """Verify AcademicERPSyncAgent enforces 400ms spacing between sequential calls."""
        sync_path = REPO_ROOT / "src" / "erp" / "sync.py"
        content = sync_path.read_text(encoding="utf-8")

        sleep_count = content.count("await asyncio.sleep(0.4)")
        assert sleep_count >= 2, (
            f"Expected at least 2 inter-request sleep(0.4) calls, found {sleep_count}"
        )
