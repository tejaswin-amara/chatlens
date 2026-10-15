"""CLI script to export the production AI Extractor system prompt for promptfoo evaluations."""

from pathlib import Path

from src.parsing.ai_extractor import SYSTEM_INSTRUCTION


def export_prompt(output_path: Path | None = None) -> Path:
    if output_path is None:
        repo_root = Path(__file__).resolve().parent.parent
        output_path = repo_root / "evals" / "prompts" / "academic_event_extractor.txt"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(SYSTEM_INSTRUCTION, encoding="utf-8")
    print(f"Exported system prompt ({len(SYSTEM_INSTRUCTION)} chars) to {output_path}")
    return output_path


if __name__ == "__main__":
    export_prompt()
