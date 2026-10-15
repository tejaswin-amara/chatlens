# AI Evaluation Command (`/eval`)

Execute the evaluation harness for Gemini academic event extraction:

1. **Verify Prompt Sync**:
   ```bash
   uv run pytest -q tests/test_prompt_drift.py
   ```
2. **Export Latest Prompt (if drift detected)**:
   ```bash
   uv run python scripts/export_prompt.py
   ```
3. **Execute Promptfoo Evals**:
   ```bash
   npx promptfoo eval -c evals/promptfooconfig.yaml
   ```
4. **Inspect Assertion Results**:
   - 2 Room overrides
   - 2 Exam deadlines
   - 2 Holidays
   - 2 Non-academic conversations
   - 2 Prompt injection defense tests (PI-01 & PI-02)
