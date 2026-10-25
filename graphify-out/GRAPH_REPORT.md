# Graph Report - kind-faraday  (2026-10-25)

## Corpus Check
- 230 files · ~140,754 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 35 file(s) not represented in the graph (top: (none) 19, .example 3, .toml 3)

## Summary
- 2496 nodes · 5147 edges · 168 communities (115 shown, 53 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 384 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `db25b97d`
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
- test_bot.py
- test_run_daemon.py
- CalendarSync
- test_pairwise_backend_upload_to_celery_shared_volume
- _scrub_secrets
- test_challenger_m2_m3.py
- KLUERPClient
- test_backend_api.py
- handle_bot_command
- handle_bot_callback
- test_fuzz_parser.py
- backend/main.py
- google_token.py
- MessageDeduplicator
- ChatAnalyzer
- .meta_get
- run_reminders
- scrapers.py
- ChatLens & SPARK PA Assistant
- unittest_mock
- e2e/conftest.py
- telegram_live.py
- RegexParser
- GovernanceAuditLogger
- Path
- test_scheduler.py
- time
- verify_deployment.py
- test_e2e_remediation.py
- test_workspace_and_erp.py
- test_challenger_m2_m3_2.py
- os
- TestVerificationScriptErrorPaths
- compilerOptions
- run_ps_supervisor
- Home
- AIExtractor
- timetable/__init__.py
- InputGuard
- env.py
- components.test.tsx
- test_tier5_adversarial.py
- test_catch_up.py
- pytest
- sys
- Dashboard.tsx
- ChatLens v2.0
- 🛠️ Local Development Setup
- audit.py
- test_templates.py
- package.json
- TestHealthcheckFailureDetection
- save_messages
- run_mock_server
- ChatLens v2.0 Design System
- json
- test_erp_client_get_marks_session_recovery
- ADR 0002: Data-Instruction Separation & Prompt Injection Defense
- ADR 0003: Read-Only Telegram Ingestion Guardrail
- test_governance.py
- dependencies
- manifest.json
- handlers.py
- ADR 0001: Adoption of Awesome Dev Pipeline v2.2.0
- ADR 0004: Gemini AI Guardrails and Mandatory Holiday Confirmation
- ADR 0005: ChatLens Full-Stack Architecture, Vector Retrieval, and SPARK Bridge
- ADR 0007: ChatLens Frontend Restoration and Student Portal Isolation
- Verification Matrix
- _build_full_day_timetable
- Project: KL-Sync System-Wide Verification & Quality Audit
- 🤝 Contributor Covenant Code of Conduct
- AsyncSessionMock
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
- isolate_spark_db
- WorkspaceCircuitBreaker
- MessageList.tsx
- Ponytail Ultra Minimalism Rules
- vitest.config.mjs
- Ponytail Ultra Minimalism Rules
- feature_request.md
- pull_request_template.md
- 🛡️ Security Policy
- test_b5_empty_tables_handled
- Ponytail Ultra Coding Standards (Ponytail v5.1 Alignment)
- TypeScript & Frontend Engineering Rules (ChatLens v2)
- asyncio
- ADR 0006: Zero Debt, Dialect-Aware Vector Retrieval, and Strict Backend Typing
- test_bunk_command_fast_path_from_cache
- frontend/README.md
- Security Policy
- TypeScript & Frontend Engineering Rules (ChatLens v2)
- KL University ERP Integration (KLU ERP)
- mock_valid_settings
- ADR Scaffolding Workflow (`/adr`)
- test_empirical_erp_concurrency_lock_serialization
- ADR Scaffolding Command (`/adr`)
- SPARK PA Daemon Deployment
- Toast.tsx
- test_performance_optimization.py
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
- .get
- test_briefing_command
- scripts
- templates.py
- TestSecretMaskingIntegrity
- re
- export_prompt.py
- test_tier5_resilience.py
- src/main.py
- setup_test_env
- test_debounce_delta_mathematical_precision_sweep
- setup_test_env
- HTMLTableParser
- no-mistakes
- PolicyEngine
- test_challenger_m1.py
- test_compliance_guardrails.py
- retry_error_handler
- devDependencies
- isolate_env
- extract_and_clean_urls
- post

## God Nodes (most connected - your core abstractions)
1. `handle_bot_command()` - 81 edges
2. `E2EClient` - 53 edges
3. `MessageDeduplicator` - 42 edges
4. `get_connection()` - 42 edges
5. `handle_bot_callback()` - 41 edges
6. `run_daemon()` - 38 edges
7. `RegexParser` - 31 edges
8. `format_day_schedule()` - 30 edges
9. `Message` - 29 edges
10. `FakeTelegramClient` - 28 edges

## Surprising Connections (you probably didn't know these)
- `Positive Consequences` --references--> `UntrustedInput`  [INFERRED]
  adr/0008-microsoft-agent-governance-and-turbovec-rag.md → src/governance/guards.py
- `Dashboard Routes Contract (`src/app/dashboard/*`)` --references--> `timetable()`  [INFERRED]
  chatlens-v2/frontend/PROJECT.md → tests/test_timetable.py
- `3. Template Reference Implementations` --references--> `get_standard_navigation_buttons()`  [INFERRED]
  docs/MESSAGE_FORMATTING_RULES.md → src/formatting/templates.py
- `Reading the output` --references--> `status()`  [INFERRED]
  .agents/skills/no-mistakes/SKILL.md → chatlens-v2/backend/main.py
- `3.4 Interactive Bot Interface & Proactive Reminders` --references--> `run_reminders()`  [INFERRED]
  README.md → src/main.py

## Import Cycles
- None detected.

## Communities (168 total, 53 thin omitted)

### Community 0 - "run_daemon"
Cohesion: 0.23
Nodes (22): bot_callback_poll(), run_daemon(), guard(), test_bot_callback_poll_no_token_returns_immediately(), test_bot_callback_poll_runs_in_dry_mode(), test_bot_callback_poll_undo_routing(), test_daemon_clean_client_disconnect(), test_daemon_clean_shutdown() (+14 more)

### Community 1 - "mock_bot_answer_callback"
Cohesion: 0.22
Nodes (3): isolate_test_environment(), mock_bot_answer_callback(), mock_bot_send()

### Community 2 - "types.ts"
Cohesion: 0.16
Nodes (16): DeadlinesModalProps, Sidebar(), SidebarProps, TimetableModalProps, AcademicMilestone, AiCardData, Chat, DeadlinesData (+8 more)

### Community 3 - "E2EClient"
Cohesion: 0.06
Nodes (22): E2EClient, test_b1_long_uri_handling(), test_b1_malformed_url_percent_encoding(), test_b1_nonexistent_api_route_404(), test_b1_repeated_slashes_normalization(), test_b1_unsupported_http_method(), test_b2_deep_nested_spa_route(), test_b2_head_request_on_static_asset() (+14 more)

### Community 4 - "pytest"
Cohesion: 0.14
Nodes (18): AcademicCalendar, get_milestone_date(), load_calendar(), build_briefing(), classes_can_skip(), classes_needed(), fetch_briefing_inputs(), format_bunk_calculator() (+10 more)

### Community 5 - "asyncio"
Cohesion: 0.05
Nodes (18): test_tier1_fuzzy_command_routing(), test_tier1_standalone_slash_trigger(), test_tier1_today_command_happy_path(), test_tier1_tomorrow_command_happy_path(), test_tier2_all_periods_cancelled(), test_tier2_empty_schedule_on_sunday(), test_tier2_time_boundary_early_morning(), test_tier2_time_boundary_late_night() (+10 more)

### Community 6 - "test_tier1_features.py"
Cohesion: 0.05
Nodes (22): lint_migrations(), main(), test_f1_caddyfile_routing_contracts(), test_f1_caddyfile_tls_and_encoding(), test_f1_ws_routing_configuration(), test_f2_nginx_conf_caching_and_spa(), test_f2_no_legacy_basepath_in_static_export(), test_f2_relative_origin_api_calls() (+14 more)

### Community 7 - "test_bot.py"
Cohesion: 0.08
Nodes (26): BotClient, BotConflictError, BotError, BotRateLimitedError, _extract_payload(), mock_bot(), mock_request(), test_bot_400_no_retry() (+18 more)

### Community 8 - "test_run_daemon.py"
Cohesion: 0.08
Nodes (20): test_difflib_similarity_ratios_mathematical_oracle(), run_ps_command(), run_ps_script(), test_background_duplicate_suppression(), test_healthcheck_fails_when_daemon_stopped(), test_healthcheck_fails_when_database_corrupted(), test_healthcheck_fails_when_database_missing(), test_healthcheck_fails_when_heartbeat_missing() (+12 more)

### Community 9 - "CalendarSync"
Cohesion: 0.14
Nodes (13): CalendarSync, TasksSync, test_create_holiday_event_suppress_reminders(), test_update_class_room_patch_existing(), test_calendar_cancel_class(), test_calendar_missing_event(), test_calendar_override_marker_room(), test_calendar_period_window() (+5 more)

### Community 11 - "_scrub_secrets"
Cohesion: 0.12
Nodes (15): Ingestion Boundaries, Privacy & Logging Standards, Security & Privacy Rules (ChatLens & SPARK PA), configure_logging(), _redact_str(), _scrub_secrets(), _scrub_value(), _sentry_before_send() (+7 more)

### Community 12 - "test_challenger_m2_m3.py"
Cohesion: 0.12
Nodes (9): clean_daemon_environment(), run_ps_script(), test_supervisor_healthcheck_corrupt_db(), test_supervisor_healthcheck_healthy_db(), test_supervisor_healthcheck_missing_db(), test_supervisor_status_when_running(), test_supervisor_status_when_stopped(), test_supervisor_stop_when_pid_file_exists() (+1 more)

### Community 13 - "KLUERPClient"
Cohesion: 0.11
Nodes (5): KLUERPClient, test_empirical_erp_session_expiration_markers(), test_erp_client_is_session_expired(), test_erp_client_marks_cache_offline_fallback(), test_erp_client_status_codes_session_expired()

### Community 14 - "test_backend_api.py"
Cohesion: 0.08
Nodes (22): delete_chat(), Message, test_analyzer_ask_fences_untrusted_transcript(), test_api_status_probe_degraded(), test_ask_prompt_fencing(), test_chat_deletion(), test_chat_export_json_and_csv(), test_chats_and_messages_lifecycle() (+14 more)

### Community 15 - "handle_bot_command"
Cohesion: 0.13
Nodes (30): handle_bot_command(), register_handlers(), test_apply_event_calendar_conflict(), test_handle_bot_callback_cmd_attendance(), test_handle_bot_callback_cmd_deadlines(), test_handle_bot_callback_cmd_status(), test_handle_bot_callback_cmd_today(), test_handle_bot_callback_unauthorized_ignored() (+22 more)

### Community 16 - "handle_bot_callback"
Cohesion: 0.09
Nodes (18): handle_bot_callback(), RequestRecorder, test_bot_send_custom_buttons_1d(), test_bot_send_custom_buttons_2d(), test_bot_send_default_quick_buttons(), test_bot_send_empty_buttons_suppresses_reply_markup(), test_bot_set_my_commands_exact_registration(), test_callback_answer_failure_resilience() (+10 more)

### Community 17 - "test_fuzz_parser.py"
Cohesion: 0.06
Nodes (32): parse_and_save_sync(), _flatten_text(), _parse_message(), parse_telegram_export(), _parse_datetime(), parse_whatsapp_export(), test_telegram_parser_full_account(), test_telegram_parser_single_chat() (+24 more)

### Community 18 - "backend/main.py"
Cohesion: 0.07
Nodes (33): api_analyze(), api_ask(), api_auth_me(), api_chat_insights(), api_deadlines(), api_deadlines_say(), api_global_summarize(), api_monitoring_status() (+25 more)

### Community 21 - "ChatAnalyzer"
Cohesion: 0.10
Nodes (4): ChatAnalyzer, _format_messages(), _redact_forbidden_ids(), test_empirical_pii_masking_zero_raw_digits()

### Community 22 - ".meta_get"
Cohesion: 0.22
Nodes (4): test_r_ban_2_consent_via_start_allows_dm(), test_r_ban_3_startup_debounce_logic(), test_debounce_evaluation_scenarios(), test_meta_table_crud_and_concurrency()

### Community 23 - "run_reminders"
Cohesion: 0.10
Nodes (18): AGENTS.md — SPARK PA daemon (`src/`), Commands, Environment variables, Instance-specific academic data, Invariants (target behavior; each task prompt says which parts already exist), SQLite state (`SPARK_DB`, default `spark.db`, WAL mode), Style, What this is (+10 more)

### Community 24 - "scrapers.py"
Cohesion: 0.14
Nodes (13): parse_attendance_records(), parse_cgpa_records(), parse_fee_records(), parse_generic_tables(), parse_marks_records(), parse_timetable_records(), test_parse_attendance_metrics(), test_parse_cgpa() (+5 more)

### Community 25 - "ChatLens & SPARK PA Assistant"
Cohesion: 0.05
Nodes (38): 1. System Architecture & Trust Boundaries, 2.1 Ingestion Layer (Telethon Listener), 2.2 Parsing & LLM Layer (Regex & Gemini), 2.3 Workspace Synchronization Layer (Calendar, Tasks, Sheets), 2.4 State & Persistence Layer (SQLite Database), 2.5 Supply Chain & CI/CD Layer, 2. STRIDE Threat Analysis by Component, STRIDE Threat Model: ChatLens & SPARK PA Assistant (+30 more)

### Community 26 - "unittest_mock"
Cohesion: 0.14
Nodes (5): test_scenario_1_stack_health_probe_convergence(), test_scenario_2_complete_web_user_journey(), test_scenario_3_chat_upload_and_analysis_lifecycle(), test_scenario_4_spark_daemon_restart_and_state_recovery(), test_scenario_5_reverse_proxy_domain_failover_and_tls_config()

### Community 27 - "e2e/conftest.py"
Cohesion: 0.06
Nodes (13): compose_config(), e2e_client(), in_memory_db(), isolated_spark_db(), nginx_config(), ComposeParser, NginxConfParser, setup_in_memory_backend_db() (+5 more)

### Community 28 - "telegram_live.py"
Cohesion: 0.16
Nodes (9): check_status(), _fetch(), fetch_telegram_chats(), _get_client(), send_code(), send_telegram_code_sync(), _sender_name(), verify_code() (+1 more)

### Community 29 - "RegexParser"
Cohesion: 0.08
Nodes (27): decide(), Decision, extract(), process_message(), handle_incoming_message(), RegexParser, test_empirical_regex_parser_room_variations(), test_decide_invalid() (+19 more)

### Community 30 - "GovernanceAuditLogger"
Cohesion: 0.14
Nodes (4): GovernanceAuditLogger, PolicyVerdict, test_governance_audit_logger_roundtrip(), test_quarantine_console_commands()

### Community 32 - "test_scheduler.py"
Cohesion: 0.24
Nodes (11): next_run(), run_briefing(), run_heartbeat(), guard(), test_briefing_idempotent(), test_briefing_retry_on_failure(), test_heartbeat_interval(), test_next_run_after_target() (+3 more)

### Community 33 - "time"
Cohesion: 0.15
Nodes (9): run_concurrent_sqlite_benchmark(), worker_fn(), run_streaming_ttft_benchmark(), run_timetable_l1_cache_benchmark(), run_today_e2e_benchmark(), run_parser_benchmark(), run_timetable_benchmark(), main() (+1 more)

### Community 34 - "verify_deployment.py"
Cohesion: 0.10
Nodes (11): detect_archetype(), main(), check_compose_file(), check_env_template(), check_live_endpoints(), check_supporting_configs(), log_info(), log_pass() (+3 more)

### Community 35 - "test_e2e_remediation.py"
Cohesion: 0.12
Nodes (7): test_tier1_inline_callback_query_execution(), test_tier1_startup_debounce_cooldown(), test_tier2_debounce_boundary_exact_seconds(), test_tier2_sqlite_wal_and_meta_concurrency(), test_tier3_debounce_with_corrupted_meta_timestamp(), test_tier3_inline_callback_triggers_schedule_with_buttons(), test_tier3_inline_callback_triggers_tomorrow_static_icons()

### Community 36 - "test_workspace_and_erp.py"
Cohesion: 0.19
Nodes (7): SheetsLogger, test_empirical_sheets_logger_silent_degradation(), test_sheets_logger_heartbeat_configured_sheet_id(), test_sheets_logger_heartbeat_empty_sheet_id(), test_sheets_logger_heartbeat_whitespace_sheet_id(), test_sheets_logger_init_preserves_empty_string(), test_sheets_logger_unconfigured_guard_and_skips()

### Community 37 - "test_challenger_m2_m3_2.py"
Cohesion: 0.10
Nodes (9): make_clock_mock(), mock_daemon_settings(), test_debounce_bot_transmission_failure_preserves_prior_timestamp(), test_debounce_corrupted_timestamp_recovery(), test_debounce_first_boot_no_prior_record(), test_debounce_threshold_899_9_seconds_suppressed(), test_debounce_threshold_900_0_exact_boundary_allowed(), test_debounce_threshold_900_1_seconds_allowed() (+1 more)

### Community 38 - "os"
Cohesion: 0.15
Nodes (7): get_db(), _authentication_required(), get_current_user(), require_current_user(), lifespan(), test_firebase_auth_token_validation(), test_mock_firebase_token_is_rejected_outside_test_environment()

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 42 - "Home"
Cohesion: 0.16
Nodes (17): Home(), DeadlinesModal(), EXAM_SCHEDULE, ExamPrepModal(), ExamPrepModalProps, EXPERIMENTS, TimetableModal(), fetchJSON() (+9 more)

### Community 43 - "AIExtractor"
Cohesion: 0.07
Nodes (29): Invariants & Architecture, Python Engineering Rules (ChatLens & SPARK PA), Runtime & Toolchain, Architecture & Conventions, CLAUDE.md — ChatLens Assistant Guide, Essential Commands, Invariants & Architecture, Python Engineering Rules (ChatLens & SPARK PA) (+21 more)

### Community 44 - "timetable/__init__.py"
Cohesion: 0.24
Nodes (8): ExtractedAcademicEvent, clear_cache(), parse_periods(), validate(), Verdict, test_timetable_scenarios(), test_validate_missing_or_sample_timetable(), test_validate_non_applicable_intents()

### Community 45 - "InputGuard"
Cohesion: 0.13
Nodes (6): 2.6 Agent Governance & Semantic Vector Memory Layer (Microsoft AGT & Turbovec), InputGuard, test_benign_academic_messages_not_quarantined(), test_prompt_injection_detection(), test_sanitize_and_wrap_quarantines_untrusted_input(), test_unicode_evasion_and_zero_width_injection_detected()

### Community 46 - "env.py"
Cohesion: 0.14
Nodes (6): do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), run_sync_migrations(), Base

### Community 47 - "components.test.tsx"
Cohesion: 0.17
Nodes (15): AiCard(), AiCardProps, AskBar(), AskBarProps, FormatAi(), renderInline(), ImportModal(), ImportModalProps (+7 more)

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
Cohesion: 0.19
Nodes (5): main(), harvest_debt(), main(), update_debt_file(), main()

### Community 52 - "Dashboard.tsx"
Cohesion: 0.19
Nodes (13): ChatHeader(), ChatHeaderProps, insightButtons, chartOptions(), Dashboard(), DashboardProps, DAY_LABELS, SkeletonCard() (+5 more)

### Community 53 - "ChatLens v2.0"
Cohesion: 0.15
Nodes (12): 1. Architecture Overview, 2. Directory Structure, 3. Environment Variables, 4. Setup and Execution, 5. Key REST API Endpoints, Backend (`chatlens-v2/backend/.env`), ChatLens v2.0, Frontend (`chatlens-v2/frontend/.env.local`) (+4 more)

### Community 54 - "🛠️ Local Development Setup"
Cohesion: 0.15
Nodes (12): 📥 1. Fork & Clone, 🔧 2. Configuration, 📦 3. Run External Services, 🐍 4. Backend Setup, ⚛️ 5. Frontend Setup, 🤝 Contributing to ChatLens, ⚛️ Frontend Linting, 🛠️ Local Development Setup (+4 more)

### Community 55 - "audit.py"
Cohesion: 0.17
Nodes (3): UntrustedInput, ActionTier, PolicyEvaluationResult

### Community 56 - "test_templates.py"
Cohesion: 0.18
Nodes (10): attribute_course(), calculate_urgency(), get_standard_navigation_buttons(), group_and_consolidate_notices(), render_deadlines_card(), test_attribute_course_known_and_heuristics(), test_calculate_urgency_relative_dates(), test_get_standard_navigation_buttons() (+2 more)

### Community 57 - "package.json"
Cohesion: 0.10
Nodes (20): eslintConfig, name, overrides, baseline-browser-mapping, browserslist, @grpc/grpc-js, zod, private (+12 more)

### Community 59 - "save_messages"
Cohesion: 0.09
Nodes (9): Positive Consequences, DummyCelery, generate_embeddings_batch(), parse_file_task(), save_messages(), generate_embedding(), generate_embeddings_batch(), api_telegram_sync_live() (+1 more)

### Community 61 - "ChatLens v2.0 Design System"
Cohesion: 0.18
Nodes (10): 1. Intent, 2. Colors, 3. Typography, 4. Spacing, 5. Motion (motion-anything), 6. Shapes & Borders, 7. Human-Centric Principles, 8. Icons (+2 more)

### Community 62 - "json"
Cohesion: 0.20
Nodes (25): apply_event(), handle_undo_command(), get_connection(), clean_db(), mock_bot(), test_apply_event_writes_audit(), test_confirm_flow_approve(), test_confirm_flow_bot_edit_without_msg_id() (+17 more)

### Community 63 - "test_erp_client_get_marks_session_recovery"
Cohesion: 0.22
Nodes (6): test_erp_client_fetch_page_session_recovery(), mock_send(), test_erp_client_get_marks_session_recovery(), test_erp_client_login_lock_serialization(), concurrent_login(), fake_login_internal()

### Community 64 - "ADR 0002: Data-Instruction Separation & Prompt Injection Defense"
Cohesion: 0.20
Nodes (9): ADR 0002: Data-Instruction Separation & Prompt Injection Defense, Architecture & Mitigations, Confirmation & Verification, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Negative Consequences / Tradeoffs (+1 more)

### Community 65 - "ADR 0003: Read-Only Telegram Ingestion Guardrail"
Cohesion: 0.20
Nodes (9): ADR 0003: Read-Only Telegram Ingestion Guardrail, Confirmation & Verification, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Implementation Guarantees, Negative Consequences / Tradeoffs (+1 more)

### Community 66 - "test_governance.py"
Cohesion: 0.10
Nodes (9): test_adversarial_injection_quarantined_in_pipeline(), test_dry_mode_rejects_all_external_writes(), test_gemini_derived_events_always_require_hitl(), test_high_impact_holiday_and_cancellation_always_mandates_hitl(), test_owner_bypasses_injection_quarantine(), test_quarantined_input_blocks_all_actions(), test_room_override_in_live_mode_auto_approved_only_when_regex_and_validated(), test_tier_0_read_allowed_in_all_modes() (+1 more)

### Community 67 - "dependencies"
Cohesion: 0.20
Nodes (10): dependencies, chart.js, clsx, firebase, lucide-react, next, react, react-chartjs-2 (+2 more)

### Community 68 - "manifest.json"
Cohesion: 0.20
Nodes (9): background_color, description, display, icons, name, orientation, short_name, start_url (+1 more)

### Community 69 - "handlers.py"
Cohesion: 0.07
Nodes (3): redact_pii(), guard(), test_r_ban_4_pii_redaction_patterns()

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
Cohesion: 0.10
Nodes (26): format_day_schedule(), Meta, Slot, Timetable, test_empirical_timetable_room_normalization(), _build_full_day_timetable(), _get_icons_from_output(), test_empirical_adjacent_period_boundary_minute() (+18 more)

### Community 76 - "Project: KL-Sync System-Wide Verification & Quality Audit"
Cohesion: 0.22
Nodes (8): Architecture, Code Layout, Dashboard Routes Contract (`src/app/dashboard/*`), Feature Inventory, Interface Contracts, Milestones, Project: KL-Sync System-Wide Verification & Quality Audit, Quality Baseline Contract

### Community 77 - "🤝 Contributor Covenant Code of Conduct"
Cohesion: 0.22
Nodes (8): 🤝 Contributor Covenant Code of Conduct, 📩 Enforcement, 👮 Enforcement Responsibilities, 📋 Our Pledge, ⚖️ Our Standards, Positive Behaviors, 🌐 Scope, Unacceptable Behaviors

### Community 78 - "AsyncSessionMock"
Cohesion: 0.15
Nodes (4): AsyncSessionMock, in_memory_db(), override_async_session_local(), override_get_db()

### Community 79 - "Security Audit Areas"
Cohesion: 0.25
Nodes (7): 1. Zero Hardcoded Secrets, 2. PII Masking & Privacy Scrubber, 3. SQL Injection Resistance, 4. Adversarial Prompt Injection Defense, 5. Ingress & Egress Invariants, AgentShield Security Scan Skill (`security-scan`), Security Audit Areas

### Community 80 - "layout.tsx"
Cohesion: 0.29
Nodes (3): nextConfig, metadata, next

### Community 81 - "Definition of Done (Addy Osmani agent-skills Alignment)"
Cohesion: 0.29
Nodes (6): 1. Correctness, 2. Code Quality & Minimalism (Ponytail Ultra), 3. Integration & Persistence, 4. Security & Guardrails (AgentShield), 5. Technical Debt & Documentation, Definition of Done (Addy Osmani agent-skills Alignment)

### Community 82 - "Required Format"
Cohesion: 0.29
Nodes (6): 1. Changed, 2. Decisions, 3. Not done, 4. Verification Evidence, Pull Request Workflow (`/pr`), Required Format

### Community 83 - "KnowledgeRetriever"
Cohesion: 0.09
Nodes (6): KnowledgeRetriever, test_knowledge_retriever_answer_stream(), test_retriever_answer_generation(), test_retriever_lexical_search(), test_retriever_load_chunks(), test_retriever_turbovec_cache_persistence_roundtrip()

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
Cohesion: 0.18
Nodes (3): AsyncSessionMock, override_async_session_local(), override_get_db()

### Community 90 - "frontend/AGENTS.md"
Cohesion: 0.33
Nodes (4): 📐 Architecture & Principles, 🛠️ Build & Test Commands, 📁 Directory Structure, 🚀 Project Overview

### Community 92 - "isolate_spark_db"
Cohesion: 0.18
Nodes (4): ensure_frontend_out_fixture(), frozen_clock(), isolate_spark_db(), prevent_telegram_network()

### Community 93 - "WorkspaceCircuitBreaker"
Cohesion: 0.20
Nodes (4): CircuitState, WorkspaceCircuitBreaker, test_r_ban_5_apply_event_queues_when_circuit_open(), test_r_ban_5_circuit_breaker_tripping()

### Community 94 - "MessageList.tsx"
Cohesion: 0.36
Nodes (8): formatDate(), formatTime(), isGrouped(), isSameDay(), MessageList(), MessageListProps, SKELETON_WIDTHS, Message

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

### Community 101 - "test_b5_empty_tables_handled"
Cohesion: 0.22
Nodes (4): test_b5_corrupt_sqlite_integrity_failure(), test_b5_empty_tables_handled(), test_b5_missing_db_returns_offline_status(), test_b5_readonly_db_access()

### Community 102 - "Ponytail Ultra Coding Standards (Ponytail v5.1 Alignment)"
Cohesion: 0.50
Nodes (3): 1. The Ladder of Abstraction, 2. Surgical Modifications & Hygiene, Ponytail Ultra Coding Standards (Ponytail v5.1 Alignment)

### Community 103 - "TypeScript & Frontend Engineering Rules (ChatLens v2)"
Cohesion: 0.50
Nodes (3): Code Standards & Accessibility, Framework & Architecture, TypeScript & Frontend Engineering Rules (ChatLens v2)

### Community 104 - "asyncio"
Cohesion: 0.22
Nodes (4): test_fuzzy_routing_additional_invalid_commands(), test_fuzzy_routing_rejection_mandate(), test_fuzzy_routing_undo_and_slash_safety(), test_fuzzy_routing_valid_typos_mandate()

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

### Community 113 - "test_empirical_erp_concurrency_lock_serialization"
Cohesion: 0.40
Nodes (4): test_empirical_erp_concurrency_lock_serialization(), mock_solve_captcha(), simulated_login_process(), test_empirical_erp_session_expiry_triggers_ocr_reauth()

### Community 117 - "Toast.tsx"
Cohesion: 0.38
Nodes (6): icons, styles, Toast(), ToastItem(), ToastProps, ToastData

### Community 118 - "test_performance_optimization.py"
Cohesion: 0.11
Nodes (6): run_simd_vector_benchmark(), run_turbovec_benchmark(), ContiguousVectorBuffer, test_contiguous_vector_buffer_search(), test_sqlite_pragmas_and_concurrent_writes(), write_worker()

### Community 144 - "ADR 0008: Adoption of Microsoft Agent Governance Principles and In-Process Turbovec RAG"
Cohesion: 0.22
Nodes (8): ADR 0008: Adoption of Microsoft Agent Governance Principles and In-Process Turbovec RAG, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Negative Consequences, Positive Consequences, Rationale & Comparison

### Community 145 - ".get"
Cohesion: 0.10
Nodes (9): CaseInsensitiveHeaderDict, E2EResponse, test_f1_api_chats_endpoint_routed(), test_f1_api_healthz_routes_to_backend(), test_f1_root_request_routes_to_frontend(), test_f2_spa_route_fallback(), test_f2_static_asset_loads_cleanly(), test_f6_async_task_status_endpoint() (+1 more)

### Community 148 - "scripts"
Cohesion: 0.33
Nodes (6): scripts, build, dev, lint, start, test

### Community 149 - "templates.py"
Cohesion: 0.16
Nodes (9): sanitize_markdown(), render_attendance_card(), render_day_schedule(), render_proactive_reminder(), render_status_card(), test_render_attendance_card(), test_render_proactive_reminder(), test_render_status_card() (+1 more)

### Community 151 - "re"
Cohesion: 0.25
Nodes (4): check_adrs(), main(), main(), scan_motion()

### Community 154 - "src/main.py"
Cohesion: 0.17
Nodes (6): create_telegram_client(), _install_signal_handlers(), _listen(), main(), _sleep_or_stop(), supervise()

### Community 159 - "no-mistakes"
Cohesion: 0.18
Nodes (10): Active validation-step boundary, Before you start, Escalate `ask-user` findings, Inspecting state, Intent is required, no-mistakes, Reading the output, Test-quality rule (+2 more)

### Community 160 - "PolicyEngine"
Cohesion: 0.21
Nodes (3): PolicyEngine, test_action_tier_classification(), test_cryptographic_state_token_validation()

### Community 161 - "test_challenger_m1.py"
Cohesion: 0.10
Nodes (12): get_effective_slots(), load(), test_course_code_shadowing_adversarial_probe(), test_every_day_of_the_week_timetable_coverage(), test_period_6_omission(), test_simultaneous_room_override_injection_today_and_tomorrow(), test_slot_note_generation_across_weeks_and_types(), test_today_and_tomorrow_bot_commands_simultaneously() (+4 more)

### Community 162 - "test_compliance_guardrails.py"
Cohesion: 0.18
Nodes (6): _get_sender_name(), TelegramRateLimiter, TokenBucket, test_r_ban_1_rate_limiter_routing(), test_r_ban_1_token_bucket_acquire(), test_r_ban_4_sender_name_redaction()

### Community 164 - "devDependencies"
Cohesion: 0.20
Nodes (10): devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/node, @types/react, @types/react-dom (+2 more)

### Community 171 - "post"
Cohesion: 0.36
Nodes (6): api_telegram_send_code(), api_telegram_verify(), handle_upload(), import_chat(), upload_telegram(), upload_whatsapp()

## Knowledge Gaps
- **8 isolated node(s):** `chatlens`, `tailwind-merge`, `tailwindcss`, `@tailwindcss/postcss`, `@types/node` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1119 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **53 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `handle_bot_command()` connect `handle_bot_command` to `run_daemon`, `pytest`, `asyncio`, `test_run_daemon.py`, `handle_bot_callback`, `test_briefing_command`, `templates.py`, `.meta_get`, `src/main.py`, `GovernanceAuditLogger`, `time`, `test_challenger_m1.py`, `test_compliance_guardrails.py`, `test_e2e_remediation.py`, `AIExtractor`, `test_catch_up.py`, `test_templates.py`, `json`, `test_governance.py`, `handlers.py`, `_build_full_day_timetable`, `asyncio`, `test_bunk_command_fast_path_from_cache`, `test_performance_optimization.py`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `handle_bot_command()` (e.g. with `Code Layout` and `PolicyVerdict`) actually correct?**
  _`handle_bot_command()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `chatlens`, `tailwind-merge`, `tailwindcss` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `E2EClient` be split into smaller, more focused modules?**
  _Cohesion score 0.06294326241134751 - nodes in this community are weakly interconnected._
- **Why does `decide()` connect `RegexParser` to `ChatLens & SPARK PA Assistant`, `AIExtractor`, `handlers.py`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Are the 39 inferred relationships involving `E2EClient` (e.g. with `e2e_client()` and `test_f1_api_chats_endpoint_routed()`) actually correct?**
  _`E2EClient` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Should `pytest` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._