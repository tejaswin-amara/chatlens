# Graph Report - kind-faraday  (2026-10-23)

## Corpus Check
- 214 files · ~123,515 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 35 file(s) not represented in the graph (top: (none) 19, .example 3, .toml 3)

## Summary
- 2221 nodes · 4394 edges · 159 communities (107 shown, 52 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 278 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7c21d576`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- FakeTelegramClient
- format_day_schedule
- page.tsx
- E2EClient
- test_briefing.py
- test_e2e_remediation.py
- test_tier1_features.py
- test_bot.py
- test_run_daemon.py
- json
- get
- ChatLens Full-System Engineering Audit Report
- test_challenger_m2_m3.py
- KLUERPClient
- test_backend_api.py
- handle_bot_command
- handle_bot_callback
- test_fuzz_parser.py
- backend/main.py
- run_daemon
- MessageDeduplicator
- ChatAnalyzer
- logging.py
- ExtractedAcademicEvent
- client.py
- ChatLens & SPARK PA Assistant
- harness.py
- e2e/conftest.py
- telegram_live.py
- RegexParser
- clock.py
- Path
- sqlite3
- os
- verify_deployment.py
- celery_worker.py
- test_workspace_and_erp.py
- test_tier5_resilience.py
- test_scheduler.py
- TestVerificationScriptErrorPaths
- compilerOptions
- run_ps_supervisor
- load_calendar
- analyzer.py
- typing
- env.py
- Any
- harvest_debt.py
- test_catch_up.py
- AsyncSessionMock
- test_prompt_injection_canaries.py
- benchmark_parser.py
- ChatLens v2.0
- 🛠️ Local Development Setup
- src/main.py
- subprocess
- package.json
- TestHealthcheckFailureDetection
- ADR 0006: Zero Debt, Dialect-Aware Vector Retrieval, and Strict Backend Typing
- parse_telegram_export
- ChatLens v2.0 Design System
- run_mock_server
- test_erp_client_get_marks_session_recovery
- ADR 0002: Data-Instruction Separation & Prompt Injection Defense
- ADR 0003: Read-Only Telegram Ingestion Guardrail
- AGENTS.md — SPARK PA daemon (`src/`)
- dependencies
- manifest.json
- time
- ADR 0001: Adoption of Awesome Dev Pipeline v2.2.0
- ADR 0004: Gemini AI Guardrails and Mandatory Holiday Confirmation
- ADR 0005: ChatLens Full-Stack Architecture, Vector Retrieval, and SPARK Bridge
- ADR 0007: ChatLens Frontend Restoration and Student Portal Isolation
- Verification Matrix
- devDependencies
- Project: KL-Sync System-Wide Verification & Quality Audit
- 🤝 Contributor Covenant Code of Conduct
- isolate_test_environment
- Security Audit Areas
- layout.tsx
- Definition of Done (Addy Osmani agent-skills Alignment)
- Required Format
- firebase.ts
- Required Format
- settings.json
- bug_report.md
- AgentShield Security Specification (ECC v2.2.3 Alignment)
- Workflow
- AsyncSessionMock
- frontend/AGENTS.md
- asyncio
- HTMLTableParser
- generate_embedding
- 2. Phase-by-Phase Implementation Specifications
- Ponytail Ultra Minimalism Rules
- vitest.config.mjs
- Ponytail Ultra Minimalism Rules
- feature_request.md
- pull_request_template.md
- 🛡️ Security Policy
- TEST READY — Remediation Acceptance Test Suite
- Ponytail Ultra Coding Standards (Ponytail v5.1 Alignment)
- TypeScript & Frontend Engineering Rules (ChatLens v2)
- pytest
- get_current_user
- asyncio
- frontend/README.md
- Security Policy
- TypeScript & Frontend Engineering Rules (ChatLens v2)
- KL University ERP Integration (KLU ERP)
- src/config.py
- ADR Scaffolding Workflow (`/adr`)
- test_empirical_erp_concurrency_lock_serialization
- ADR Scaffolding Command (`/adr`)
- SPARK PA Daemon Deployment
- 4. Failure Inventory (Evidence-Backed Defects)
- Project: ChatLens PA Daemon & Telegram Bot Remediation
- workflows/audit.md
- workflows/benchmark.md
- workflows/debt.md
- workflows/eval.md
- workflows/review.md
- workflows/verify.md
- postcss.config.mjs
- sw.js
- commands/audit.md
- commands/benchmark.md
- commands/debt.md
- commands/eval.md
- commands/review.md
- commands/verify.md
- PONYTAIL-DEBT.md
- verify_deployment.sh script
- chatlens
- Test Infrastructure Specification: ChatLens PA Daemon Remediation
- detect_archetype.py
- scripts
- Path
- retry_error_handler
- eslint.config.mjs
- test_debounce_delta_mathematical_precision_sweep

## God Nodes (most connected - your core abstractions)
1. `handle_bot_command()` - 62 edges
2. `E2EClient` - 53 edges
3. `handle_bot_callback()` - 41 edges
4. `run_daemon()` - 37 edges
5. `MessageDeduplicator` - 37 edges
6. `get_connection()` - 36 edges
7. `format_day_schedule()` - 31 edges
8. `KLUERPClient` - 28 edges
9. `FakeTelegramClient` - 28 edges
10. `RegexParser` - 27 edges

## Surprising Connections (you probably didn't know these)
- `Architecture` --references--> `bot_callback_poll()`  [INFERRED]
  PROJECT.md → src/main.py
- `Phase 1: Security Hardening & Authentication Enforcement (P0)` --references--> `get_current_user()`  [INFERRED]
  docs/audits/chatlens-remediation-plan.md → chatlens-v2/backend/firebase_auth.py
- `Dashboard Routes Contract (`src/app/dashboard/*`)` --references--> `timetable()`  [INFERRED]
  chatlens-v2/frontend/PROJECT.md → tests/test_timetable.py
- `Code Layout` --references--> `handle_bot_callback()`  [INFERRED]
  PROJECT.md → src/ingestion/handlers.py
- `Code Layout` --references--> `handle_bot_command()`  [INFERRED]
  PROJECT.md → src/ingestion/handlers.py

## Import Cycles
- None detected.

## Communities (159 total, 52 thin omitted)

### Community 0 - "FakeTelegramClient"
Cohesion: 0.12
Nodes (8): make_clock_mock(), test_debounce_bot_transmission_failure_preserves_prior_timestamp(), test_debounce_corrupted_timestamp_recovery(), test_debounce_first_boot_no_prior_record(), test_debounce_threshold_899_9_seconds_suppressed(), test_debounce_threshold_900_0_exact_boundary_allowed(), test_debounce_threshold_900_1_seconds_allowed(), FakeTelegramClient

### Community 1 - "format_day_schedule"
Cohesion: 0.06
Nodes (41): format_day_schedule(), get_effective_slots(), load(), Meta, parse_periods(), Slot, Timetable, validate() (+33 more)

### Community 2 - "page.tsx"
Cohesion: 0.06
Nodes (68): Home(), AiCard(), AiCardProps, AskBar(), AskBarProps, ChatHeader(), ChatHeaderProps, insightButtons (+60 more)

### Community 3 - "E2EClient"
Cohesion: 0.06
Nodes (28): E2EClient, test_b1_long_uri_handling(), test_b1_malformed_url_percent_encoding(), test_b1_nonexistent_api_route_404(), test_b1_repeated_slashes_normalization(), test_b1_unsupported_http_method(), test_b2_deep_nested_spa_route(), test_b2_missing_static_file_returns_404() (+20 more)

### Community 4 - "test_briefing.py"
Cohesion: 0.24
Nodes (13): build_briefing(), classes_can_skip(), classes_needed(), fetch_briefing_inputs(), guard(), test_build_briefing_attendance(), test_build_briefing_empty(), test_build_briefing_tasks_events_milestones() (+5 more)

### Community 5 - "test_e2e_remediation.py"
Cohesion: 0.05
Nodes (25): test_tier1_fuzzy_command_routing(), test_tier1_inline_callback_query_execution(), test_tier1_standalone_slash_trigger(), test_tier1_startup_debounce_cooldown(), test_tier1_today_command_happy_path(), test_tier1_tomorrow_command_happy_path(), test_tier2_all_periods_cancelled(), test_tier2_debounce_boundary_exact_seconds() (+17 more)

### Community 6 - "test_tier1_features.py"
Cohesion: 0.04
Nodes (25): lint_migrations(), main(), test_f1_api_chats_endpoint_routed(), test_f1_api_healthz_routes_to_backend(), test_f1_caddyfile_routing_contracts(), test_f1_caddyfile_tls_and_encoding(), test_f1_root_request_routes_to_frontend(), test_f1_ws_routing_configuration() (+17 more)

### Community 7 - "test_bot.py"
Cohesion: 0.09
Nodes (26): BotClient, BotConflictError, BotError, BotRateLimitedError, _extract_payload(), mock_bot(), mock_request(), test_bot_400_no_retry() (+18 more)

### Community 8 - "test_run_daemon.py"
Cohesion: 0.09
Nodes (14): run_ps_command(), run_ps_script(), test_healthcheck_fails_when_daemon_stopped(), test_healthcheck_fails_when_database_corrupted(), test_healthcheck_fails_when_heartbeat_missing(), test_healthcheck_passes_when_heartbeat_fresh(), test_healthcheck_passes_with_fresh_startup_notify_ts(), test_healthcheck_selects_most_recent_timestamp() (+6 more)

### Community 9 - "json"
Cohesion: 0.06
Nodes (41): main(), handle_undo_command(), get_connection(), record_write(), CalendarSync, TasksSync, clean_db(), test_create_holiday_event_suppress_reminders() (+33 more)

### Community 10 - "get"
Cohesion: 0.08
Nodes (22): api_analyze(), api_ask(), api_chat_insights(), api_deadlines(), api_global_summarize(), api_monitoring_status(), api_timetable_today(), api_timetable_week() (+14 more)

### Community 11 - "ChatLens Full-System Engineering Audit Report"
Cohesion: 0.12
Nodes (15): 1. Executive Summary, 2. System Architecture & Component Inventory, 3. Baseline Verification Results, 6. Critical User-Journey Verification Matrix, 7.1 Authentication & Authorization Bypass (DEF-04), 7.2 Hardcoded Secrets & PII Scrubbing, 7.3 Prompt Injection Defense, 7. Security and Privacy Review (+7 more)

### Community 12 - "test_challenger_m2_m3.py"
Cohesion: 0.12
Nodes (10): clean_daemon_environment(), run_ps_script(), test_difflib_similarity_ratios_mathematical_oracle(), test_supervisor_healthcheck_corrupt_db(), test_supervisor_healthcheck_healthy_db(), test_supervisor_healthcheck_missing_db(), test_supervisor_status_when_running(), test_supervisor_status_when_stopped() (+2 more)

### Community 13 - "KLUERPClient"
Cohesion: 0.12
Nodes (4): KLUERPClient, test_empirical_erp_session_expiration_markers(), test_erp_client_is_session_expired(), test_erp_client_status_codes_session_expired()

### Community 14 - "test_backend_api.py"
Cohesion: 0.10
Nodes (4): test_api_status_probe_degraded(), test_chats_import_endpoint_and_payload_limits(), test_concurrent_imports_and_duplicate_collision(), test_upload_deduplication_lifecycle()

### Community 15 - "handle_bot_command"
Cohesion: 0.13
Nodes (30): handle_bot_command(), register_handlers(), test_apply_event_calendar_conflict(), test_format_day_schedule_missing_timetable(), test_handle_bot_callback_cmd_attendance(), test_handle_bot_callback_cmd_deadlines(), test_handle_bot_callback_cmd_status(), test_handle_bot_callback_cmd_today() (+22 more)

### Community 16 - "handle_bot_callback"
Cohesion: 0.10
Nodes (17): handle_bot_callback(), RequestRecorder, test_bot_send_custom_buttons_1d(), test_bot_send_custom_buttons_2d(), test_bot_send_default_quick_buttons(), test_bot_send_empty_buttons_suppresses_reply_markup(), test_bot_set_my_commands_exact_registration(), test_callback_answer_failure_resilience() (+9 more)

### Community 17 - "test_fuzz_parser.py"
Cohesion: 0.16
Nodes (15): _parse_datetime(), parse_whatsapp_export(), test_parse_and_save_empty_zip(), test_parse_and_save_valid_nested_zip(), test_parse_and_save_zip_slip_rejection(), test_parse_and_save_zip_without_chat_files(), test_telegram_corrupt_json(), test_telegram_empty_or_non_dict() (+7 more)

### Community 18 - "backend/main.py"
Cohesion: 0.12
Nodes (16): get_db(), api_deadlines_say(), api_telegram_send_code(), api_telegram_verify(), api_timetable_override(), AskRequest, ChatRequest, handle_upload() (+8 more)

### Community 19 - "run_daemon"
Cohesion: 0.22
Nodes (21): bot_callback_poll(), run_daemon(), guard(), mock_valid_settings(), test_bot_callback_poll_no_token_returns_immediately(), test_bot_callback_poll_runs_in_dry_mode(), test_bot_callback_poll_undo_routing(), test_daemon_clean_client_disconnect() (+13 more)

### Community 20 - "MessageDeduplicator"
Cohesion: 0.09
Nodes (7): MessageDeduplicator, setup_test_env(), setup_test_env(), mock_daemon_settings(), test_debounce_evaluation_scenarios(), test_meta_table_crud_and_concurrency(), test_spark_rules_dedupe()

### Community 21 - "ChatAnalyzer"
Cohesion: 0.13
Nodes (4): ChatAnalyzer, _format_messages(), test_analyzer_forbidden_id_redaction(), test_analyzer_format_messages()

### Community 22 - "logging.py"
Cohesion: 0.06
Nodes (16): Ingestion Boundaries, Privacy & Logging Standards, Security & Privacy Rules (ChatLens & SPARK PA), KnowledgeRetriever, configure_logging(), _redact_str(), _scrub_secrets(), _scrub_value() (+8 more)

### Community 23 - "ExtractedAcademicEvent"
Cohesion: 0.17
Nodes (12): AIExtractor, ExtractedAcademicEvent, today_ist(), test_ai_extractor_budget_exhaustion(), test_ai_extractor_clienterror_not_retried(), test_ai_extractor_day_rollover(), test_ai_extractor_empty_response(), test_ai_extractor_media_gate() (+4 more)

### Community 24 - "client.py"
Cohesion: 0.14
Nodes (13): parse_attendance_records(), parse_cgpa_records(), parse_fee_records(), parse_generic_tables(), parse_marks_records(), parse_timetable_records(), test_parse_attendance_metrics(), test_parse_cgpa() (+5 more)

### Community 25 - "ChatLens & SPARK PA Assistant"
Cohesion: 0.07
Nodes (26): 1. System Architecture & Trust Boundaries, 2.1 Ingestion Layer (Telethon Listener), 2.2 Parsing & LLM Layer (Regex & Gemini), 2.3 Workspace Synchronization Layer (Calendar, Tasks, Sheets), 2.4 State & Persistence Layer (SQLite Database), 2.5 Supply Chain & CI/CD Layer, 2. STRIDE Threat Analysis by Component, STRIDE Threat Model: ChatLens & SPARK PA Assistant (+18 more)

### Community 26 - "harness.py"
Cohesion: 0.10
Nodes (6): test_pairwise_backend_upload_to_celery_shared_volume(), test_pairwise_celery_task_update_to_api_poll(), test_pairwise_daemon_sqlite_wal_to_backend_status_bridge(), test_pairwise_frontend_calls_backend_through_proxy(), test_pairwise_migrations_run_before_backend_accepts_traffic(), test_pairwise_proxy_tls_termination_and_upstream_headers()

### Community 27 - "e2e/conftest.py"
Cohesion: 0.10
Nodes (9): compose_config(), e2e_client(), in_memory_db(), isolated_spark_db(), nginx_config(), ComposeParser, NginxConfParser, setup_isolated_spark_db() (+1 more)

### Community 28 - "telegram_live.py"
Cohesion: 0.12
Nodes (11): api_telegram_status(), api_telegram_sync_live(), check_status(), _fetch(), fetch_telegram_chats(), _get_client(), send_code(), send_telegram_code_sync() (+3 more)

### Community 29 - "RegexParser"
Cohesion: 0.16
Nodes (13): RegexParser, test_empirical_regex_parser_room_variations(), test_periods_dashes(), test_room_direction(), test_task_precision(), test_regex_parser_course_mapping_table(), test_regex_parser_holiday_summary_truncation(), test_regex_parser_none_on_unstructured() (+5 more)

### Community 30 - "clock.py"
Cohesion: 0.11
Nodes (15): Invariants & Architecture, Python Engineering Rules (ChatLens & SPARK PA), Runtime & Toolchain, Architecture & Conventions, CLAUDE.md — ChatLens Assistant Guide, Essential Commands, Invariants & Architecture, Python Engineering Rules (ChatLens & SPARK PA) (+7 more)

### Community 32 - "sqlite3"
Cohesion: 0.07
Nodes (16): caddyfile_config(), CaddyfileParser, test_f8_backend_spark_status_bridge(), test_f8_spark_sqlite_integrity_check(), test_f8_spark_sqlite_wal_persistence(), test_alembic_migration_idempotency_sqlite(), test_alembic_migration_preexisting_table(), test_caddyfile_path_matching_api_exact() (+8 more)

### Community 33 - "os"
Cohesion: 0.14
Nodes (7): main(), test_upload_sync_fallback_when_broker_unreachable(), test_chat_statistics_aggregation(), test_telegram_parser_full_export_chats_list(), test_telegram_parser_single_chat(), test_whatsapp_parser_standard(), test_whatsapp_parser_us_format_and_12h()

### Community 34 - "verify_deployment.py"
Cohesion: 0.21
Nodes (7): check_compose_file(), check_env_template(), check_live_endpoints(), check_supporting_configs(), log_info(), log_pass(), main()

### Community 35 - "celery_worker.py"
Cohesion: 0.13
Nodes (7): DummyCelery, generate_embeddings_batch(), parse_and_save_sync(), parse_file_task(), save_messages(), DEF-09: Unbounded Celery File Deletion Preventing Task Retries, test_content_hash_determinism()

### Community 36 - "test_workspace_and_erp.py"
Cohesion: 0.11
Nodes (8): GoogleWorkspaceAuth, SheetsLogger, test_empirical_sheets_logger_silent_degradation(), test_sheets_logger_heartbeat_configured_sheet_id(), test_sheets_logger_heartbeat_empty_sheet_id(), test_sheets_logger_heartbeat_whitespace_sheet_id(), test_sheets_logger_init_preserves_empty_string(), test_sheets_logger_unconfigured_guard_and_skips()

### Community 37 - "test_tier5_resilience.py"
Cohesion: 0.10
Nodes (3): MockHealthHandler, TestLogRotationEnforcement, TestSecretMaskingIntegrity

### Community 38 - "test_scheduler.py"
Cohesion: 0.24
Nodes (11): next_run(), run_briefing(), run_heartbeat(), guard(), test_briefing_idempotent(), test_briefing_retry_on_failure(), test_heartbeat_interval(), test_next_run_after_target() (+3 more)

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 42 - "load_calendar"
Cohesion: 0.39
Nodes (4): AcademicCalendar, get_milestone_date(), load_calendar(), apply_event()

### Community 46 - "env.py"
Cohesion: 0.16
Nodes (7): do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), run_sync_migrations(), Base, Message

### Community 47 - "Any"
Cohesion: 0.21
Nodes (3): CaseInsensitiveHeaderDict, E2EResponse, test_b2_head_request_on_static_asset()

### Community 48 - "harvest_debt.py"
Cohesion: 0.15
Nodes (9): check_adrs(), main(), harvest_debt(), main(), update_debt_file(), main(), scan_motion(), test_adr_compliance() (+1 more)

### Community 49 - "test_catch_up.py"
Cohesion: 0.30
Nodes (12): catch_up_chats(), clean_db(), mock_client(), test_catch_up_7_day_cutoff(), test_catch_up_first_run(), test_catch_up_inaccessible_chat(), test_catch_up_live_message_advances(), test_catch_up_max_keeping_upsert() (+4 more)

### Community 50 - "AsyncSessionMock"
Cohesion: 0.15
Nodes (4): AsyncSessionMock, in_memory_db(), override_async_session_local(), override_get_db()

### Community 51 - "test_prompt_injection_canaries.py"
Cohesion: 0.17
Nodes (11): decide(), Decision, extract(), _get_sender_name(), process_message(), handle_incoming_message(), test_empirical_prompt_injection_canaries_suite(), test_decide_invalid() (+3 more)

### Community 52 - "benchmark_parser.py"
Cohesion: 0.31
Nodes (3): run_parser_benchmark(), run_timetable_benchmark(), main()

### Community 53 - "ChatLens v2.0"
Cohesion: 0.15
Nodes (12): 1. Architecture Overview, 2. Directory Structure, 3. Environment Variables, 4. Setup and Execution, 5. Key REST API Endpoints, Backend (`chatlens-v2/backend/.env`), ChatLens v2.0, Frontend (`chatlens-v2/frontend/.env.local`) (+4 more)

### Community 54 - "🛠️ Local Development Setup"
Cohesion: 0.15
Nodes (12): 📥 1. Fork & Clone, 🔧 2. Configuration, 📦 3. Run External Services, 🐍 4. Backend Setup, ⚛️ 5. Frontend Setup, 🤝 Contributing to ChatLens, ⚛️ Frontend Linting, 🛠️ Local Development Setup (+4 more)

### Community 55 - "src/main.py"
Cohesion: 0.19
Nodes (7): create_telegram_client(), _install_signal_handlers(), _listen(), main(), _sleep_or_stop(), supervise(), test_ask_prompt_fencing()

### Community 56 - "subprocess"
Cohesion: 0.18
Nodes (4): main(), _docker_available(), test_postgres_pgvector_content_hash(), test_status_when_daemon_running()

### Community 57 - "package.json"
Cohesion: 0.17
Nodes (11): name, private, version, react-dom, tailwind-merge, tailwindcss, @tailwindcss/postcss, @types/node (+3 more)

### Community 59 - "ADR 0006: Zero Debt, Dialect-Aware Vector Retrieval, and Strict Backend Typing"
Cohesion: 0.22
Nodes (8): ADR 0006: Zero Debt, Dialect-Aware Vector Retrieval, and Strict Backend Typing, Confirmation & Verification, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Negative Consequences / Tradeoffs, Positive Consequences

### Community 60 - "parse_telegram_export"
Cohesion: 0.18
Nodes (8): _flatten_text(), _parse_message(), parse_telegram_export(), test_telegram_parser_full_account(), test_telegram_parser_single_chat(), test_whatsapp_parser_24h_format(), test_whatsapp_parser_basic(), test_telegram_flatten_text_heterogeneous_structures()

### Community 61 - "ChatLens v2.0 Design System"
Cohesion: 0.18
Nodes (10): 1. Intent, 2. Colors, 3. Typography, 4. Spacing, 5. Motion (motion-anything), 6. Shapes & Borders, 7. Human-Centric Principles, 8. Icons (+2 more)

### Community 63 - "test_erp_client_get_marks_session_recovery"
Cohesion: 0.18
Nodes (7): test_erp_client_fetch_page_session_recovery(), mock_send(), test_erp_client_get_marks_session_recovery(), test_erp_client_login_lock_serialization(), concurrent_login(), fake_login_internal(), test_erp_client_marks_cache_offline_fallback()

### Community 64 - "ADR 0002: Data-Instruction Separation & Prompt Injection Defense"
Cohesion: 0.20
Nodes (9): ADR 0002: Data-Instruction Separation & Prompt Injection Defense, Architecture & Mitigations, Confirmation & Verification, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Negative Consequences / Tradeoffs (+1 more)

### Community 65 - "ADR 0003: Read-Only Telegram Ingestion Guardrail"
Cohesion: 0.20
Nodes (9): ADR 0003: Read-Only Telegram Ingestion Guardrail, Confirmation & Verification, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Implementation Guarantees, Negative Consequences / Tradeoffs (+1 more)

### Community 66 - "AGENTS.md — SPARK PA daemon (`src/`)"
Cohesion: 0.20
Nodes (9): AGENTS.md — SPARK PA daemon (`src/`), Commands, Domain constants (do not regress; `tests/test_spark_rules.py` pins them), Environment variables, Invariants (target behavior; each task prompt says which parts already exist), SQLite state (`SPARK_DB`, default `spark.db`, WAL mode), Style, What this is (+1 more)

### Community 67 - "dependencies"
Cohesion: 0.20
Nodes (10): dependencies, chart.js, clsx, firebase, lucide-react, next, react, react-chartjs-2 (+2 more)

### Community 68 - "manifest.json"
Cohesion: 0.20
Nodes (9): background_color, description, display, icons, name, orientation, short_name, start_url (+1 more)

### Community 69 - "time"
Cohesion: 0.14
Nodes (4): test_background_duplicate_suppression(), test_healthcheck_fails_when_database_missing(), test_healthcheck_fails_when_heartbeat_stale(), test_stop_terminates_running_process()

### Community 70 - "ADR 0001: Adoption of Awesome Dev Pipeline v2.2.0"
Cohesion: 0.22
Nodes (8): ADR 0001: Adoption of Awesome Dev Pipeline v2.2.0, Confirmation & Verification, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Negative Consequences / Tradeoffs, Positive Consequences

### Community 71 - "ADR 0004: Gemini AI Guardrails and Mandatory Holiday Confirmation"
Cohesion: 0.22
Nodes (8): ADR 0004: Gemini AI Guardrails and Mandatory Holiday Confirmation, Confirmation & Verification, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Policy & Behavioral Rules, Positive Consequences

### Community 72 - "ADR 0005: ChatLens Full-Stack Architecture, Vector Retrieval, and SPARK Bridge"
Cohesion: 0.22
Nodes (8): ADR 0005: ChatLens Full-Stack Architecture, Vector Retrieval, and SPARK Bridge, Confirmation & Verification, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Negative Consequences / Tradeoffs, Positive Consequences

### Community 73 - "ADR 0007: ChatLens Frontend Restoration and Student Portal Isolation"
Cohesion: 0.22
Nodes (8): ADR 0007: ChatLens Frontend Restoration and Student Portal Isolation, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Negative Consequences, Positive Consequences, Rationale & Comparison

### Community 74 - "Verification Matrix"
Cohesion: 0.22
Nodes (8): 1. Python Linting & Formatting, 2. Python Type Checking, 3. Python Test Execution, 4. Prompt Drift Verification, 5. Frontend Static Checks & Production Build, 6. Negative Invariant Checks, Complete Pipeline Verification Skill (`verify`), Verification Matrix

### Community 75 - "devDependencies"
Cohesion: 0.22
Nodes (9): devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/node, @types/react, @types/react-dom (+1 more)

### Community 76 - "Project: KL-Sync System-Wide Verification & Quality Audit"
Cohesion: 0.22
Nodes (8): Architecture, Code Layout, Dashboard Routes Contract (`src/app/dashboard/*`), Feature Inventory, Interface Contracts, Milestones, Project: KL-Sync System-Wide Verification & Quality Audit, Quality Baseline Contract

### Community 77 - "🤝 Contributor Covenant Code of Conduct"
Cohesion: 0.22
Nodes (8): 🤝 Contributor Covenant Code of Conduct, 📩 Enforcement, 👮 Enforcement Responsibilities, 📋 Our Pledge, ⚖️ Our Standards, Positive Behaviors, 🌐 Scope, Unacceptable Behaviors

### Community 78 - "isolate_test_environment"
Cohesion: 0.22
Nodes (3): isolate_test_environment(), mock_bot_answer_callback(), mock_bot_send()

### Community 79 - "Security Audit Areas"
Cohesion: 0.25
Nodes (7): 1. Zero Hardcoded Secrets, 2. PII Masking & Privacy Scrubber, 3. SQL Injection Resistance, 4. Adversarial Prompt Injection Defense, 5. Ingress & Egress Invariants, AgentShield Security Scan Skill (`security-scan`), Security Audit Areas

### Community 80 - "layout.tsx"
Cohesion: 0.25
Nodes (4): nextConfig, inter, metadata, next

### Community 81 - "Definition of Done (Addy Osmani agent-skills Alignment)"
Cohesion: 0.29
Nodes (6): 1. Correctness, 2. Code Quality & Minimalism (Ponytail Ultra), 3. Integration & Persistence, 4. Security & Guardrails (AgentShield), 5. Technical Debt & Documentation, Definition of Done (Addy Osmani agent-skills Alignment)

### Community 82 - "Required Format"
Cohesion: 0.29
Nodes (6): 1. Changed, 2. Decisions, 3. Not done, 4. Verification Evidence, Pull Request Workflow (`/pr`), Required Format

### Community 83 - "firebase.ts"
Cohesion: 0.29
Nodes (6): app, auth, db, firebaseConfig, storage, firebase

### Community 84 - "Required Format"
Cohesion: 0.29
Nodes (6): 1. Changed, 2. Decisions, 3. Not done, 4. Verification Evidence, Pull Request Command (`/pr`), Required Format

### Community 85 - "settings.json"
Cohesion: 0.29
Nodes (6): approvedCommands, denyPaths, hooks, PostToolUse, readOnlyPaths, $schema

### Community 86 - "bug_report.md"
Cohesion: 0.29
Nodes (6): 📝 Additional context, 🐛 Describe the bug, 💻 Environment, 🎯 Expected behavior, 📸 Screenshots, 🔄 To Reproduce

### Community 87 - "AgentShield Security Specification (ECC v2.2.3 Alignment)"
Cohesion: 0.33
Nodes (5): 1. Zero Plaintext Secrets, 2. Input Boundaries & Prompt Injection Defense, 3. Telegram Ingress Invariant, 4. Database & Persistence Guardrails, AgentShield Security Specification (ECC v2.2.3 Alignment)

### Community 88 - "Workflow"
Cohesion: 0.33
Nodes (5): 1. Repository Mapping, 2. Systematic Codebase Scan, 3. Reporting Format, Whole-Repo Audit Skill (`audit`), Workflow

### Community 89 - "AsyncSessionMock"
Cohesion: 0.17
Nodes (4): AsyncSessionMock, setup_in_memory_backend_db(), override_async_session_local(), override_get_db()

### Community 90 - "frontend/AGENTS.md"
Cohesion: 0.33
Nodes (4): 📐 Architecture & Principles, 🛠️ Build & Test Commands, 📁 Directory Structure, 🚀 Project Overview

### Community 91 - "asyncio"
Cohesion: 0.22
Nodes (4): test_fuzzy_routing_additional_invalid_commands(), test_fuzzy_routing_rejection_mandate(), test_fuzzy_routing_undo_and_slash_safety(), test_fuzzy_routing_valid_typos_mandate()

### Community 93 - "generate_embedding"
Cohesion: 0.21
Nodes (5): generate_embedding(), generate_embeddings_batch(), _escape_like(), search_messages(), Phase 5: Reliability & Retrieval Enhancements (P2)

### Community 94 - "2. Phase-by-Phase Implementation Specifications"
Cohesion: 0.17
Nodes (10): lifespan(), 1. Prioritization & Sequencing Strategy, 2. Phase-by-Phase Implementation Specifications, 3. End-to-End Verification Matrix, 4. Risks, Dependencies & Rollback Strategy, ChatLens Remediation Plan: Implementation Roadmap, Phase 1: Security Hardening & Authentication Enforcement (P0), Phase 3: Container Orchestration & Healthcheck Repair (P1) (+2 more)

### Community 95 - "Ponytail Ultra Minimalism Rules"
Cohesion: 0.40
Nodes (4): Core Philosophy, Hierarchy of Implementation, Ponytail Ultra Minimalism Rules, Rigor & Hygiene

### Community 97 - "Ponytail Ultra Minimalism Rules"
Cohesion: 0.40
Nodes (4): Core Philosophy, Hierarchy of Implementation, Ponytail Ultra Minimalism Rules, Rigor & Hygiene

### Community 98 - "feature_request.md"
Cohesion: 0.40
Nodes (4): 📝 Additional context, 🔄 Describe alternatives you've considered, 💡 Describe the solution you'd like, 🚀 Is your feature request related to a problem?

### Community 99 - "pull_request_template.md"
Cohesion: 0.40
Nodes (4): Changed, Decisions, Not done, Verification Evidence

### Community 100 - "🛡️ Security Policy"
Cohesion: 0.40
Nodes (4): ⏱️ Our Commitment, 📥 Reporting a Vulnerability, 🛡️ Security Policy, 📅 Supported Versions

### Community 101 - "TEST READY — Remediation Acceptance Test Suite"
Cohesion: 0.40
Nodes (4): Covered Requirements & Acceptance Criteria, Suite Summary, TEST READY — Remediation Acceptance Test Suite, Verification Commands

### Community 102 - "Ponytail Ultra Coding Standards (Ponytail v5.1 Alignment)"
Cohesion: 0.50
Nodes (3): 1. The Ladder of Abstraction, 2. Surgical Modifications & Hygiene, Ponytail Ultra Coding Standards (Ponytail v5.1 Alignment)

### Community 103 - "TypeScript & Frontend Engineering Rules (ChatLens v2)"
Cohesion: 0.50
Nodes (3): Code Standards & Accessibility, Framework & Architecture, TypeScript & Frontend Engineering Rules (ChatLens v2)

### Community 104 - "pytest"
Cohesion: 0.45
Nodes (6): Settings, test_settings_invalid_chat_ids(), test_settings_invalid_chat_ids_non_integer(), test_settings_invalid_mode(), test_settings_missing_live_confirm(), test_settings_valid()

### Community 105 - "get_current_user"
Cohesion: 0.22
Nodes (5): get_current_user(), require_current_user(), 5. Root-Cause Analysis: Confirmed Causes vs. Hypotheses, DEF-04: Zero Authentication Enforcement on All Backend Endpoints, test_firebase_auth_token_validation()

### Community 106 - "asyncio"
Cohesion: 0.24
Nodes (7): test_analyzer_ask_fences_untrusted_transcript(), test_get_task_status(), test_message_to_dict(), test_monitoring_status_endpoint(), test_spark_status_offline(), test_spark_status_online(), test_timetable_and_deadlines_endpoints()

### Community 107 - "frontend/README.md"
Cohesion: 0.50
Nodes (3): Deploy on Vercel, Getting Started, Learn More

### Community 108 - "Security Policy"
Cohesion: 0.50
Nodes (3): Reporting a Vulnerability, Scope, Security Policy

### Community 109 - "TypeScript & Frontend Engineering Rules (ChatLens v2)"
Cohesion: 0.50
Nodes (3): Code Standards & Accessibility, Framework & Architecture, TypeScript & Frontend Engineering Rules (ChatLens v2)

### Community 110 - "KL University ERP Integration (KLU ERP)"
Cohesion: 0.50
Nodes (3): Available Bot Commands, Features, KL University ERP Integration (KLU ERP)

### Community 113 - "test_empirical_erp_concurrency_lock_serialization"
Cohesion: 0.40
Nodes (4): test_empirical_erp_concurrency_lock_serialization(), mock_solve_captcha(), simulated_login_process(), test_empirical_erp_session_expiry_triggers_ocr_reauth()

### Community 117 - "4. Failure Inventory (Evidence-Backed Defects)"
Cohesion: 0.20
Nodes (10): 4. Failure Inventory (Evidence-Backed Defects), DEF-01: Complete Substitution & Deletion of ChatLens UI, DEF-02: Frontend Docker Build & Static Export Deadlock, DEF-03: Reverse Proxy API Interception Deadlock, DEF-05: Backend Container Healthcheck Endpoint Mismatch, DEF-06: Database Credential and Connection String Divergence, DEF-07: Redundant Dual/Triple Migration Execution with Bare Exception Suppression, DEF-08: Asymmetric Vector Retrieval Degradation via Omitted Task Type (+2 more)

### Community 118 - "Project: ChatLens PA Daemon & Telegram Bot Remediation"
Cohesion: 0.20
Nodes (9): Architecture, Code Layout, Feature Inventory, Interface Contracts, Milestones, Project: ChatLens PA Daemon & Telegram Bot Remediation, `src/notify/bot.py` ↔ `src/ingestion/handlers.py` & `src/main.py`, `src/timetable/__init__.py` ↔ `src/ingestion/handlers.py` (+1 more)

### Community 144 - "Test Infrastructure Specification: ChatLens PA Daemon Remediation"
Cohesion: 0.20
Nodes (9): 1. Overview & Architecture, 2. Directory Layout & Artifact Index, 3. Tier Coverage Matrix (`tests/test_e2e_remediation.py`), 4. Execution & Verification Commands, 5. Invariant Gates & Quality Enforcements, Running Specific Tiers, Running the Remediation Acceptance Suite, Static Analysis & Linter Verification (+1 more)

### Community 146 - "scripts"
Cohesion: 0.33
Nodes (6): scripts, build, dev, lint, start, test

### Community 149 - "eslint.config.mjs"
Cohesion: 0.50
Nodes (3): eslintConfig, eslint, eslint-config-next

## Knowledge Gaps
- **8 isolated node(s):** `tailwind-merge`, `@tailwindcss/postcss`, `@types/node`, `@types/react`, `@types/react-dom` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1026 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **52 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `2. Phase-by-Phase Implementation Specifications` connect `2. Phase-by-Phase Implementation Specifications` to `page.tsx`, `generate_embedding`?**
  _High betweenness centrality (0.133) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `handle_bot_command()` (e.g. with `Code Layout` and `1. Overview & Architecture`) actually correct?**
  _`handle_bot_command()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `tailwind-merge`, `@tailwindcss/postcss`, `@types/node` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `FakeTelegramClient` be split into smaller, more focused modules?**
  _Cohesion score 0.11904761904761904 - nodes in this community are weakly interconnected._
- **Why does `Phase 2: Frontend Restoration & Static Export Configuration (P1)` connect `page.tsx` to `2. Phase-by-Phase Implementation Specifications`?**
  _High betweenness centrality (0.130) - this node is a cross-community bridge._
- **Are the 39 inferred relationships involving `E2EClient` (e.g. with `e2e_client()` and `test_f1_api_chats_endpoint_routed()`) actually correct?**
  _`E2EClient` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Should `format_day_schedule` be split into smaller, more focused modules?**
  _Cohesion score 0.057711950970377936 - nodes in this community are weakly interconnected._