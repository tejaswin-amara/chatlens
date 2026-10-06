# JULES FINAL PROMPT (v3): remediate and improve the SPARK PA daemon and chatlens

Repo: tejaswin-amara/chatlens. Base branch `master` at ca58cd9 (verified 4 Oct 2026; PR #15 and #16 are merged). Timezone IST (Asia/Kolkata). Standards: Awesome Dev Pipeline operational defaults (record every deviation in an ADR) and the agent-config practices curated in hesreallyhim/awesome-claude-code.
If this prompt is too long for the task box, commit it as `JULES_PROMPT.md` and tell Jules: "Follow JULES_PROMPT.md exactly."

## 0. Operating rules
1. Do phases R1 to R10 in order (R4 is the test matrix, delivered together with R2 and R3; R5 is intentionally unused). Open one PR per group: A = R1-R2, B = R3-R4, C = R6, D = R7-R8, E = R9-R10, each branched from the latest `master`. If you can only open one PR, keep one commit per phase.
2. Commits and PR titles use Conventional Commits: `type(scope): subject` with type feat, fix, test, refactor, ci, docs, chore, style or build; imperative, at most 72 characters, body explains why. Delete the stray `commit_msg.txt` in the first commit.
3. Test first. For every defect below, write the failing test, run it and see it fail for the stated reason, then fix it. Quote the one-line failure in the PR.
4. Never weaken an existing assertion. No new runtime dependency (dev or optional extras only where a phase names them). No secrets anywhere. Tests never touch the network, Telegram, Google or Gemini, and nothing makes a network call at import time.
5. Test hygiene: every async test runs through a shared `guard(coro, seconds=5)` helper in `tests/helpers.py` (`asyncio.wait_for`), hand-written fakes instead of `AsyncMock` for objects with sync and async methods, and the suite must pass with `-W error::RuntimeWarning`.
6. Ambiguity: choose the option that writes nothing over one that might write something wrong, and record it under "Decisions". A blocked phase is skipped with the reason under "Not done".
7. Your plan names every file you will touch. Do not edit `data/calendar_2026_27.toml` (read-only, verified against the official PDF), root `requirements.txt` (legacy v1), `_next/`, `docs/`, `index.html`.
8. PR description sections: Changed, Decisions, Not done, Verification (commands and results), MCP usage.
9. Style: Python 3.12, ruff line length 100, smallest diff that works, reuse helpers, comments only where the why is not obvious.

## MCP servers connected to this Jules workspace (standing rules)
Use them and log each call under "MCP usage" (server, tool, purpose, result). MCP is development-time only: no MCP client code, connection string, token or key in any commit, PR, log, fixture or issue. Never read, write or send real chat data. If a tool asks for cost confirmation or would create a paid resource, stop and list it under "Not done".

| Server | Use | Not allowed |
|---|---|---|
| Context7 | MANDATORY before coding against a library: resolve the id and read current docs for Telethon, google-genai, google-api-python-client, tenacity, structlog, pydantic-settings, pytest-asyncio, SQLAlchemy, FastAPI, Flask, pgvector. Say in the PR where the docs changed your approach. | none |
| Linear | One parent issue per phase `R<n>: <title>` (label `spark`, only or first team), status updates, one sub-issue per "Not done" and per owner-only item, final PR links. | editing, closing or deleting existing issues; assigning people; message text in issues |
| Neon | R6 only: validate the v2 migration on a THROWAWAY branch (or throwaway project `chatlens-scratch`), paste statements and results, then delete it. | touching existing branches, projects or data |
| Supabase | Read-only: `search_docs` for pgvector and Postgres syntax; `list_projects` to confirm nothing named chatlens or spark exists. | create_project, apply_migration, execute_sql on existing projects, branches |
| Render | Read-only: list services and logs to confirm NO service runs `src.main` (only one daemon instance may run, otherwise bot 409 conflicts); verify current free-tier terms before any README mention. | create, update or deploy anything |
| Tinybird, Stitch, v0 | Only in optional R10. | everything else |

## 1. Verified state of master (reproduced, not assumed)
Green: `pytest` 28 passed and 1 skipped (29 tests), `ruff check src tests scripts` clean, `mypy src` clean (22 files). `ruff format --check` would reformat 23 files.
Done and correct: baseline PA fixes; parser accuracy (destination room wins, en dash, clock-time ranges, task precision, mid-term, CLASS_CANCELLED); timetable loader and validator; bot client; catch-up; Gemini guardrails (model `gemini-3.5-flash-lite`, no sampling params, budget, ClientError not retried, `SPARK_MEDIA` gate); idempotent task creation; briefing builder; v1 web hardening; v2 duplicate protection in the model; compose ports bound to localhost.

Defects to fix (D-numbers are referenced below):
- D1 `run_daemon` (src/main.py): repeated clean disconnects reconnect with no sleep (17,845 `connect()` calls in 2 s against a fake client). `run_briefing`, `run_heartbeat` and `bot_callback_poll` are re-created on every reconnect and race the listener in one `asyncio.wait(FIRST_COMPLETED)`, so a background crash drops the Telegram connection and each reconnect resets the heartbeat and briefing timers. Cancelled tasks are never awaited. `catch_up_chats` runs before `is_user_authorized()`. Synchronous `bot.send` (urllib, `time.sleep` on 429) is called on the event loop in the exit paths. `run_daemon` cannot be unit-tested (no injection) and has 3 tests.
- D2 `process_message`: `source` is assigned only on the text path. Voice, photo and PDF events raise `UnboundLocalError` and end as `FAILED` in confirm and live modes.
- D3 `timetable.validate` runs for every intent. With a real timetable: HOLIDAY gives NO_SLOT, TASK with no date gives INVALID_DATE, TASK after the term gives OUTSIDE_TERM, so everything becomes NEEDS_REVIEW.
- D4 In live mode with a missing or sample timetable (the shipped `data/timetable_T04.toml` has `sample = true`) a regex ROOM_OVERRIDE is auto-written unvalidated. Required: behave as confirm.
- D5 Bot callbacks: no owner check on `callback_query` (the `/undo` path has one); pending rows are read then updated non-atomically (double tap can apply twice); status is set APPROVED before the write; the edited message says "✅ Action applied" even on failure; no audit row or receipt for confirmed actions; `handle_undo_command` makes blocking Google calls on the event loop.
- D6 The event fingerprint is stored before validation and before the write, and also in dry mode, so a legitimate retry is dropped as DUPLICATE_EVENT for 7 days.
- D7 Fallback dates use naive local `datetime.now()` (6 places in handlers.py): wrong on a UTC host between 18:30 and 24:00 UTC.
- D8 `BotClient`: Markdown `parse_mode` is switched on whenever the text contains `*` or a backtick, including user-derived text (an unbalanced `_` or `*` returns HTTP 400 and the alert is lost); `edit` always uses Markdown; errors are string-typed (`"429:…"`); receipts always go to Saved Messages (silent, no phone notification) even when the bot is configured.
- D9 Config: invalid entries in `SPARK_CHAT_IDS` are silently dropped (a typo shrinks the allowlist); `spark_mode` is a plain `str`; secrets are plain `str`.
- D10 The 🔁 marker is read by `briefing.py` but never written by `calendar_sync` (grep finds `spark_override` only in briefing); the calendar-conflict guard is missing (`academic_calendar.get_milestone_date` is unused); the HOLIDAY title is still doubled ("University Holiday: University Holiday Notice: …").
- D11 Briefing: the retry path uses `text`, which is unbound if the fetch or build failed; data fetching lives in `main.py`; the first heartbeat is written 15 minutes after start.
- D12 Raw `sqlite3.connect()` used as `with` (commits but does not close, so connections leak) in handlers.py, main.py, tasks_sync.py and calendar_sync.py; about 40 lines of apply logic are duplicated between `process_message` and `handle_bot_callback`.
- D13 Only 29 tests. None for timetable, bot, confirm flow, undo, catch-up, scheduler, config, logging privacy.
- D14 Legacy not done: v1 `MessageStore.search` raises `sqlite3.OperationalError` on "what's the budget?", "budget-meeting", "C++ budget", "AND OR NOT" (raw FTS5 MATCH), and filters by chat after LIMIT; `if code == 'already': return True` in both `telegram_live.py` files; v2 upload path uses the raw `file.filename`; v2 `create_all` never adds `content_hash` to an existing `messages` table (UndefinedColumn on upgraded databases), `save_messages` has no empty-list guard or batching (asyncpg parameter limit), and compose has `POSTGRES_DB: ${POSTGRES_DB:-chatlens}_db`, which appends `_db` to any override.
- D15 Pipeline gaps: CI uses unpinned `@v4` actions and `gitleaks-action@v2`, pip instead of uv, no `permissions:` or `concurrency:`, mypy is non-blocking although clean, no `ruff format --check`; `pre-commit` dev dependency unused next to lefthook; lefthook runs the full suite on every commit and has no commit-msg hook; lower bounds are stale (`google-genai>=0.1.1`, locked 2.28.0); no Dependabot, CodeQL, Semgrep, Trivy, Scorecard, SBOM, link check, ADRs, diagrams, Dockerfile, devcontainer or Claude Code config.

## 2. Invariants
1. Telegram is read-only: never send into groups or channels; output goes to the owner through the bot, else Saved Messages.
2. `SPARK_MODE`: `dry` never writes. `confirm` needs ✅ for every write. `live` auto-writes only a regex-sourced, timetable-validated ROOM_OVERRIDE and a regex-sourced TASK or EXAM_DEADLINE. Gemini-derived events (text, voice, photo, PDF), HOLIDAY, CLASS_CANCELLED, and ROOM_OVERRIDE while the timetable is missing or sample always need ✅. A failed validation notifies only (no Apply button).
3. Only chats in `SPARK_CHAT_IDS` are processed; an empty or malformed allowlist refuses to start.
4. No secrets or message text in INFO logs, Sentry or Linear; DEBUG only.
5. All dates are IST. Telegram never changes academic-calendar dates; conflicts are flagged.
6. Exit 0 clean, 2 unrecoverable (config or auth), anything else crash. Never reintroduce Keep, Postgres, Celery or Redis into the daemon.
7. Gemini: model only from `GEMINI_MODEL`, no `temperature`/`top_p`/`top_k`, budgeted, media gated, 4xx never retried.
8. Every write is idempotent and recorded so `/undo` can revert it.

## R1. Supervisor and background jobs (src/main.py) fixes D1
Target structure:
- `run_daemon(*, client=None, stop_event=None, handle_signals=True) -> int` returns the exit code; `main()` ends with `sys.exit(code)`. Config failure, unauthorized session and the five unrecoverable Telethon errors (AuthKeyUnregisteredError, SessionRevokedError, SessionExpiredError, UserDeactivatedError, UserDeactivatedBanError) return 2. Order per cycle: `connect()`, then `is_user_authorized()`, then `catch_up_chats` (failure logged only), then the startup notice (once per process, not per reconnect), then listen.
- Signal setup in `_install_signal_handlers(loop, stop_event)`, tolerant of `NotImplementedError`.
- Every sleep (backoff, FloodWait, clean disconnect) goes through `_sleep_or_stop`, so a stop request interrupts it. A clean disconnect also backs off.
- Briefing, heartbeat and bot polling run as supervised jobs started ONCE before the connection loop, independent of the Telegram connection, and are cancelled and awaited at shutdown. A job that crashes restarts with capped backoff and never drops the listener.
- All blocking calls (`bot.send`, Google, sqlite) go through `asyncio.to_thread`.
```python
BACKOFF_START, BACKOFF_MAX = 2.0, 60.0

async def _sleep_or_stop(stop: asyncio.Event, seconds: float) -> None:
    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout=seconds)

async def _listen(client, stop: asyncio.Event) -> None:
    listen = asyncio.create_task(client.run_until_disconnected())
    waiter = asyncio.create_task(stop.wait())
    try:
        done, _ = await asyncio.wait({listen, waiter}, return_when=asyncio.FIRST_COMPLETED)
        if listen in done:
            listen.result()  # re-raise what ended the connection
    finally:
        for t in (listen, waiter):
            t.cancel()
        await asyncio.gather(listen, waiter, return_exceptions=True)

async def supervise(name: str, job, stop: asyncio.Event) -> None:
    backoff = BACKOFF_START
    while not stop.is_set():
        try:
            await job()
            return  # a job that finishes on its own is done (e.g. bot polling disabled in dry mode)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Background job crashed", job=name, error=str(e), backoff_s=backoff)
            await _sleep_or_stop(stop, backoff)
            backoff = min(backoff * 2, BACKOFF_MAX)
```
Tests (`tests/test_main.py`, `tests/fakeclient.py`, at least 12): config failure, unauthorized start (no catch-up, no listen), mid-run auth errors (two classes) return 2, transient error reconnects then stops with 0, clean disconnect backs off (fewer than 30 connects in 0.2 s with a patched backoff), stop interrupts a 3600 s FloodWait, a crashing job restarts without disconnecting the client, a job that returns is not restarted, shutdown cancels jobs, the startup notice is sent once across reconnects, signal helper registers SIGINT and SIGTERM and tolerates `NotImplementedError`, `main()` exits with the returned code. The fake has no `start()` method.

## R2. Decision logic, validator, callbacks (handlers.py, timetable) fixes D2 to D7, D12
1. Split `process_message` into `extract(client, msg) -> (event, source)`, a pure `decide(mode, source, event, verdict, timetable_ready) -> Decision` (DRY_RUN, REVIEW, CONFIRM, AUTO), and one shared `apply_event(event)` used by AUTO and by the ✅ callback (delete the duplicated block). Initialise `source = "gemini"` for voice, photo and PDF.
2. `decide` implements invariant 2 exactly and is covered by a table-driven test of every mode x source x intent x verdict combination (at least 24 cases).
3. `validate` returns `Verdict(True, "NOT_APPLICABLE")` for every intent except ROOM_OVERRIDE and CLASS_CANCELLED, and never raises on `target_date=None`. Add reason `NO_TIMETABLE` (ok=True) when the timetable is missing or sample; `decide` sends ROOM_OVERRIDE to CONFIRM in that case.
4. A REVIEW decision sends the owner the reason with no Apply button.
5. Mark the message and the event fingerprint only after the decision is persisted (pending row created or write succeeded), never in dry mode, and not after a transient exception, so catch-up can retry. Fingerprint TTL 24 hours.
6. Callbacks: accept only `from.id == OWNER_CHAT_ID`; claim with `UPDATE pending SET status='APPROVED' WHERE id=? AND status='PENDING'` and proceed only if `rowcount == 1`; set APPROVED after success and FAILED otherwise; the edited message reflects the real outcome; write the audit row and a receipt for confirmed actions; `getUpdates` passes `allowed_updates=["callback_query","message"]`.
7. `/undo` and every Google call run in `asyncio.to_thread`. `handle_undo_command` marks `undone=1` only after the revert succeeds.
8. Receipts and alerts go through the bot when `BOT_TOKEN` and `OWNER_CHAT_ID` are set, else Saved Messages.
9. `src/utils/clock.py`: `now_ist()` and `today_ist()` (injectable for tests); replace every naive `datetime.now()` in `src/`.
10. `src/utils/db.py`: one `connect()` returning a `contextlib.closing` connection with `busy_timeout`, and state-store methods on the deduplicator (`add_pending`, `claim_pending`, `finish_pending`, `record_write`, `last_write`, `mark_undone`, `meta_get`, `meta_set`). Remove raw `sqlite3` from handlers.py, main.py, tasks_sync.py, calendar_sync.py and ai_extractor.py.

## R3. Config, bot client, logging, calendar gaps fixes D8 to D11
1. Config: `spark_mode: Literal["dry","confirm","live"]`; an invalid `SPARK_CHAT_IDS` token raises; secrets (`telegram_api_hash`, `telegram_session_string`, `gemini_api_key`, `bot_token`, `google_credentials_base64`) become `SecretStr`; move `allowed_chat_ids` below the fields; keep `.env.example` in sync.
2. Bot: send plain text by default; `parse_mode` is an explicit argument and dynamic text is escaped (HTML mode with `html.escape`); typed exceptions `BotRateLimited(retry_after)`, `BotConflict`, `BotError` replace the string protocol; the bot token never appears in an exception, log line or Sentry event (redaction processor for `bot\d+:[\w-]+` and `AIza[\w-]{35}`); `edit` follows the same rules. Tests: 429 retry, 409 backoff, HTTP error, parse-mode escaping, token redaction.
3. Logging privacy: Sentry `send_default_pii=False` with a `before_send` that drops message text; test that INFO output for a processed message contains no chat title, sender or text.
4. Write the 🔁 marker: `update_class_room` sets `extendedProperties.private.spark_override = "1"`; `writes.prior_json` stores the previous `extendedProperties`; `/undo` sends `{"extendedProperties": {"private": {"spark_override": None}}}` when the marker was absent. Test the exact patch bodies with a fake calendar service.
5. Calendar-conflict guard (invariant 5): for EXAM_DEADLINE and TASK events naming a milestone (fee, re-check, last instruction, detention, mid-term, lab exam, sem-end), compare `target_date` with `academic_calendar.get_milestone_date` for the term containing the message date; on a mismatch audit `CALENDAR_CONFLICT`, tell the owner both dates, create no task; missing calendar file skips the guard with one warning.
6. HOLIDAY title: the parser summary is the first 100 characters of the text without the "University Holiday Notice:" prefix; the calendar adds "University Holiday: " exactly once. Test both layers.
7. Briefing: move the data fetch into `src/briefing.py::fetch_briefing_inputs()`; fix the unbound `text` (build once, retry only the send); a pure `next_run(now)` for 07:00 IST tested across midnight; the double-send guard goes through the state store; write the first heartbeat at start, then every 15 minutes. Extract `classes_can_skip(a, h, floor)` and `classes_needed(a, h, floor)`: classes you can still skip are $\max\!\left(0,\left\lfloor\frac{100a-fh}{f}\right\rfloor\right)$ and classes needed are $\max\!\left(0,\left\lceil\frac{fh-100a}{100-f}\right\rceil\right)$ for floor $f\in\{85,75\}$, in integer arithmetic, with an exhaustive test for $h=1..199$.
8. Dependency bounds: set lower bounds to the versions in `uv.lock`, drop the unused `pre-commit` dev dependency, add `B`, `ASYNC` and `S` to the ruff rules (fix or `# noqa: <rule>  # reason`).

## R4. Test matrix (minimum; total at least 120 tests, under 15 s)
| File | Minimum cases |
|---|---|
| test_decide.py | 24 (mode x source x intent x verdict) |
| test_timetable.py | 14 (Saturday, multi-block, P6 range, clock time, OUTSIDE_TERM, NO_CHANGE, AMBIGUOUS_PERIOD, NOT_APPLICABLE, NO_TIMETABLE, sample treated as missing) |
| test_confirm_flow.py | 9 (approve, ignore, expired, non-owner, double tap applies once, failed write, outcome text, audit row, receipt) |
| test_undo.py | 5 (patch body incl. marker clear, delete event, delete task, nothing to undo, failure keeps undone=0) |
| test_bot.py | 8 |
| test_catch_up.py | 7 (first run, 7-day cutoff, outgoing skipped, max-keeping upsert, truncation warning, inaccessible chat, runs after reconnect) |
| test_ai_extractor.py | 8 more (budget exhaustion and day rollover, retry counts toward budget, redaction cases, no sampling params, ClientError not retried, media gate, empty response) |
| test_calendar_sync.py, test_tasks_sync.py | idempotency, period window, cancel_class, marker, same-title task |
| test_scheduler.py | 5 (next_run, no retroactive send, double-send guard, retry send only, heartbeat tab creation) |
| test_config.py, test_logging_privacy.py | 6 and 3 |
Mutation check before finishing, by hand, recording each in the PR: drop `task.result()`; drop the clean-disconnect backoff; make `decide` return AUTO for gemini; remove the owner check; remove `source = "gemini"` on media; run the validator on HOLIDAY; drop `AND status='PENDING'`; use naive `datetime.now()`. Each must fail a test.

## R6. Legacy fixes fixes D14 (OWASP Cheat Sheet Series applied: injection, upload handling, debug exposure)
1. v1 `chatlens/storage.py`: build the FTS query from word tokens (`re.findall(r"\w+", q)`, each quoted, joined with ` OR `, empty list returns `[]`); add an optional `chat_name` argument applied in SQL and use it in `/api/ask`. Tests: the five strings above do not raise; "budget meeting" still matches; with 40 messages in chat A and 1 in chat B, filtering by B returns the one.
2. Delete `if code == 'already': return True` from both `telegram_live.py` files.
3. v2 upload: store with `Path(file.filename or "upload").name`; return the platform and status, not the server path.
4. v2 migration: `chatlens-v2/backend/migrations/001_content_hash.sql` (`ALTER TABLE messages ADD COLUMN IF NOT EXISTS content_hash TEXT; CREATE UNIQUE INDEX IF NOT EXISTS ux_messages_content_hash ON messages (content_hash);`) applied in the lifespan after `create_all`; `save_messages` returns early on an empty list and inserts in chunks of 1000. Validate the SQL on a throwaway Neon branch with `CREATE EXTENSION IF NOT EXISTS vector`, inserting the same row twice and confirming one row. Add an optional `integration` extra (`testcontainers[postgres]`, `psycopg[binary]`) and a test using `pgvector/pgvector:pg16` that is skipped without Docker.
5. `chatlens-v2/docker-compose.yml`: `POSTGRES_DB: ${POSTGRES_DB:-chatlens_db}`.

## R7. Dev pipeline conformance (Awesome Dev Pipeline defaults)
1. Hooks and toolchain: `lefthook.yml` with pre-commit (`ruff check`, `ruff format --check`, `gitleaks git --pre-commit --staged`, fast tests only), commit-msg (`commitlint lint --message={1}` using the Go tool `conventionalcommit/commitlint`, config `.commitlint.yaml` from `commitlint config create`) and pre-push (full `pytest`, `mypy src`). `mise.toml` pinning Python 3.12, uv, lefthook, gitleaks, node. `.python-version`. One `style:` commit running `ruff format src tests scripts`, then enforce it.
2. CI (`.github/workflows/ci.yml`, `permissions: contents: read`, `concurrency` cancel-in-progress): jobs lint (ruff check and format check), test (`astral-sh/setup-uv`, `uv sync --frozen --extra dev`, `uv run pytest -q -W error::RuntimeWarning`), types (`uv run mypy src`, blocking), commits (lint each PR commit message with commitlint), agent-config (`uvx agnix .` and `npx --yes @ctxlint/ctxlint check`, pinning the current npm version), docs (`lycheeverse/lychee-action` on Markdown).
3. Security workflows: `security.yml` with gitleaks (`gitleaks/gitleaks-action`), Semgrep (`uvx semgrep scan --config p/python --error src scripts`; legacy trees report-only), Trivy filesystem scan (`aquasecurity/trivy-action`, HIGH and CRITICAL, `ignore-unfixed`, blocking for `uv.lock`, report-only for legacy lockfiles); `codeql.yml` (python and javascript-typescript, PR and weekly); `scorecard.yml` (`ossf/scorecard-action`, publish results); `sbom.yml` on tags (`anchore/sbom-action` SPDX artifact, then `anchore/scan-action` Grype failing on high).
4. Pin every third-party Action to a full commit SHA with the version as a trailing comment. Versions at the time of writing: actions/checkout v7.0.1, astral-sh/setup-uv v10.2.0, gitleaks/gitleaks-action v3.0.0, github/codeql-action v4.38.2, aquasecurity/trivy-action v0.36.0, ossf/scorecard-action v2.4.4, anchore/sbom-action v0.24.3, anchore/scan-action v7.4.2, lycheeverse/lychee-action v2.9.0, conventionalcommit/commitlint v0.12.0 (binary). Resolve the commit with `git ls-remote https://github.com/<repo> 'refs/tags/<tag>^{}'` (fall back to `refs/tags/<tag>` for lightweight tags).
5. `.github/dependabot.yml`, weekly with minor and patch grouped: `uv` (root), `github-actions`, `npm` (chatlens-v2/frontend), `pip` (chatlens-v2/backend and root legacy `requirements.txt`), `docker-compose` (chatlens-v2).
6. Containers: multi-stage `Dockerfile` for the daemon (uv, non-root user, no secrets, `SPARK_MODE=dry` default) with `.dockerignore` excluding `.env`, `*.db*`, `*.session`, `token.json`; `compose.yaml` for local dry runs with a named volume for `spark.db`; Trivy image scan in CI (build only, no push); `.devcontainer/devcontainer.json` per the devcontainers spec (Python 3.12, uv, lefthook).
7. Docs: `adr/` at the repo root (not under `docs/`, which is the Pages export) using the joelparkerhenderson template (Title, Status, Context, Decision, Consequences). `adr/0001` records the pipeline mapping: ADOPTED Conventional Commits, commitlint, lefthook, mise, uv, ruff, pytest, testcontainers (v2 only), Dependabot, ADRs, Mermaid, google/eng-practices, OWASP cheat sheets, CodeQL, Semgrep, Gitleaks, Trivy, Scorecard, Syft/Grype, lychee, promptfoo, Sentry, devcontainers; NOT ADOPTED with reason: Renovate (Dependabot chosen), cosign and semantic-release (no released artifacts), OpenTofu/Kubernetes/Argo CD (single VM), Prometheus/Grafana/Loki/Tempo/OTel (disproportionate; Sentry plus Sheet heartbeat), pgbackrest (SQLite `.backup`), Playwright/Cypress (daemon has no UI), k6/Locust (no HTTP service), Schemathesis (v2 API, deferred), Plane (Linear used). Further ADRs: read-only Telethon user client, SQLite state, Gemini model policy, mypy stub overrides, urllib bot client, Keep removal, state-store design, HOLIDAY always confirm. README gets three Mermaid diagrams (architecture, message-flow sequence, mode state machine); `CONTRIBUTING.md` links Conventional Commits and google/eng-practices (small changes, clear descriptions); the PR template adds a pipeline checklist.

## R8. Claude Code layer (awesome-claude-code practices)
1. Keep `AGENTS.md` under about 100 lines (the instruction-budget advice in "Writing a Good CLAUDE.md"): commands via uv, the invariants above, Conventional Commits, ADR-for-deviations, the MCP usage rules. Remove anything an agent would get right without being told.
2. `CLAUDE.md` (under 60 lines): first line `@AGENTS.md`, then only Claude-specific notes (plan before multi-file edits, run `/verify`, never commit `.env`).
3. `.claude/settings.json`: deny Read and Edit for `.env`, `.env.*` (not `.env.example`), `*.session`, `token.json`, `client_secret*.json`, `spark.db*`, `data/private/**`; deny `Bash(git push --force*)`, `Bash(git reset --hard*)`, `Bash(rm -rf*)`; allow `uv run pytest`, `uv run ruff`, `uv run mypy`; a PostToolUse hook for Edit and Write that runs `.claude/hooks/format_python.py`, which reads the tool JSON from stdin and runs `ruff format` and `ruff check --fix` on a changed `.py` file, always exiting 0.
4. `.claude/commands/verify.md` (lint, format check, mypy, tests, summary), `.claude/commands/pr.md` (draft the PR body with Changed, Decisions, Not done, Verification, MCP usage), `.claude/commands/adr.md` (new ADR from the template).
5. Lint the agent config in CI and lefthook with agnix and ctxlint; fix every warning.
6. README "Working with agents": for the owner only, optional tools from the list that are NOT committed: Claude Code Safety Net, TDD Guard. State that anthropics/claude-code-action and claude-code-security-review need a paid `ANTHROPIC_API_KEY` and stay disabled.

## R9. LLM eval harness (promptfoo; not part of pytest)
`evals/promptfooconfig.yaml` with provider `google:gemini-3.5-flash-lite`, cases from `tests/fixtures/sample_circulars.json` plus `tests/fixtures/real_circulars.json` when present, asserting intent, course key and room, pass threshold 90 percent, at most 40 calls per run (free tier). `scripts/export_prompt.py` writes `ai_extractor.SYSTEM_INSTRUCTION` to `evals/prompt.txt`, and a pytest asserts the committed file matches (drift test). `.github/workflows/llm-eval.yml` with `workflow_dispatch` and a weekly cron, secret `GEMINI_API_KEY`, `npx promptfoo@<pinned current version> eval`. Used for every future model migration.

## R10. Optional, design only (Tinybird, Stitch, v0)
Only after R1 to R9 are green. Touch only `observability/` at the repo root: no `src/` change, no deploy, no real data.
1. Tinybird: `observability/tinybird/spark_events.datasource` (ts, day, intent, status, course, source, mode, latency_ms, gemini_calls; no text, sender or chat title) and pipes `daily_intent_counts.pipe`, `failures_7d.pipe`; validate with whichever build or validate tool the MCP offers on a branch or dry run, else mark "not validated".
2. Stitch: one dark responsive "Status" screen (mode badge, last heartbeat, pending confirmations, Gemini budget meter, last 20 audit rows with intent and status only); record the link in `observability/status-page.md`.
3. v0: a React status-card prototype from that design in `observability/status-page/` with static fixtures only.
4. `observability/README.md` describes how the daemon would emit those metrics (no code) and repeats invariant 4.

## Final acceptance
`uv run pytest -q -W error::RuntimeWarning` green with at least 120 tests; `uv run ruff check src tests scripts`, `uv run ruff format --check src tests scripts` and `uv run mypy src` clean; CI green on every PR; `grep -rn "datetime.now()" src` returns nothing; `grep -rn "temperature" src` returns nothing; `git status` shows no `.db`, `.session`, token or `commit_msg.txt`; each defect D1 to D15 is closed or listed under "Not done"; the PR lists every deleted file with the reason and every changed assertion.

## Owner-only (do not attempt)
Credentials and `.env`; running `generate_session.py`; the real `data/timetable_T04.toml` from the official timetable CSV (set `sample = false`); anonymized real circulars in `tests/fixtures/real_circulars.json`; GitHub settings (branch protection, enabling Dependabot alerts, Pages source); installing lefthook, mise and commitlint locally; deleting the stale `test-no-mistakes` branch; switching `SPARK_MODE` from dry.
