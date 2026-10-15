"""Tests to ensure promptfoo evaluation prompt matches production SYSTEM_INSTRUCTION."""

from pathlib import Path

from src.parsing.ai_extractor import SYSTEM_INSTRUCTION


def test_prompt_no_drift() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    prompt_file = repo_root / "evals" / "prompts" / "academic_event_extractor.txt"
    assert prompt_file.exists(), (
        f"Prompt file {prompt_file} does not exist. Run scripts/export_prompt.py to generate it."
    )
    exported_content = prompt_file.read_text(encoding="utf-8")
    assert exported_content == SYSTEM_INSTRUCTION, (
        "Prompt drift detected! Production SYSTEM_INSTRUCTION in src.parsing.ai_extractor "
        "does not match evals/prompts/academic_event_extractor.txt. "
        "Run `python scripts/export_prompt.py` to sync."
    )
