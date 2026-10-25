# Graph Report - kind-faraday  (2026-10-25)

## Corpus Check
- 234 files · ~146,879 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 35 file(s) not represented in the graph (top: (none) 19, .example 3, .toml 3)

## Summary
- 2546 nodes · 5143 edges · 180 communities (110 shown, 70 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 378 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `571139df`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- run_daemon
- mock_bot_answer_callback
- types.ts
- E2EClient
- pytest
- asyncio
- test_tier1_features.py
- BotClient
- test_run_daemon.py
- logging.py
- test_tier2_boundaries.py
- ChatLens Full-System Engineering Audit Report
- test_challenger_m2_m3.py
- KLUERPClient
- test_backend_api.py
- handle_bot_command
- handle_bot_callback
- test_fuzz_parser.py
- backend/main.py
- json
- MessageDeduplicator
- ChatAnalyzer
- .meta_get
- run_reminders
- scrapers.py
- ChatLens & SPARK PA Assistant
- harness.py
- e2e/conftest.py
- telegram_live.py
- test_challenger_empirical.py
- GovernanceAuditLogger
- Path
- test_scheduler.py
- celery_worker.py
- verify_deployment.py
- 4. Failure Inventory (Evidence-Backed Defects)
- test_workspace_and_erp.py
- test_challenger_m2_m3_2.py
- os
- TestVerificationScriptErrorPaths
- compilerOptions
- run_ps_supervisor
- Home
- AIExtractor
- datetime
- test_governance.py
- env.py
- components.test.tsx
- test_tier5_adversarial.py
- test_catch_up.py
- pytest
- sys
- Dashboard.tsx
- ChatLens v2.0
- 🛠️ Local Development Setup
- retriever.py
- whatsapp.py
- package.json
- TestHealthcheckFailureDetection
- save_messages
- clock.py
- ChatLens v2.0 Design System
- google_token.py
- test_erp_client_get_marks_session_recovery
- ADR 0002: Data-Instruction Separation & Prompt Injection Defense
- ADR 0003: Read-Only Telegram Ingestion Guardrail
- AGENTS.md — SPARK PA daemon (`src/`)
- dependencies
- manifest.json
- TelegramRateLimiter
- ADR 0001: Adoption of Awesome Dev Pipeline v2.2.0
- ADR 0004: Gemini AI Guardrails and Mandatory Holiday Confirmation
- ADR 0005: ChatLens Full-Stack Architecture, Vector Retrieval, and SPARK Bridge
- ADR 0007: ChatLens Frontend Restoration and Student Portal Isolation
- Verification Matrix
- _build_full_day_timetable
- Project: KL-Sync System-Wide Verification & Quality Audit
- 🤝 Contributor Covenant Code of Conduct
- run_mock_server
- Security Audit Areas
- layout.tsx
- Definition of Done (Addy Osmani agent-skills Alignment)
- Required Format
- KnowledgeRetriever
- Required Format
- settings.json
- bug_report.md
- AgentShield Security Specification (ECC v2.2.3 Alignment)
- Workflow
- AsyncSessionMock
- frontend/AGENTS.md
- GoogleWorkspaceAuth
- handlers.py
- WorkspaceCircuitBreaker
- analyzer.py
- Ponytail Ultra Minimalism Rules
- vitest.config.mjs
- Ponytail Ultra Minimalism Rules
- feature_request.md
- pull_request_template.md
- 🛡️ Security Policy
- TEST READY — Remediation Acceptance Test Suite
- Ponytail Ultra Coding Standards (Ponytail v5.1 Alignment)
- TypeScript & Frontend Engineering Rules (ChatLens v2)
- run_ps_command
- ADR 0006: Zero Debt, Dialect-Aware Vector Retrieval, and Strict Backend Typing
- test_timetable_l1_cache_hit_and_invalidation
- frontend/README.md
- Security Policy
- TypeScript & Frontend Engineering Rules (ChatLens v2)
- KL University ERP Integration (KLU ERP)
- bot.py
- ADR Scaffolding Workflow (`/adr`)
- test_empirical_erp_concurrency_lock_serialization
- ADR Scaffolding Command (`/adr`)
- SPARK PA Daemon Deployment
- Toast.tsx
- ContiguousVectorBuffer
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
- ADR 0008: Adoption of Microsoft Agent Governance Principles and In-Process Turbovec RAG
- CaseInsensitiveHeaderDict
- test_briefing_command
- asyncio
- re
- TestSecretMaskingIntegrity
- CLAUDE.md — ChatLens Assistant Guide
- backend/main.py
- test_tier5_resilience.py
- src/main.py
- 2. Phase-by-Phase Implementation Specifications
- telegram.py
- setup_test_env
- HTMLTableParser
- no-mistakes
- test_today_and_tomorrow_bot_commands_simultaneously
- setup_test_env
- retry_error_handler
- devDependencies
- helpers.py
- isolate_env
- test_run_daemon_no_legacy_get_process_commandline

## God Nodes (most connected - your core abstractions)
1. `handle_bot_command()` - 79 edges
2. `E2EClient` - 53 edges
3. `MessageDeduplicator` - 42 edges
4. `get_connection()` - 42 edges
5. `handle_bot_callback()` - 41 edges
6. `run_daemon()` - 38 edges
7. `format_day_schedule()` - 30 edges
8. `Message` - 29 edges
9. `RegexParser` - 29 edges
10. `FakeTelegramClient` - 28 edges

## Surprising Connections (you probably didn't know these)
- `3. Template Reference Implementations` --references--> `get_standard_navigation_buttons()`  [INFERRED]
  docs/MESSAGE_FORMATTING_RULES.md → src/formatting/templates.py
- `Positive Consequences` --references--> `UntrustedInput`  [INFERRED]
  adr/0008-microsoft-agent-governance-and-turbovec-rag.md → src/governance/guards.py
- `Dashboard Routes Contract (`src/app/dashboard/*`)` --references--> `timetable()`  [INFERRED]
  chatlens-v2/frontend/PROJECT.md → tests/test_timetable.py
- `Phase 1: Security Hardening & Authentication Enforcement (P0)` --references--> `get_current_user()`  [INFERRED]
  docs/audits/chatlens-remediation-plan.md → chatlens-v2/backend/firebase_auth.py
- `Reading the output` --references--> `status()`  [INFERRED]
  .agents/skills/no-mistakes/SKILL.md → chatlens-v2/backend/main.py

## Import Cycles
- None detected.

## Communities (180 total, 70 thin omitted)

### Community 0 - "run_daemon"
Cohesion: 0.15
Nodes (23): run_daemon(), run_heartbeat(), FakeTelegramClient, guard(), test_bot_callback_poll_no_token_returns_immediately(), test_bot_callback_poll_runs_in_dry_mode(), test_bot_callback_poll_undo_routing(), test_daemon_clean_client_disconnect() (+15 more)

### Community 2 - "types.ts"
Cohesion: 0.13
Nodes (25): Home(), DeadlinesModal(), DeadlinesModalProps, Sidebar(), SidebarProps, SparkStatusModal(), SparkStatusModalProps, TimetableModal() (+17 more)

### Community 3 - "E2EClient"
Cohesion: 0.06
Nodes (26): E2EClient, E2EResponse, test_f1_api_chats_endpoint_routed(), test_f1_api_healthz_routes_to_backend(), test_f1_root_request_routes_to_frontend(), test_f2_spa_route_fallback(), test_f2_static_asset_loads_cleanly(), test_f6_async_task_status_endpoint() (+18 more)

### Community 4 - "pytest"
Cohesion: 0.14
Nodes (18): AcademicCalendar, get_milestone_date(), load_calendar(), build_briefing(), classes_can_skip(), classes_needed(), fetch_briefing_inputs(), format_bunk_calculator() (+10 more)

### Community 5 - "asyncio"
Cohesion: 0.05
Nodes (26): test_tier1_fuzzy_command_routing(), test_tier1_inline_callback_query_execution(), test_tier1_standalone_slash_trigger(), test_tier1_startup_debounce_cooldown(), test_tier1_timetable_fallback_happy_path(), test_tier1_today_command_happy_path(), test_tier1_tomorrow_command_happy_path(), test_tier2_all_periods_cancelled() (+18 more)

### Community 6 - "test_tier1_features.py"
Cohesion: 0.05
Nodes (22): lint_migrations(), main(), test_f1_caddyfile_routing_contracts(), test_f1_caddyfile_tls_and_encoding(), test_f1_ws_routing_configuration(), test_f2_nginx_conf_caching_and_spa(), test_f2_no_legacy_basepath_in_static_export(), test_f2_relative_origin_api_calls() (+14 more)

### Community 7 - "BotClient"
Cohesion: 0.06
Nodes (35): BotClient, BotConflictError, BotError, BotRateLimitedError, 1. Overview & Architecture, 2. Directory Layout & Artifact Index, 3. Tier Coverage Matrix (`tests/test_e2e_remediation.py`), 4. Execution & Verification Commands (+27 more)

### Community 8 - "test_run_daemon.py"
Cohesion: 0.10
Nodes (16): main(), run_ps_script(), test_background_duplicate_suppression(), test_healthcheck_fails_when_daemon_stopped(), test_healthcheck_fails_when_database_corrupted(), test_healthcheck_fails_when_database_missing(), test_healthcheck_fails_when_heartbeat_missing(), test_healthcheck_fails_when_heartbeat_stale() (+8 more)

### Community 9 - "logging.py"
Cohesion: 0.06
Nodes (28): Ingestion Boundaries, Privacy & Logging Standards, Security & Privacy Rules (ChatLens & SPARK PA), configure_logging(), _redact_str(), _scrub_secrets(), _scrub_value(), _sentry_before_send() (+20 more)

### Community 10 - "test_tier2_boundaries.py"
Cohesion: 0.06
Nodes (15): test_b3_consecutive_reruns_idempotent(), test_b3_destructive_ddl_rejection(), test_b3_duplicate_content_hash_collision(), test_b3_null_embedding_vector_handling(), test_b3_table_already_exists_resilience(), test_b4_broker_down_fallback(), test_b4_empty_upload_payload(), test_b4_invalid_platform_parameter() (+7 more)

### Community 11 - "ChatLens Full-System Engineering Audit Report"
Cohesion: 0.12
Nodes (15): 1. Executive Summary, 2. System Architecture & Component Inventory, 3. Baseline Verification Results, 6. Critical User-Journey Verification Matrix, 7.1 Authentication & Authorization Bypass (DEF-04), 7.2 Hardcoded Secrets & PII Scrubbing, 7.3 Prompt Injection Defense, 7. Security and Privacy Review (+7 more)

### Community 12 - "test_challenger_m2_m3.py"
Cohesion: 0.12
Nodes (10): clean_daemon_environment(), run_ps_script(), test_difflib_similarity_ratios_mathematical_oracle(), test_supervisor_healthcheck_corrupt_db(), test_supervisor_healthcheck_healthy_db(), test_supervisor_healthcheck_missing_db(), test_supervisor_status_when_running(), test_supervisor_status_when_stopped() (+2 more)

### Community 13 - "KLUERPClient"
Cohesion: 0.10
Nodes (6): KLUERPClient, test_empirical_erp_session_expiration_markers(), test_empirical_erp_session_expiry_triggers_ocr_reauth(), test_erp_client_is_session_expired(), test_erp_client_marks_cache_offline_fallback(), test_erp_client_status_codes_session_expired()

### Community 14 - "test_backend_api.py"
Cohesion: 0.05
Nodes (25): AsyncSessionMock, in_memory_db(), override_async_session_local(), override_get_db(), test_analyzer_ask_fences_untrusted_transcript(), test_api_status_probe_degraded(), test_ask_prompt_fencing(), test_chat_deletion() (+17 more)

### Community 15 - "handle_bot_command"
Cohesion: 0.13
Nodes (30): handle_bot_command(), register_handlers(), test_format_day_schedule_missing_timetable(), test_handle_bot_callback_cmd_attendance(), test_handle_bot_callback_cmd_deadlines(), test_handle_bot_callback_cmd_status(), test_handle_bot_callback_cmd_today(), test_handle_bot_callback_unauthorized_ignored() (+22 more)

### Community 16 - "handle_bot_callback"
Cohesion: 0.09
Nodes (18): handle_bot_callback(), RequestRecorder, test_bot_send_custom_buttons_1d(), test_bot_send_custom_buttons_2d(), test_bot_send_default_quick_buttons(), test_bot_send_empty_buttons_suppresses_reply_markup(), test_bot_set_my_commands_exact_registration(), test_callback_answer_failure_resilience() (+10 more)

### Community 17 - "test_fuzz_parser.py"
Cohesion: 0.17
Nodes (16): parse_and_save_sync(), parse_telegram_export(), parse_whatsapp_export(), test_parse_and_save_empty_zip(), test_parse_and_save_valid_nested_zip(), test_parse_and_save_zip_slip_rejection(), test_parse_and_save_zip_without_chat_files(), test_telegram_corrupt_json() (+8 more)

### Community 18 - "backend/main.py"
Cohesion: 0.11
Nodes (20): api_analyze(), api_auth_me(), api_chat_insights(), api_deadlines(), api_global_summarize(), api_monitoring_status(), api_timetable_today(), api_timetable_week() (+12 more)

### Community 19 - "json"
Cohesion: 0.19
Nodes (25): handle_undo_command(), get_connection(), clean_db(), mock_bot(), test_confirm_flow_approve(), test_confirm_flow_bot_edit_without_msg_id(), test_confirm_flow_expired(), test_confirm_flow_failed_write() (+17 more)

### Community 22 - ".meta_get"
Cohesion: 0.18
Nodes (5): test_r_ban_2_consent_via_start_allows_dm(), test_r_ban_3_startup_debounce_logic(), isolate_test_environment(), test_debounce_evaluation_scenarios(), test_meta_table_crud_and_concurrency()

### Community 23 - "run_reminders"
Cohesion: 0.18
Nodes (12): Instance-specific academic data, Architecture, Code Layout, Feature Inventory, Interface Contracts, Milestones, Project: ChatLens PA Daemon & Telegram Bot Architecture, `src/formatting/templates.py` ↔ `src/ingestion/handlers.py` & `src/main.py` (+4 more)

### Community 24 - "scrapers.py"
Cohesion: 0.14
Nodes (13): parse_attendance_records(), parse_cgpa_records(), parse_fee_records(), parse_generic_tables(), parse_marks_records(), parse_timetable_records(), test_parse_attendance_metrics(), test_parse_cgpa() (+5 more)

### Community 25 - "ChatLens & SPARK PA Assistant"
Cohesion: 0.05
Nodes (38): 1. System Architecture & Trust Boundaries, 2.1 Ingestion Layer (Telethon Listener), 2.2 Parsing & LLM Layer (Regex & Gemini), 2.3 Workspace Synchronization Layer (Calendar, Tasks, Sheets), 2.4 State & Persistence Layer (SQLite Database), 2.5 Supply Chain & CI/CD Layer, 2. STRIDE Threat Analysis by Component, STRIDE Threat Model: ChatLens & SPARK PA Assistant (+30 more)

### Community 26 - "harness.py"
Cohesion: 0.10
Nodes (4): export_prompt(), test_pairwise_backend_upload_to_celery_shared_volume(), test_pairwise_daemon_sqlite_wal_to_backend_status_bridge(), test_pairwise_migrations_run_before_backend_accepts_traffic()

### Community 27 - "e2e/conftest.py"
Cohesion: 0.11
Nodes (9): compose_config(), e2e_client(), in_memory_db(), isolated_spark_db(), nginx_config(), ComposeParser, NginxConfParser, setup_isolated_spark_db() (+1 more)

### Community 28 - "telegram_live.py"
Cohesion: 0.15
Nodes (10): api_telegram_status(), check_status(), _fetch(), fetch_telegram_chats(), _get_client(), send_code(), send_telegram_code_sync(), _sender_name() (+2 more)

### Community 29 - "test_challenger_empirical.py"
Cohesion: 0.06
Nodes (29): run_parser_benchmark(), run_timetable_benchmark(), run_turbovec_benchmark(), main(), decide(), Decision, RegexParser, test_empirical_prompt_injection_canaries_suite() (+21 more)

### Community 30 - "GovernanceAuditLogger"
Cohesion: 0.12
Nodes (4): GovernanceAuditLogger, test_adversarial_injection_quarantined_in_pipeline(), test_governance_audit_logger_roundtrip(), test_quarantine_console_commands()

### Community 32 - "test_scheduler.py"
Cohesion: 0.26
Nodes (10): next_run(), run_briefing(), guard(), test_briefing_idempotent(), test_briefing_retry_on_failure(), test_heartbeat_interval(), test_next_run_after_target(), test_next_run_before_target() (+2 more)

### Community 33 - "celery_worker.py"
Cohesion: 0.17
Nodes (3): DummyCelery, generate_embeddings_batch(), parse_file_task()

### Community 34 - "verify_deployment.py"
Cohesion: 0.15
Nodes (9): detect_archetype(), main(), check_compose_file(), check_env_template(), check_live_endpoints(), check_supporting_configs(), log_info(), log_pass() (+1 more)

### Community 35 - "4. Failure Inventory (Evidence-Backed Defects)"
Cohesion: 0.18
Nodes (11): 4. Failure Inventory (Evidence-Backed Defects), DEF-01: Complete Substitution & Deletion of ChatLens UI, DEF-02: Frontend Docker Build & Static Export Deadlock, DEF-03: Reverse Proxy API Interception Deadlock, DEF-05: Backend Container Healthcheck Endpoint Mismatch, DEF-06: Database Credential and Connection String Divergence, DEF-07: Redundant Dual/Triple Migration Execution with Bare Exception Suppression, DEF-08: Asymmetric Vector Retrieval Degradation via Omitted Task Type (+3 more)

### Community 36 - "test_workspace_and_erp.py"
Cohesion: 0.17
Nodes (7): SheetsLogger, test_empirical_sheets_logger_silent_degradation(), test_sheets_logger_heartbeat_configured_sheet_id(), test_sheets_logger_heartbeat_empty_sheet_id(), test_sheets_logger_heartbeat_whitespace_sheet_id(), test_sheets_logger_init_preserves_empty_string(), test_sheets_logger_unconfigured_guard_and_skips()

### Community 37 - "test_challenger_m2_m3_2.py"
Cohesion: 0.13
Nodes (9): make_clock_mock(), mock_daemon_settings(), test_debounce_bot_transmission_failure_preserves_prior_timestamp(), test_debounce_corrupted_timestamp_recovery(), test_debounce_delta_mathematical_precision_sweep(), test_debounce_first_boot_no_prior_record(), test_debounce_threshold_899_9_seconds_suppressed(), test_debounce_threshold_900_0_exact_boundary_allowed() (+1 more)

### Community 38 - "os"
Cohesion: 0.08
Nodes (14): _authentication_required(), get_current_user(), require_current_user(), 5. Root-Cause Analysis: Confirmed Causes vs. Hypotheses, DEF-04: Zero Authentication Enforcement on All Backend Endpoints, test_mock_firebase_token_is_rejected_outside_test_environment(), test_analyzer_forbidden_id_redaction(), test_analyzer_format_messages() (+6 more)

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 42 - "Home"
Cohesion: 0.15
Nodes (15): AskBar(), AskBarProps, EXAM_SCHEDULE, ExamPrepModal(), ExamPrepModalProps, EXPERIMENTS, app, auth (+7 more)

### Community 43 - "AIExtractor"
Cohesion: 0.11
Nodes (20): Invariants & Architecture, Python Engineering Rules (ChatLens & SPARK PA), Runtime & Toolchain, Architecture & Conventions, Invariants & Architecture, Python Engineering Rules (ChatLens & SPARK PA), Runtime & Toolchain, AIExtractor (+12 more)

### Community 44 - "datetime"
Cohesion: 0.09
Nodes (27): format_day_schedule(), get_effective_slots(), load(), Meta, parse_periods(), Slot, Timetable, validate() (+19 more)

### Community 45 - "test_governance.py"
Cohesion: 0.05
Nodes (21): 2.6 Agent Governance & Semantic Vector Memory Layer (Microsoft AGT & Turbovec), InputGuard, UntrustedInput, ActionTier, PolicyEngine, PolicyEvaluationResult, PolicyVerdict, test_action_tier_classification() (+13 more)

### Community 46 - "env.py"
Cohesion: 0.17
Nodes (6): do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), run_sync_migrations(), Base

### Community 47 - "components.test.tsx"
Cohesion: 0.15
Nodes (21): AiCard(), AiCardProps, ChatHeader(), ChatHeaderProps, insightButtons, FormatAi(), renderInline(), ImportModal() (+13 more)

### Community 48 - "test_tier5_adversarial.py"
Cohesion: 0.08
Nodes (14): caddyfile_config(), CaddyfileParser, test_alembic_migration_idempotency_sqlite(), test_alembic_migration_preexisting_table(), test_caddyfile_path_matching_api_exact(), test_compose_custom_database_url_override_ignored(), test_compose_variable_interpolation_special_chars(), test_proxy_route_api_trailing_slash_discrepancy() (+6 more)

### Community 49 - "test_catch_up.py"
Cohesion: 0.30
Nodes (12): catch_up_chats(), clean_db(), mock_client(), test_catch_up_7_day_cutoff(), test_catch_up_first_run(), test_catch_up_inaccessible_chat(), test_catch_up_live_message_advances(), test_catch_up_max_keeping_upsert() (+4 more)

### Community 50 - "pytest"
Cohesion: 0.45
Nodes (6): Settings, test_settings_invalid_chat_ids(), test_settings_invalid_chat_ids_non_integer(), test_settings_invalid_mode(), test_settings_missing_live_confirm(), test_settings_valid()

### Community 51 - "sys"
Cohesion: 0.25
Nodes (4): main(), harvest_debt(), main(), update_debt_file()

### Community 52 - "Dashboard.tsx"
Cohesion: 0.29
Nodes (9): chartOptions(), Dashboard(), DashboardProps, DAY_LABELS, SkeletonCard(), SkeletonChart(), ChatStats, chart.js (+1 more)

### Community 53 - "ChatLens v2.0"
Cohesion: 0.15
Nodes (12): 1. Architecture Overview, 2. Directory Structure, 3. Environment Variables, 4. Setup and Execution, 5. Key REST API Endpoints, Backend (`chatlens-v2/backend/.env`), ChatLens v2.0, Frontend (`chatlens-v2/frontend/.env.local`) (+4 more)

### Community 54 - "🛠️ Local Development Setup"
Cohesion: 0.15
Nodes (12): 📥 1. Fork & Clone, 🔧 2. Configuration, 📦 3. Run External Services, 🐍 4. Backend Setup, ⚛️ 5. Frontend Setup, 🤝 Contributing to ChatLens, ⚛️ Frontend Linting, 🛠️ Local Development Setup (+4 more)

### Community 56 - "whatsapp.py"
Cohesion: 0.24
Nodes (5): _parse_datetime(), test_telegram_parser_full_account(), test_telegram_parser_single_chat(), test_whatsapp_parser_24h_format(), test_whatsapp_parser_basic()

### Community 57 - "package.json"
Cohesion: 0.07
Nodes (26): eslintConfig, name, overrides, baseline-browser-mapping, browserslist, @grpc/grpc-js, zod, private (+18 more)

### Community 59 - "save_messages"
Cohesion: 0.15
Nodes (8): Positive Consequences, save_messages(), generate_embedding(), generate_embeddings_batch(), api_ask(), api_telegram_sync_live(), AskRequest, _retrieve_relevant_messages()

### Community 60 - "clock.py"
Cohesion: 0.27
Nodes (5): to_ist(), test_clock_boundary(), test_clock_to_ist_aware_converted(), test_clock_to_ist_naive_treated_as_utc(), test_frozen_clock_fixture()

### Community 61 - "ChatLens v2.0 Design System"
Cohesion: 0.18
Nodes (10): 1. Intent, 2. Colors, 3. Typography, 4. Spacing, 5. Motion (motion-anything), 6. Shapes & Borders, 7. Human-Centric Principles, 8. Icons (+2 more)

### Community 63 - "test_erp_client_get_marks_session_recovery"
Cohesion: 0.22
Nodes (6): test_erp_client_fetch_page_session_recovery(), mock_send(), test_erp_client_get_marks_session_recovery(), test_erp_client_login_lock_serialization(), concurrent_login(), fake_login_internal()

### Community 64 - "ADR 0002: Data-Instruction Separation & Prompt Injection Defense"
Cohesion: 0.20
Nodes (9): ADR 0002: Data-Instruction Separation & Prompt Injection Defense, Architecture & Mitigations, Confirmation & Verification, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Negative Consequences / Tradeoffs (+1 more)

### Community 65 - "ADR 0003: Read-Only Telegram Ingestion Guardrail"
Cohesion: 0.20
Nodes (9): ADR 0003: Read-Only Telegram Ingestion Guardrail, Confirmation & Verification, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Implementation Guarantees, Negative Consequences / Tradeoffs (+1 more)

### Community 66 - "AGENTS.md — SPARK PA daemon (`src/`)"
Cohesion: 0.22
Nodes (8): AGENTS.md — SPARK PA daemon (`src/`), Commands, Environment variables, Invariants (target behavior; each task prompt says which parts already exist), SQLite state (`SPARK_DB`, default `spark.db`, WAL mode), Style, What this is, Working rules for Jules

### Community 67 - "dependencies"
Cohesion: 0.20
Nodes (10): dependencies, chart.js, clsx, firebase, lucide-react, next, react, react-chartjs-2 (+2 more)

### Community 68 - "manifest.json"
Cohesion: 0.20
Nodes (9): background_color, description, display, icons, name, orientation, short_name, start_url (+1 more)

### Community 69 - "TelegramRateLimiter"
Cohesion: 0.31
Nodes (4): TelegramRateLimiter, TokenBucket, test_r_ban_1_rate_limiter_routing(), test_r_ban_1_token_bucket_acquire()

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

### Community 75 - "_build_full_day_timetable"
Cohesion: 0.13
Nodes (12): _build_full_day_timetable(), _get_icons_from_output(), test_empirical_adjacent_period_boundary_minute(), test_empirical_after_all_classes_end(), test_empirical_before_classes_start(), test_empirical_inter_period_breaks(), test_empirical_lunch_break_transitions(), test_empirical_period_exact_end_time() (+4 more)

### Community 76 - "Project: KL-Sync System-Wide Verification & Quality Audit"
Cohesion: 0.22
Nodes (8): Architecture, Code Layout, Dashboard Routes Contract (`src/app/dashboard/*`), Feature Inventory, Interface Contracts, Milestones, Project: KL-Sync System-Wide Verification & Quality Audit, Quality Baseline Contract

### Community 77 - "🤝 Contributor Covenant Code of Conduct"
Cohesion: 0.22
Nodes (8): 🤝 Contributor Covenant Code of Conduct, 📩 Enforcement, 👮 Enforcement Responsibilities, 📋 Our Pledge, ⚖️ Our Standards, Positive Behaviors, 🌐 Scope, Unacceptable Behaviors

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

### Community 83 - "KnowledgeRetriever"
Cohesion: 0.16
Nodes (4): KnowledgeRetriever, test_knowledge_retriever_answer_stream(), test_retriever_answer_generation(), test_retriever_lexical_search()

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
Cohesion: 0.15
Nodes (4): AsyncSessionMock, setup_in_memory_backend_db(), override_async_session_local(), override_get_db()

### Community 90 - "frontend/AGENTS.md"
Cohesion: 0.33
Nodes (4): 📐 Architecture & Principles, 🛠️ Build & Test Commands, 📁 Directory Structure, 🚀 Project Overview

### Community 92 - "handlers.py"
Cohesion: 0.07
Nodes (15): apply_event(), extract(), _get_sender_name(), process_message(), handle_incoming_message(), ExtractedAcademicEvent, record_write(), redact_pii() (+7 more)

### Community 93 - "WorkspaceCircuitBreaker"
Cohesion: 0.20
Nodes (3): CircuitState, WorkspaceCircuitBreaker, test_r_ban_5_circuit_breaker_tripping()

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

### Community 104 - "run_ps_command"
Cohesion: 0.29
Nodes (3): run_ps_command(), test_run_daemon_parameters_defined(), test_run_daemon_syntax_valid_powershell_5_1()

### Community 105 - "ADR 0006: Zero Debt, Dialect-Aware Vector Retrieval, and Strict Backend Typing"
Cohesion: 0.25
Nodes (7): ADR 0006: Zero Debt, Dialect-Aware Vector Retrieval, and Strict Backend Typing, Confirmation & Verification, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Negative Consequences / Tradeoffs

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

### Community 111 - "bot.py"
Cohesion: 0.18
Nodes (5): ensure_frontend_out_fixture(), frozen_clock(), isolate_spark_db(), prevent_telegram_network(), mock_valid_settings()

### Community 113 - "test_empirical_erp_concurrency_lock_serialization"
Cohesion: 0.67
Nodes (3): test_empirical_erp_concurrency_lock_serialization(), mock_solve_captcha(), simulated_login_process()

### Community 117 - "Toast.tsx"
Cohesion: 0.38
Nodes (6): icons, styles, Toast(), ToastItem(), ToastProps, ToastData

### Community 144 - "ADR 0008: Adoption of Microsoft Agent Governance Principles and In-Process Turbovec RAG"
Cohesion: 0.22
Nodes (8): ADR 0008: Adoption of Microsoft Agent Governance Principles and In-Process Turbovec RAG, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Negative Consequences, Positive Consequences, Rationale & Comparison

### Community 148 - "asyncio"
Cohesion: 0.22
Nodes (4): test_fuzzy_routing_additional_invalid_commands(), test_fuzzy_routing_rejection_mandate(), test_fuzzy_routing_undo_and_slash_safety(), test_fuzzy_routing_valid_typos_mandate()

### Community 149 - "re"
Cohesion: 0.07
Nodes (25): check_adrs(), main(), main(), scan_motion(), extract_and_clean_urls(), sanitize_markdown(), attribute_course(), calculate_urgency() (+17 more)

### Community 152 - "backend/main.py"
Cohesion: 0.10
Nodes (18): get_db(), api_deadlines_say(), api_telegram_send_code(), api_telegram_verify(), api_timetable_override(), ChatRequest, get_spark_status(), get_task_status() (+10 more)

### Community 153 - "test_tier5_resilience.py"
Cohesion: 0.11
Nodes (4): MockHealthHandler, TestLogRotationEnforcement, _docker_available(), test_postgres_pgvector_content_hash()

### Community 154 - "src/main.py"
Cohesion: 0.17
Nodes (6): create_telegram_client(), _install_signal_handlers(), _listen(), main(), _sleep_or_stop(), supervise()

### Community 155 - "2. Phase-by-Phase Implementation Specifications"
Cohesion: 0.13
Nodes (12): _escape_like(), lifespan(), 1. Prioritization & Sequencing Strategy, 2. Phase-by-Phase Implementation Specifications, 3. End-to-End Verification Matrix, 4. Risks, Dependencies & Rollback Strategy, ChatLens Remediation Plan: Implementation Roadmap, Phase 1: Security Hardening & Authentication Enforcement (P0) (+4 more)

### Community 156 - "telegram.py"
Cohesion: 0.33
Nodes (3): _flatten_text(), _parse_message(), test_telegram_flatten_text_heterogeneous_structures()

### Community 159 - "no-mistakes"
Cohesion: 0.18
Nodes (10): Active validation-step boundary, Before you start, Escalate `ask-user` findings, Inspecting state, Intent is required, no-mistakes, Reading the output, Test-quality rule (+2 more)

### Community 164 - "devDependencies"
Cohesion: 0.20
Nodes (10): devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/node, @types/react, @types/react-dom (+2 more)

## Knowledge Gaps
- **8 isolated node(s):** `chatlens`, `tailwind-merge`, `tailwindcss`, `@tailwindcss/postcss`, `@types/node` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1161 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **70 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `2. Phase-by-Phase Implementation Specifications` connect `2. Phase-by-Phase Implementation Specifications` to `types.ts`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `handle_bot_command()` (e.g. with `Code Layout` and `1. Overview & Architecture`) actually correct?**
  _`handle_bot_command()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `chatlens`, `tailwind-merge`, `tailwindcss` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `types.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.12688172043010754 - nodes in this community are weakly interconnected._
- **Why does `Phase 2: Frontend Restoration & Static Export Configuration (P1)` connect `types.ts` to `2. Phase-by-Phase Implementation Specifications`, `Dashboard.tsx`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 39 inferred relationships involving `E2EClient` (e.g. with `e2e_client()` and `test_f1_api_chats_endpoint_routed()`) actually correct?**
  _`E2EClient` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Should `E2EClient` be split into smaller, more focused modules?**
  _Cohesion score 0.056261343012704176 - nodes in this community are weakly interconnected._