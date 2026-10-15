# ADR 0004: Gemini AI Guardrails and Mandatory Holiday Confirmation

* Status: accepted
* Deciders: Autonomous Engineering Team, Academic Integrity Board
* Date: 2026-10-15

## Context and Problem Statement
When academic events are processed by an LLM, hallucinations or misclassifications can carry severe real-world consequences. Specifically:
- Incorrectly declaring a class cancellation or holiday can cause a student to skip an active class, risking academic detention (minimum attendance threshold).
- Fabricating or misdating examination schedules or assignment deadlines can lead to zero credit.
- Legacy Gemini parameters (`temperature`, `top_p`, `top_k`) are deprecated for `gemini-3.x` models and induce non-deterministic reasoning.
- Uncontrolled API calls or retries on 4xx quota errors can quickly exhaust daily budgets.

## Decision Drivers
* Academic fail-safety: Never apply a false holiday or cancellation automatically.
* Cost and quota predictability: Bound daily Gemini API calls.
* Compatibility with modern Google GenAI SDK standards: Use `gemini-3.5-flash-lite`, omit deprecated sampling parameters.

## Considered Options
* Option 1: Fully autonomous application of all extracted events (including holidays and cancellations) in `SPARK_MODE=live`.
* Option 2: Selective autonomous application where only regex-sourced, timetable-validated room overrides and regex tasks are auto-applied; all Gemini extractions, holidays, and cancellations mandate human confirmation.

## Decision Outcome
Chosen option: **Option 2**.

### Policy & Behavioral Rules
1. **Model Specification**: The model name is strictly sourced from `settings.gemini_model`, defaulting to `gemini-3.5-flash-lite`. Legacy `gemini-2.x` defaults and `temperature`, `top_p`, `top_k` sampling overrides are prohibited.
2. **Quota & Rate Limits**: All invocations are tracked against `GEMINI_DAILY_BUDGET`. Client errors (HTTP 4xx, invalid argument, quota exceeded) are never retried.
3. **Mandatory Confirmation**:
   - `HOLIDAY` and `CLASS_CANCELLED` intents always result in `Decision.CONFIRM`, requiring the owner's explicit `✅ Apply` click in the Telegram bot.
   - Any event extracted via Gemini (text, voice, photo, or PDF) always results in `Decision.CONFIRM`.
   - In `SPARK_MODE=live`, automatic calendar execution is strictly limited to regex-sourced, timetable-verified `ROOM_OVERRIDE` events and regex-sourced `TASK`/`EXAM_DEADLINE` events.

### Positive Consequences
* Prevents accidental detention or missed classes due to misparsed rumors or jokes about holidays in student group chats.
* Protects API quota and ensures robust execution.

## Confirmation & Verification
* Automated rule tests in `tests/test_spark_rules.py` and `tests/test_handlers.py`.
* Decision matrix testing covering all combinations of `SPARK_MODE`, extraction source, intent, and timetable verdict.
