"""CLI script to export the production AI Extractor system prompt for promptfoo evaluations."""

from pathlib import Path

from src.parsing.ai_extractor import SYSTEM_INSTRUCTION


def export_prompt(output_path: Path | None = None) -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    if output_path is None:
        output_path = repo_root / "evals" / "prompts" / "academic_event_extractor.txt"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(SYSTEM_INSTRUCTION, encoding="utf-8")

    # Also mirror to evals/prompt.txt for backwards compatibility with legacy evaluators
    legacy_prompt_path = repo_root / "evals" / "prompt.txt"
    legacy_prompt_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_prompt_path.write_text(SYSTEM_INSTRUCTION, encoding="utf-8")

    print(
        f"Exported system prompt ({len(SYSTEM_INSTRUCTION)} chars) "
        f"to {output_path} and {legacy_prompt_path}"
    )
    return output_path


if __name__ == "__main__":
    export_prompt()
