# Python Engineering Rules (ChatLens & SPARK PA)

## Runtime & Toolchain
- **Runtime**: Python 3.12 exclusively. Package manager: `uv`.
- **Linter & Formatter**: `ruff` with line length 100.
- **Type Checker**: `mypy` with full type annotations. No untyped public functions.
- **Test Runner**: `pytest` running with `-W error::RuntimeWarning` to immediately fail on unawaited coroutines or event loop resource leaks.

## Invariants & Architecture
- **Timezone Awareness**: All timestamps MUST use `src.utils.clock` (`clock.now_ist()` or `clock.today_ist()`). Never call raw `datetime.now()` or `date.today()`.
- **Async Execution**: Every async test must use `guard(coro, seconds=5.0)` to eliminate hanging tests.
- **Database Access**: SQLite WAL mode only (`spark.db`). Parameterized SQL only (`?`); zero dynamic SQL concatenation.
- **Gemini AI Extraction**: Default model `gemini-3.5-flash-lite`. Never pass deprecated sampling parameters (`temperature`, `top_p`, `top_k`). Enforce `GEMINI_DAILY_BUDGET`.
- **Exit Codes**: `0` = clean shutdown; `2` = unrecoverable config or auth error; other non-zero = crash.
