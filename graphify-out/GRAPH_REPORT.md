# Graph Report - kind-faraday  (2026-10-23)

## Corpus Check
- 213 files · ~122,368 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 36 file(s) not represented in the graph (top: (none) 19, .example 3, .toml 3)

## Summary
- 2207 nodes · 4413 edges · 143 communities (97 shown, 46 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 312 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a1952e4b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- run_daemon
- format_day_schedule
- page.tsx
- E2EClient
- pytest
- test_e2e_remediation.py
- test_tier1_features.py
- test_bot.py
- test_run_daemon.py
- json
- get
- 4. Failure Inventory (Evidence-Backed Defects)
- test_challenger_m2_m3.py
- KLUERPClient
- test_backend_api.py
- handle_bot_command
- CalendarSync
- test_fuzz_parser.py
- backend/main.py
- test_today_and_tomorrow_bot_commands_simultaneously
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
- datetime
- celery_worker.py
- test_workspace_and_erp.py
- test_tier5_resilience.py
- MessageList.tsx
- TestVerificationScriptErrorPaths
- compilerOptions
- run_ps_supervisor
- handlers.py
- typing
- KnowledgeRetriever
- env.py
- components.test.tsx
- harvest_debt.py
- test_catch_up.py
- AsyncSessionMock
- test_prompt_injection_canaries.py
- benchmark_parser.py
- ChatLens v2.0
- 🛠️ Local Development Setup
- auth.py
- Dashboard.tsx
- package.json
- TestHealthcheckFailureDetection
- save_messages
- whatsapp.py
- ChatLens v2.0 Design System
- run_mock_server
- test_erp_client_get_marks_session_recovery
- ADR 0002: Data-Instruction Separation & Prompt Injection Defense
- ADR 0003: Read-Only Telegram Ingestion Guardrail
- AGENTS.md — SPARK PA daemon (`src/`)
- dependencies
- manifest.json
- parse_telegram_export
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
- lucide-react
- frontend/AGENTS.md
- asyncio
- HTMLTableParser
- re
- unittest_mock
- Ponytail Ultra Minimalism Rules
- vitest.config.mjs
- Ponytail Ultra Minimalism Rules
- feature_request.md
- pull_request_template.md
- 🛡️ Security Policy
- TEST READY — Remediation Acceptance Test Suite
- Ponytail Ultra Coding Standards (Ponytail v5.1 Alignment)
- TypeScript & Frontend Engineering Rules (ChatLens v2)
- telegram.py
- Toast.tsx
- ._is_session_expired
- frontend/README.md
- Security Policy
- TypeScript & Frontend Engineering Rules (ChatLens v2)
- KL University ERP Integration (KLU ERP)
- src/config.py
- ADR Scaffolding Workflow (`/adr`)
- test_empirical_erp_concurrency_lock_serialization
- ADR Scaffolding Command (`/adr`)
- SPARK PA Daemon Deployment
- tests/conftest.py
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

## God Nodes (most connected - your core abstractions)
1. `handle_bot_command()` - 62 edges
2. `E2EClient` - 53 edges
3. `handle_bot_callback()` - 41 edges
4. `run_daemon()` - 37 edges
5. `MessageDeduplicator` - 37 edges
6. `get_connection()` - 36 edges
7. `RegexParser` - 31 edges
8. `format_day_schedule()` - 31 edges
9. `Message` - 29 edges
10. `KLUERPClient` - 28 edges

## Surprising Connections (you probably didn't know these)
- `Dashboard Routes Contract (`src/app/dashboard/*`)` --references--> `timetable()`  [INFERRED]
  chatlens-v2/frontend/PROJECT.md → tests/test_timetable.py
- `DEF-09: Unbounded Celery File Deletion Preventing Task Retries` --references--> `parse_and_save_sync()`  [INFERRED]
  docs/audits/chatlens-system-audit.md → chatlens-v2/backend/celery_worker.py
- `Phase 5: Reliability & Retrieval Enhancements (P2)` --references--> `generate_embedding()`  [INFERRED]
  docs/audits/chatlens-remediation-plan.md → chatlens-v2/backend/embeddings.py
- `Phase 1: Security Hardening & Authentication Enforcement (P0)` --references--> `get_current_user()`  [INFERRED]
  docs/audits/chatlens-remediation-plan.md → chatlens-v2/backend/firebase_auth.py
- `5. Root-Cause Analysis: Confirmed Causes vs. Hypotheses` --references--> `get_current_user()`  [INFERRED]
  docs/audits/chatlens-system-audit.md → chatlens-v2/backend/firebase_auth.py

## Import Cycles
- None detected.

## Communities (143 total, 46 thin omitted)

### Community 0 - "run_daemon"
Cohesion: 0.06
Nodes (46): Architecture, Code Layout, Feature Inventory, Interface Contracts, Milestones, Project: ChatLens PA Daemon & Telegram Bot Remediation, `src/notify/bot.py` ↔ `src/ingestion/handlers.py` & `src/main.py`, `src/timetable/__init__.py` ↔ `src/ingestion/handlers.py` (+38 more)

### Community 1 - "format_day_schedule"
Cohesion: 0.09
Nodes (25): format_day_schedule(), get_effective_slots(), load(), Meta, parse_periods(), Slot, Timetable, validate() (+17 more)

### Community 2 - "page.tsx"
Cohesion: 0.15
Nodes (25): Home(), AskBar(), DeadlinesModal(), DeadlinesModalProps, ImportModal(), Sidebar(), SidebarProps, SparkStatusModal() (+17 more)

### Community 3 - "E2EClient"
Cohesion: 0.05
Nodes (33): E2EClient, E2EResponse, test_f1_api_chats_endpoint_routed(), test_f1_api_healthz_routes_to_backend(), test_f1_root_request_routes_to_frontend(), test_f2_spa_route_fallback(), test_f2_static_asset_loads_cleanly(), test_f6_async_task_status_endpoint() (+25 more)

### Community 4 - "pytest"
Cohesion: 0.10
Nodes (29): build_briefing(), classes_can_skip(), classes_needed(), fetch_briefing_inputs(), next_run(), Settings, run_briefing(), guard() (+21 more)

### Community 5 - "test_e2e_remediation.py"
Cohesion: 0.05
Nodes (26): test_tier1_fuzzy_command_routing(), test_tier1_inline_callback_query_execution(), test_tier1_standalone_slash_trigger(), test_tier1_startup_debounce_cooldown(), test_tier1_timetable_fallback_happy_path(), test_tier1_today_command_happy_path(), test_tier1_tomorrow_command_happy_path(), test_tier2_all_periods_cancelled() (+18 more)

### Community 6 - "test_tier1_features.py"
Cohesion: 0.05
Nodes (19): lint_migrations(), main(), test_f1_caddyfile_routing_contracts(), test_f1_caddyfile_tls_and_encoding(), test_f1_ws_routing_configuration(), test_f2_nginx_conf_caching_and_spa(), test_f2_no_legacy_basepath_in_static_export(), test_f2_relative_origin_api_calls() (+11 more)

### Community 7 - "test_bot.py"
Cohesion: 0.06
Nodes (35): BotClient, BotConflictError, BotError, BotRateLimitedError, 1. Overview & Architecture, 2. Directory Layout & Artifact Index, 3. Tier Coverage Matrix (`tests/test_e2e_remediation.py`), 4. Execution & Verification Commands (+27 more)

### Community 8 - "test_run_daemon.py"
Cohesion: 0.08
Nodes (21): main(), test_b5_rapid_sequential_healthcheck_polling(), run_ps_command(), run_ps_script(), test_background_duplicate_suppression(), test_healthcheck_fails_when_daemon_stopped(), test_healthcheck_fails_when_database_corrupted(), test_healthcheck_fails_when_database_missing() (+13 more)

### Community 9 - "json"
Cohesion: 0.06
Nodes (45): main(), handle_bot_callback(), handle_undo_command(), get_connection(), record_write(), clean_db(), RequestRecorder, test_bot_send_custom_buttons_1d() (+37 more)

### Community 10 - "get"
Cohesion: 0.07
Nodes (18): api_deadlines(), api_monitoring_status(), api_timetable_today(), api_timetable_week(), delete_chat(), _escape_like(), export_chat(), get_chat_stats() (+10 more)

### Community 11 - "4. Failure Inventory (Evidence-Backed Defects)"
Cohesion: 0.05
Nodes (37): get_current_user(), require_current_user(), 1. Prioritization & Sequencing Strategy, 2. Phase-by-Phase Implementation Specifications, 3. End-to-End Verification Matrix, 4. Risks, Dependencies & Rollback Strategy, ChatLens Remediation Plan: Implementation Roadmap, Phase 1: Security Hardening & Authentication Enforcement (P0) (+29 more)

### Community 12 - "test_challenger_m2_m3.py"
Cohesion: 0.12
Nodes (10): clean_daemon_environment(), run_ps_script(), test_difflib_similarity_ratios_mathematical_oracle(), test_supervisor_healthcheck_corrupt_db(), test_supervisor_healthcheck_healthy_db(), test_supervisor_healthcheck_missing_db(), test_supervisor_status_when_running(), test_supervisor_status_when_stopped() (+2 more)

### Community 14 - "test_backend_api.py"
Cohesion: 0.10
Nodes (21): Message, test_analyzer_ask_fences_untrusted_transcript(), test_api_status_probe_degraded(), test_ask_prompt_fencing(), test_chat_deletion(), test_chat_export_json_and_csv(), test_chats_and_messages_lifecycle(), test_concurrent_imports_and_duplicate_collision() (+13 more)

### Community 15 - "handle_bot_command"
Cohesion: 0.13
Nodes (31): handle_bot_command(), register_handlers(), handle_incoming_message(), test_apply_event_calendar_conflict(), test_format_day_schedule_missing_timetable(), test_handle_bot_callback_cmd_attendance(), test_handle_bot_callback_cmd_deadlines(), test_handle_bot_callback_cmd_status() (+23 more)

### Community 16 - "CalendarSync"
Cohesion: 0.12
Nodes (13): CalendarSync, TasksSync, test_create_holiday_event_suppress_reminders(), test_update_class_room_patch_existing(), test_calendar_cancel_class(), test_calendar_missing_event(), test_calendar_override_marker_room(), test_calendar_period_window() (+5 more)

### Community 17 - "test_fuzz_parser.py"
Cohesion: 0.20
Nodes (13): parse_and_save_sync(), parse_whatsapp_export(), test_chats_import_endpoint_and_payload_limits(), test_parse_and_save_empty_zip(), test_parse_and_save_valid_nested_zip(), test_parse_and_save_zip_slip_rejection(), test_parse_and_save_zip_without_chat_files(), test_whatsapp_empty_file() (+5 more)

### Community 18 - "backend/main.py"
Cohesion: 0.09
Nodes (23): get_db(), api_analyze(), api_ask(), api_chat_insights(), api_deadlines_say(), api_global_summarize(), api_telegram_verify(), api_timetable_override() (+15 more)

### Community 20 - "MessageDeduplicator"
Cohesion: 0.09
Nodes (7): MessageDeduplicator, setup_test_env(), setup_test_env(), mock_daemon_settings(), test_debounce_evaluation_scenarios(), test_meta_table_crud_and_concurrency(), test_spark_rules_dedupe()

### Community 21 - "ChatAnalyzer"
Cohesion: 0.11
Nodes (6): ChatAnalyzer, _format_messages(), _redact_forbidden_ids(), test_empirical_pii_masking_zero_raw_digits(), test_analyzer_forbidden_id_redaction(), test_analyzer_format_messages()

### Community 22 - "logging.py"
Cohesion: 0.11
Nodes (15): Ingestion Boundaries, Privacy & Logging Standards, Security & Privacy Rules (ChatLens & SPARK PA), configure_logging(), _redact_str(), _scrub_secrets(), _scrub_value(), _sentry_before_send() (+7 more)

### Community 23 - "ExtractedAcademicEvent"
Cohesion: 0.19
Nodes (11): AIExtractor, today_ist(), test_ai_extractor_budget_exhaustion(), test_ai_extractor_clienterror_not_retried(), test_ai_extractor_day_rollover(), test_ai_extractor_empty_response(), test_ai_extractor_media_gate(), test_ai_extractor_no_sampling_params() (+3 more)

### Community 24 - "client.py"
Cohesion: 0.14
Nodes (13): parse_attendance_records(), parse_cgpa_records(), parse_fee_records(), parse_generic_tables(), parse_marks_records(), parse_timetable_records(), test_parse_attendance_metrics(), test_parse_cgpa() (+5 more)

### Community 25 - "ChatLens & SPARK PA Assistant"
Cohesion: 0.07
Nodes (26): 1. System Architecture & Trust Boundaries, 2.1 Ingestion Layer (Telethon Listener), 2.2 Parsing & LLM Layer (Regex & Gemini), 2.3 Workspace Synchronization Layer (Calendar, Tasks, Sheets), 2.4 State & Persistence Layer (SQLite Database), 2.5 Supply Chain & CI/CD Layer, 2. STRIDE Threat Analysis by Component, STRIDE Threat Model: ChatLens & SPARK PA Assistant (+18 more)

### Community 26 - "harness.py"
Cohesion: 0.16
Nodes (3): test_pairwise_celery_task_update_to_api_poll(), test_pairwise_migrations_run_before_backend_accepts_traffic(), test_pairwise_proxy_tls_termination_and_upstream_headers()

### Community 27 - "e2e/conftest.py"
Cohesion: 0.06
Nodes (14): compose_config(), e2e_client(), in_memory_db(), isolated_spark_db(), nginx_config(), AsyncSessionMock, CaseInsensitiveHeaderDict, ComposeParser (+6 more)

### Community 28 - "telegram_live.py"
Cohesion: 0.13
Nodes (12): api_telegram_send_code(), api_telegram_status(), api_telegram_sync_live(), check_status(), _fetch(), fetch_telegram_chats(), _get_client(), send_code() (+4 more)

### Community 29 - "RegexParser"
Cohesion: 0.17
Nodes (13): RegexParser, test_empirical_regex_parser_room_variations(), test_periods_dashes(), test_room_direction(), test_task_precision(), test_regex_parser_course_mapping_table(), test_regex_parser_holiday_summary_truncation(), test_regex_parser_none_on_unstructured() (+5 more)

### Community 30 - "clock.py"
Cohesion: 0.11
Nodes (15): Invariants & Architecture, Python Engineering Rules (ChatLens & SPARK PA), Runtime & Toolchain, Architecture & Conventions, CLAUDE.md — ChatLens Assistant Guide, Essential Commands, Invariants & Architecture, Python Engineering Rules (ChatLens & SPARK PA) (+7 more)

### Community 32 - "sqlite3"
Cohesion: 0.07
Nodes (17): caddyfile_config(), CaddyfileParser, test_f8_backend_spark_status_bridge(), test_f8_spark_sqlite_integrity_check(), test_f8_spark_sqlite_wal_persistence(), test_pairwise_daemon_sqlite_wal_to_backend_status_bridge(), test_alembic_migration_idempotency_sqlite(), test_alembic_migration_preexisting_table() (+9 more)

### Community 33 - "os"
Cohesion: 0.13
Nodes (6): generate_embeddings_batch(), main(), test_chat_statistics_aggregation(), test_content_hash_determinism(), test_whatsapp_parser_standard(), test_whatsapp_parser_us_format_and_12h()

### Community 34 - "datetime"
Cohesion: 0.12
Nodes (14): _build_full_day_timetable(), _get_icons_from_output(), test_empirical_adjacent_period_boundary_minute(), test_empirical_after_all_classes_end(), test_empirical_before_classes_start(), test_empirical_inter_period_breaks(), test_empirical_lunch_break_transitions(), test_empirical_period_exact_end_time() (+6 more)

### Community 36 - "test_workspace_and_erp.py"
Cohesion: 0.18
Nodes (7): SheetsLogger, test_empirical_sheets_logger_silent_degradation(), test_sheets_logger_heartbeat_configured_sheet_id(), test_sheets_logger_heartbeat_empty_sheet_id(), test_sheets_logger_heartbeat_whitespace_sheet_id(), test_sheets_logger_init_preserves_empty_string(), test_sheets_logger_unconfigured_guard_and_skips()

### Community 37 - "test_tier5_resilience.py"
Cohesion: 0.05
Nodes (14): detect_archetype(), main(), check_compose_file(), check_env_template(), check_live_endpoints(), check_supporting_configs(), log_info(), log_pass() (+6 more)

### Community 38 - "MessageList.tsx"
Cohesion: 0.22
Nodes (12): ChatHeader(), ChatHeaderProps, insightButtons, formatDate(), formatTime(), isGrouped(), isSameDay(), MessageList() (+4 more)

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 42 - "handlers.py"
Cohesion: 0.21
Nodes (8): AcademicCalendar, get_milestone_date(), load_calendar(), apply_event(), extract(), _get_sender_name(), process_message(), ExtractedAcademicEvent

### Community 46 - "env.py"
Cohesion: 0.14
Nodes (8): lifespan(), do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), run_sync_migrations(), Base, Phase 4: Database Harmonization & Migration Lifecycle Cleanup (P2)

### Community 47 - "components.test.tsx"
Cohesion: 0.36
Nodes (6): AiCard(), AiCardProps, FormatAi(), renderInline(), WelcomePage(), WelcomePageProps

### Community 48 - "harvest_debt.py"
Cohesion: 0.21
Nodes (7): check_adrs(), main(), harvest_debt(), main(), update_debt_file(), test_adr_compliance(), test_debt_ledger_sync()

### Community 49 - "test_catch_up.py"
Cohesion: 0.30
Nodes (12): catch_up_chats(), clean_db(), mock_client(), test_catch_up_7_day_cutoff(), test_catch_up_first_run(), test_catch_up_inaccessible_chat(), test_catch_up_live_message_advances(), test_catch_up_max_keeping_upsert() (+4 more)

### Community 50 - "AsyncSessionMock"
Cohesion: 0.15
Nodes (4): AsyncSessionMock, in_memory_db(), override_async_session_local(), override_get_db()

### Community 51 - "test_prompt_injection_canaries.py"
Cohesion: 0.23
Nodes (7): decide(), Decision, test_empirical_prompt_injection_canaries_suite(), test_decide_invalid(), test_decide_valid(), test_canary_dry_mode_absolute_lock(), test_canary_regex_parsing_and_decision_policy()

### Community 52 - "benchmark_parser.py"
Cohesion: 0.31
Nodes (3): run_parser_benchmark(), run_timetable_benchmark(), main()

### Community 53 - "ChatLens v2.0"
Cohesion: 0.15
Nodes (12): 1. Architecture Overview, 2. Directory Structure, 3. Environment Variables, 4. Setup and Execution, 5. Key REST API Endpoints, Backend (`chatlens-v2/backend/.env`), ChatLens v2.0, Frontend (`chatlens-v2/frontend/.env.local`) (+4 more)

### Community 54 - "🛠️ Local Development Setup"
Cohesion: 0.15
Nodes (12): 📥 1. Fork & Clone, 🔧 2. Configuration, 📦 3. Run External Services, 🐍 4. Backend Setup, ⚛️ 5. Frontend Setup, 🤝 Contributing to ChatLens, ⚛️ Frontend Linting, 🛠️ Local Development Setup (+4 more)

### Community 56 - "Dashboard.tsx"
Cohesion: 0.29
Nodes (9): chartOptions(), Dashboard(), DashboardProps, DAY_LABELS, SkeletonCard(), SkeletonChart(), ChatStats, chart.js (+1 more)

### Community 57 - "package.json"
Cohesion: 0.10
Nodes (20): eslintConfig, name, private, scripts, build, dev, lint, start (+12 more)

### Community 59 - "save_messages"
Cohesion: 0.12
Nodes (12): ADR 0006: Zero Debt, Dialect-Aware Vector Retrieval, and Strict Backend Typing, Confirmation & Verification, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Negative Consequences / Tradeoffs, Positive Consequences (+4 more)

### Community 60 - "whatsapp.py"
Cohesion: 0.24
Nodes (5): _parse_datetime(), test_telegram_parser_full_account(), test_telegram_parser_single_chat(), test_whatsapp_parser_24h_format(), test_whatsapp_parser_basic()

### Community 61 - "ChatLens v2.0 Design System"
Cohesion: 0.18
Nodes (10): 1. Intent, 2. Colors, 3. Typography, 4. Spacing, 5. Motion (motion-anything), 6. Shapes & Borders, 7. Human-Centric Principles, 8. Icons (+2 more)

### Community 63 - "test_erp_client_get_marks_session_recovery"
Cohesion: 0.24
Nodes (6): test_erp_client_fetch_page_session_recovery(), mock_send(), test_erp_client_get_marks_session_recovery(), test_erp_client_login_lock_serialization(), concurrent_login(), fake_login_internal()

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

### Community 69 - "parse_telegram_export"
Cohesion: 0.22
Nodes (6): parse_telegram_export(), test_telegram_corrupt_json(), test_telegram_empty_or_non_dict(), test_telegram_missing_and_service_fields(), test_telegram_parser_full_export_chats_list(), test_telegram_parser_single_chat()

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

### Community 89 - "lucide-react"
Cohesion: 0.28
Nodes (6): AskBarProps, ImportModalProps, SparkStatusModalProps, SparkStatus, clsx, lucide-react

### Community 90 - "frontend/AGENTS.md"
Cohesion: 0.33
Nodes (4): 📐 Architecture & Principles, 🛠️ Build & Test Commands, 📁 Directory Structure, 🚀 Project Overview

### Community 91 - "asyncio"
Cohesion: 0.22
Nodes (4): test_fuzzy_routing_additional_invalid_commands(), test_fuzzy_routing_rejection_mandate(), test_fuzzy_routing_undo_and_slash_safety(), test_fuzzy_routing_valid_typos_mandate()

### Community 94 - "unittest_mock"
Cohesion: 0.12
Nodes (7): test_b4_broker_down_fallback(), test_b4_empty_upload_payload(), test_b4_invalid_platform_parameter(), test_b4_upload_file_exceeds_max_bytes(), test_pairwise_backend_upload_to_celery_shared_volume(), test_scenario_3_chat_upload_and_analysis_lifecycle(), test_scenario_4_spark_daemon_restart_and_state_recovery()

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

### Community 104 - "telegram.py"
Cohesion: 0.33
Nodes (3): _flatten_text(), _parse_message(), test_telegram_flatten_text_heterogeneous_structures()

### Community 105 - "Toast.tsx"
Cohesion: 0.38
Nodes (6): icons, styles, Toast(), ToastItem(), ToastProps, ToastData

### Community 106 - "._is_session_expired"
Cohesion: 0.29
Nodes (3): test_empirical_erp_session_expiration_markers(), test_erp_client_is_session_expired(), test_erp_client_status_codes_session_expired()

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

## Knowledge Gaps
- **8 isolated node(s):** `tailwind-merge`, `@tailwindcss/postcss`, `@types/node`, `@types/react`, `@types/react-dom` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1006 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **46 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `2. Phase-by-Phase Implementation Specifications` connect `4. Failure Inventory (Evidence-Backed Defects)` to `page.tsx`, `get`, `env.py`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `handle_bot_command()` (e.g. with `Code Layout` and `1. Overview & Architecture`) actually correct?**
  _`handle_bot_command()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `tailwind-merge`, `@tailwindcss/postcss`, `@types/node` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `run_daemon` be split into smaller, more focused modules?**
  _Cohesion score 0.05574229691876751 - nodes in this community are weakly interconnected._
- **Why does `Phase 2: Frontend Restoration & Static Export Configuration (P1)` connect `page.tsx` to `Dashboard.tsx`, `4. Failure Inventory (Evidence-Backed Defects)`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Are the 39 inferred relationships involving `E2EClient` (e.g. with `e2e_client()` and `test_f1_api_chats_endpoint_routed()`) actually correct?**
  _`E2EClient` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Should `format_day_schedule` be split into smaller, more focused modules?**
  _Cohesion score 0.09276018099547512 - nodes in this community are weakly interconnected._