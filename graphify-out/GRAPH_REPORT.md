# Graph Report - kind-faraday  (2026-10-25)

## Corpus Check
- 234 files · ~146,879 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 35 file(s) not represented in the graph (top: (none) 19, .example 3, .toml 3)

## Summary
- 2553 nodes · 5216 edges · 171 communities (116 shown, 55 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 400 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cfacabda`
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
- sqlite3
- ChatLens Full-System Engineering Audit Report
- test_challenger_m2_m3.py
- KLUERPClient
- test_backend_api.py
- handle_bot_command
- handle_bot_callback
- celery_worker.py
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
- RegexParser
- GovernanceAuditLogger
- Path
- test_scheduler.py
- time
- verify_deployment.py
- decide
- test_workspace_and_erp.py
- test_challenger_m2_m3_2.py
- os
- TestVerificationScriptErrorPaths
- compilerOptions
- run_ps_supervisor
- Home
- AIExtractor
- datetime
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
- today_ist
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
- test_challenger_empirical.py
- test_compliance_guardrails.py
- 2. STRIDE Threat Analysis by Component
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
- typing
- test_briefing_command
- get_standard_navigation_buttons
- templates.py
- TestSecretMaskingIntegrity
- re
- ai_extractor.py
- test_tier5_resilience.py
- src/main.py
- 2. Phase-by-Phase Implementation Specifications
- ActionTier
- setup_test_env
- HTMLTableParser
- no-mistakes
- PolicyEngine
- test_today_and_tomorrow_bot_commands_simultaneously
- setup_test_env
- retry_error_handler
- devDependencies
- Test Infrastructure Specification: ChatLens PA Daemon Remediation
- test_db_integration.py
- test_run_daemon_no_legacy_get_process_commandline
- extract_and_clean_urls
- detect_archetype.py
- test_every_day_of_the_week_timetable_coverage

## God Nodes (most connected - your core abstractions)
1. `handle_bot_command()` - 82 edges
2. `E2EClient` - 53 edges
3. `handle_bot_callback()` - 42 edges
4. `get_connection()` - 42 edges
5. `MessageDeduplicator` - 42 edges
6. `run_daemon()` - 38 edges
7. `RegexParser` - 31 edges
8. `format_day_schedule()` - 30 edges
9. `Message` - 29 edges
10. `KLUERPClient` - 28 edges

## Surprising Connections (you probably didn't know these)
- `Phase 1: Security Hardening & Authentication Enforcement (P0)` --references--> `get_current_user()`  [INFERRED]
  docs/audits/chatlens-remediation-plan.md → chatlens-v2/backend/firebase_auth.py
- `5. Root-Cause Analysis: Confirmed Causes vs. Hypotheses` --references--> `get_current_user()`  [INFERRED]
  docs/audits/chatlens-system-audit.md → chatlens-v2/backend/firebase_auth.py
- `Reading the output` --references--> `status()`  [INFERRED]
  .agents/skills/no-mistakes/SKILL.md → chatlens-v2/backend/main.py
- `Positive Consequences` --references--> `UntrustedInput`  [INFERRED]
  adr/0008-microsoft-agent-governance-and-turbovec-rag.md → src/governance/guards.py
- `3.4 Interactive Bot Interface & Proactive Reminders` --references--> `run_reminders()`  [INFERRED]
  README.md → src/main.py

## Import Cycles
- None detected.

## Communities (171 total, 55 thin omitted)

### Community 0 - "run_daemon"
Cohesion: 0.15
Nodes (24): bot_callback_poll(), run_daemon(), run_heartbeat(), FakeTelegramClient, guard(), test_bot_callback_poll_no_token_returns_immediately(), test_bot_callback_poll_runs_in_dry_mode(), test_bot_callback_poll_undo_routing() (+16 more)

### Community 2 - "types.ts"
Cohesion: 0.13
Nodes (25): Home(), DeadlinesModal(), DeadlinesModalProps, Sidebar(), SidebarProps, SparkStatusModal(), SparkStatusModalProps, TimetableModal() (+17 more)

### Community 3 - "E2EClient"
Cohesion: 0.06
Nodes (23): E2EClient, test_b1_long_uri_handling(), test_b1_malformed_url_percent_encoding(), test_b1_nonexistent_api_route_404(), test_b1_repeated_slashes_normalization(), test_b1_unsupported_http_method(), test_b2_deep_nested_spa_route(), test_b2_head_request_on_static_asset() (+15 more)

### Community 4 - "pytest"
Cohesion: 0.20
Nodes (15): build_briefing(), classes_can_skip(), classes_needed(), fetch_briefing_inputs(), format_bunk_calculator(), guard(), test_build_briefing_attendance(), test_build_briefing_empty() (+7 more)

### Community 5 - "asyncio"
Cohesion: 0.05
Nodes (26): test_tier1_fuzzy_command_routing(), test_tier1_inline_callback_query_execution(), test_tier1_standalone_slash_trigger(), test_tier1_startup_debounce_cooldown(), test_tier1_timetable_fallback_happy_path(), test_tier1_today_command_happy_path(), test_tier1_tomorrow_command_happy_path(), test_tier2_all_periods_cancelled() (+18 more)

### Community 6 - "test_tier1_features.py"
Cohesion: 0.04
Nodes (23): lint_migrations(), main(), test_f1_api_chats_endpoint_routed(), test_f1_api_healthz_routes_to_backend(), test_f1_caddyfile_routing_contracts(), test_f1_caddyfile_tls_and_encoding(), test_f1_ws_routing_configuration(), test_f2_nginx_conf_caching_and_spa() (+15 more)

### Community 7 - "BotClient"
Cohesion: 0.08
Nodes (27): BotClient, BotConflictError, BotError, BotRateLimitedError, _extract_payload(), mock_bot(), mock_request(), test_bot_400_no_retry() (+19 more)

### Community 8 - "test_run_daemon.py"
Cohesion: 0.10
Nodes (16): main(), run_ps_script(), test_background_duplicate_suppression(), test_healthcheck_fails_when_daemon_stopped(), test_healthcheck_fails_when_database_corrupted(), test_healthcheck_fails_when_database_missing(), test_healthcheck_fails_when_heartbeat_missing(), test_healthcheck_fails_when_heartbeat_stale() (+8 more)

### Community 9 - "logging.py"
Cohesion: 0.05
Nodes (30): _redact_forbidden_ids(), Ingestion Boundaries, Privacy & Logging Standards, Security & Privacy Rules (ChatLens & SPARK PA), configure_logging(), _redact_str(), _scrub_secrets(), _scrub_value() (+22 more)

### Community 10 - "sqlite3"
Cohesion: 0.08
Nodes (12): test_f8_backend_spark_status_bridge(), test_f8_spark_sqlite_integrity_check(), test_f8_spark_sqlite_wal_persistence(), test_b5_corrupt_sqlite_integrity_failure(), test_b5_empty_tables_handled(), test_b5_missing_db_returns_offline_status(), test_b5_readonly_db_access(), test_pairwise_daemon_sqlite_wal_to_backend_status_bridge() (+4 more)

### Community 11 - "ChatLens Full-System Engineering Audit Report"
Cohesion: 0.07
Nodes (27): 1. Executive Summary, 2. System Architecture & Component Inventory, 3. Baseline Verification Results, 4. Failure Inventory (Evidence-Backed Defects), 5. Root-Cause Analysis: Confirmed Causes vs. Hypotheses, 6. Critical User-Journey Verification Matrix, 7.1 Authentication & Authorization Bypass (DEF-04), 7.2 Hardcoded Secrets & PII Scrubbing (+19 more)

### Community 12 - "test_challenger_m2_m3.py"
Cohesion: 0.09
Nodes (14): clean_daemon_environment(), run_ps_script(), test_difflib_similarity_ratios_mathematical_oracle(), test_fuzzy_routing_additional_invalid_commands(), test_fuzzy_routing_rejection_mandate(), test_fuzzy_routing_undo_and_slash_safety(), test_fuzzy_routing_valid_typos_mandate(), test_supervisor_healthcheck_corrupt_db() (+6 more)

### Community 13 - "KLUERPClient"
Cohesion: 0.11
Nodes (5): KLUERPClient, test_empirical_erp_session_expiration_markers(), test_erp_client_is_session_expired(), test_erp_client_marks_cache_offline_fallback(), test_erp_client_status_codes_session_expired()

### Community 14 - "test_backend_api.py"
Cohesion: 0.09
Nodes (22): Message, test_analyzer_ask_fences_untrusted_transcript(), test_api_status_probe_degraded(), test_ask_prompt_fencing(), test_chat_deletion(), test_chat_export_json_and_csv(), test_chats_and_messages_lifecycle(), test_chats_import_endpoint_and_payload_limits() (+14 more)

### Community 15 - "handle_bot_command"
Cohesion: 0.13
Nodes (30): handle_bot_command(), register_handlers(), test_format_day_schedule_missing_timetable(), test_handle_bot_callback_cmd_attendance(), test_handle_bot_callback_cmd_deadlines(), test_handle_bot_callback_cmd_status(), test_handle_bot_callback_cmd_today(), test_handle_bot_callback_unauthorized_ignored() (+22 more)

### Community 16 - "handle_bot_callback"
Cohesion: 0.09
Nodes (18): handle_bot_callback(), 1. Overview & Architecture, RequestRecorder, test_bot_send_custom_buttons_1d(), test_bot_send_custom_buttons_2d(), test_bot_send_default_quick_buttons(), test_bot_send_empty_buttons_suppresses_reply_markup(), test_bot_set_my_commands_exact_registration() (+10 more)

### Community 17 - "celery_worker.py"
Cohesion: 0.07
Nodes (26): DummyCelery, parse_and_save_sync(), parse_file_task(), _flatten_text(), _parse_message(), parse_telegram_export(), _parse_datetime(), parse_whatsapp_export() (+18 more)

### Community 18 - "backend/main.py"
Cohesion: 0.06
Nodes (39): api_analyze(), api_ask(), api_auth_me(), api_chat_insights(), api_deadlines(), api_deadlines_say(), api_global_summarize(), api_monitoring_status() (+31 more)

### Community 19 - "json"
Cohesion: 0.19
Nodes (15): get_connection(), clean_db(), mock_bot(), test_apply_event_writes_audit(), test_confirm_flow_approve(), test_confirm_flow_bot_edit_without_msg_id(), test_confirm_flow_expired(), test_confirm_flow_failed_write() (+7 more)

### Community 21 - "ChatAnalyzer"
Cohesion: 0.13
Nodes (4): ChatAnalyzer, _format_messages(), test_analyzer_forbidden_id_redaction(), test_analyzer_format_messages()

### Community 22 - ".meta_get"
Cohesion: 0.22
Nodes (4): test_r_ban_3_startup_debounce_logic(), isolate_test_environment(), test_debounce_evaluation_scenarios(), test_meta_table_crud_and_concurrency()

### Community 23 - "run_reminders"
Cohesion: 0.10
Nodes (18): AGENTS.md — SPARK PA daemon (`src/`), Commands, Environment variables, Instance-specific academic data, Invariants (target behavior; each task prompt says which parts already exist), SQLite state (`SPARK_DB`, default `spark.db`, WAL mode), Style, What this is (+10 more)

### Community 24 - "scrapers.py"
Cohesion: 0.14
Nodes (13): parse_attendance_records(), parse_cgpa_records(), parse_fee_records(), parse_generic_tables(), parse_marks_records(), parse_timetable_records(), test_parse_attendance_metrics(), test_parse_cgpa() (+5 more)

### Community 25 - "ChatLens & SPARK PA Assistant"
Cohesion: 0.10
Nodes (20): 1. System Architecture, 2. Ingestion & Decision Lifecycle, 3.1 Decision matrix, 3.2 Universal Message Formatting & Design System, 3.3 Telegram Platform Compliance & Anti-Ban Architecture, 3.4 Interactive Bot Interface & Proactive Reminders, 3. SPARK_MODE State Machine, 4. Deployment-Specific Data & Safe Customization (+12 more)

### Community 26 - "harness.py"
Cohesion: 0.10
Nodes (6): test_pairwise_frontend_calls_backend_through_proxy(), test_pairwise_migrations_run_before_backend_accepts_traffic(), test_pairwise_proxy_tls_termination_and_upstream_headers(), test_scenario_2_complete_web_user_journey(), test_scenario_3_chat_upload_and_analysis_lifecycle(), test_scenario_5_reverse_proxy_domain_failover_and_tls_config()

### Community 27 - "e2e/conftest.py"
Cohesion: 0.11
Nodes (9): compose_config(), e2e_client(), in_memory_db(), isolated_spark_db(), nginx_config(), ComposeParser, NginxConfParser, setup_isolated_spark_db() (+1 more)

### Community 28 - "telegram_live.py"
Cohesion: 0.11
Nodes (9): check_status(), _fetch(), fetch_telegram_chats(), _get_client(), send_code(), send_telegram_code_sync(), _sender_name(), verify_code() (+1 more)

### Community 29 - "RegexParser"
Cohesion: 0.14
Nodes (16): extract(), process_message(), handle_incoming_message(), RegexParser, test_empirical_regex_parser_room_variations(), test_periods_dashes(), test_room_direction(), test_task_precision() (+8 more)

### Community 30 - "GovernanceAuditLogger"
Cohesion: 0.14
Nodes (4): GovernanceAuditLogger, PolicyVerdict, test_governance_audit_logger_roundtrip(), test_quarantine_console_commands()

### Community 32 - "test_scheduler.py"
Cohesion: 0.26
Nodes (10): next_run(), run_briefing(), guard(), test_briefing_idempotent(), test_briefing_retry_on_failure(), test_heartbeat_interval(), test_next_run_after_target(), test_next_run_before_target() (+2 more)

### Community 33 - "time"
Cohesion: 0.13
Nodes (11): run_concurrent_sqlite_benchmark(), worker_fn(), run_streaming_ttft_benchmark(), run_timetable_l1_cache_benchmark(), run_today_e2e_benchmark(), run_parser_benchmark(), run_timetable_benchmark(), run_simd_vector_benchmark() (+3 more)

### Community 34 - "verify_deployment.py"
Cohesion: 0.22
Nodes (7): check_compose_file(), check_env_template(), check_live_endpoints(), check_supporting_configs(), log_info(), log_pass(), main()

### Community 35 - "decide"
Cohesion: 0.15
Nodes (12): decide(), Decision, test_empirical_prompt_injection_canaries_suite(), test_decide_invalid(), test_decide_valid(), canary_cases(), test_canary_dry_mode_absolute_lock(), test_canary_regex_parsing_and_decision_policy() (+4 more)

### Community 36 - "test_workspace_and_erp.py"
Cohesion: 0.19
Nodes (7): SheetsLogger, test_empirical_sheets_logger_silent_degradation(), test_sheets_logger_heartbeat_configured_sheet_id(), test_sheets_logger_heartbeat_empty_sheet_id(), test_sheets_logger_heartbeat_whitespace_sheet_id(), test_sheets_logger_init_preserves_empty_string(), test_sheets_logger_unconfigured_guard_and_skips()

### Community 37 - "test_challenger_m2_m3_2.py"
Cohesion: 0.13
Nodes (9): make_clock_mock(), mock_daemon_settings(), test_debounce_bot_transmission_failure_preserves_prior_timestamp(), test_debounce_corrupted_timestamp_recovery(), test_debounce_delta_mathematical_precision_sweep(), test_debounce_first_boot_no_prior_record(), test_debounce_threshold_899_9_seconds_suppressed(), test_debounce_threshold_900_0_exact_boundary_allowed() (+1 more)

### Community 38 - "os"
Cohesion: 0.08
Nodes (13): _authentication_required(), get_current_user(), require_current_user(), DEF-04: Zero Authentication Enforcement on All Backend Endpoints, main(), main(), test_mock_firebase_token_is_rejected_outside_test_environment(), test_chat_statistics_aggregation() (+5 more)

### Community 40 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 42 - "Home"
Cohesion: 0.15
Nodes (15): AskBar(), AskBarProps, EXAM_SCHEDULE, ExamPrepModal(), ExamPrepModalProps, EXPERIMENTS, app, auth (+7 more)

### Community 43 - "AIExtractor"
Cohesion: 0.18
Nodes (11): AIExtractor, clean_db(), test_ai_extractor_budget_exhaustion(), test_ai_extractor_clienterror_not_retried(), test_ai_extractor_day_rollover(), test_ai_extractor_empty_response(), test_ai_extractor_media_gate(), test_ai_extractor_no_sampling_params() (+3 more)

### Community 44 - "datetime"
Cohesion: 0.12
Nodes (22): get_effective_slots(), load(), Meta, parse_periods(), Slot, Timetable, validate(), Verdict (+14 more)

### Community 45 - "InputGuard"
Cohesion: 0.13
Nodes (6): 2.6 Agent Governance & Semantic Vector Memory Layer (Microsoft AGT & Turbovec), InputGuard, test_benign_academic_messages_not_quarantined(), test_prompt_injection_detection(), test_sanitize_and_wrap_quarantines_untrusted_input(), test_unicode_evasion_and_zero_width_injection_detected()

### Community 46 - "env.py"
Cohesion: 0.14
Nodes (7): get_db(), do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), run_sync_migrations(), Base

### Community 47 - "components.test.tsx"
Cohesion: 0.15
Nodes (21): AiCard(), AiCardProps, ChatHeader(), ChatHeaderProps, insightButtons, FormatAi(), renderInline(), ImportModal() (+13 more)

### Community 48 - "test_tier5_adversarial.py"
Cohesion: 0.10
Nodes (11): caddyfile_config(), CaddyfileParser, test_alembic_migration_idempotency_sqlite(), test_alembic_migration_preexisting_table(), test_caddyfile_path_matching_api_exact(), test_compose_custom_database_url_override_ignored(), test_compose_variable_interpolation_special_chars(), test_proxy_route_api_trailing_slash_discrepancy() (+3 more)

### Community 49 - "test_catch_up.py"
Cohesion: 0.30
Nodes (12): catch_up_chats(), clean_db(), mock_client(), test_catch_up_7_day_cutoff(), test_catch_up_first_run(), test_catch_up_inaccessible_chat(), test_catch_up_live_message_advances(), test_catch_up_max_keeping_upsert() (+4 more)

### Community 50 - "pytest"
Cohesion: 0.45
Nodes (6): Settings, test_settings_invalid_chat_ids(), test_settings_invalid_chat_ids_non_integer(), test_settings_invalid_mode(), test_settings_missing_live_confirm(), test_settings_valid()

### Community 51 - "sys"
Cohesion: 0.53
Nodes (3): harvest_debt(), main(), update_debt_file()

### Community 52 - "Dashboard.tsx"
Cohesion: 0.29
Nodes (9): chartOptions(), Dashboard(), DashboardProps, DAY_LABELS, SkeletonCard(), SkeletonChart(), ChatStats, chart.js (+1 more)

### Community 53 - "ChatLens v2.0"
Cohesion: 0.15
Nodes (12): 1. Architecture Overview, 2. Directory Structure, 3. Environment Variables, 4. Setup and Execution, 5. Key REST API Endpoints, Backend (`chatlens-v2/backend/.env`), ChatLens v2.0, Frontend (`chatlens-v2/frontend/.env.local`) (+4 more)

### Community 54 - "🛠️ Local Development Setup"
Cohesion: 0.15
Nodes (12): 📥 1. Fork & Clone, 🔧 2. Configuration, 📦 3. Run External Services, 🐍 4. Backend Setup, ⚛️ 5. Frontend Setup, 🤝 Contributing to ChatLens, ⚛️ Frontend Linting, 🛠️ Local Development Setup (+4 more)

### Community 56 - "test_templates.py"
Cohesion: 0.18
Nodes (10): attribute_course(), calculate_urgency(), group_and_consolidate_notices(), render_deadlines_card(), test_attribute_course_known_and_heuristics(), test_calculate_urgency_relative_dates(), test_group_and_consolidate_fragmented_notices(), test_render_attendance_card() (+2 more)

### Community 57 - "package.json"
Cohesion: 0.07
Nodes (26): eslintConfig, name, overrides, baseline-browser-mapping, browserslist, @grpc/grpc-js, zod, private (+18 more)

### Community 59 - "save_messages"
Cohesion: 0.15
Nodes (7): Positive Consequences, generate_embeddings_batch(), save_messages(), generate_embedding(), generate_embeddings_batch(), api_telegram_sync_live(), _retrieve_relevant_messages()

### Community 60 - "today_ist"
Cohesion: 0.11
Nodes (17): Invariants & Architecture, Python Engineering Rules (ChatLens & SPARK PA), Runtime & Toolchain, Architecture & Conventions, CLAUDE.md — ChatLens Assistant Guide, Essential Commands, Invariants & Architecture, Python Engineering Rules (ChatLens & SPARK PA) (+9 more)

### Community 61 - "ChatLens v2.0 Design System"
Cohesion: 0.18
Nodes (10): 1. Intent, 2. Colors, 3. Typography, 4. Spacing, 5. Motion (motion-anything), 6. Shapes & Borders, 7. Human-Centric Principles, 8. Icons (+2 more)

### Community 62 - "json"
Cohesion: 0.35
Nodes (12): main(), handle_undo_command(), guard(), test_undo_already_undone_ignored(), test_undo_delete_event(), test_undo_delete_task(), test_undo_failure_keeps_undone_0(), test_undo_missing_prior_keys() (+4 more)

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
Cohesion: 0.12
Nodes (7): test_adversarial_injection_quarantined_in_pipeline(), test_dry_mode_rejects_all_external_writes(), test_gemini_derived_events_always_require_hitl(), test_owner_bypasses_injection_quarantine(), test_quarantined_input_blocks_all_actions(), test_room_override_in_live_mode_auto_approved_only_when_regex_and_validated(), test_zero_disclosure_pii_redaction()

### Community 67 - "dependencies"
Cohesion: 0.20
Nodes (10): dependencies, chart.js, clsx, firebase, lucide-react, next, react, react-chartjs-2 (+2 more)

### Community 68 - "manifest.json"
Cohesion: 0.20
Nodes (9): background_color, description, display, icons, name, orientation, short_name, start_url (+1 more)

### Community 69 - "handlers.py"
Cohesion: 0.22
Nodes (6): AcademicCalendar, get_milestone_date(), load_calendar(), apply_event(), ExtractedAcademicEvent, test_apply_event_calendar_conflict()

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
Cohesion: 0.12
Nodes (15): format_day_schedule(), _build_full_day_timetable(), _get_icons_from_output(), test_empirical_adjacent_period_boundary_minute(), test_empirical_after_all_classes_end(), test_empirical_before_classes_start(), test_empirical_inter_period_breaks(), test_empirical_lunch_break_transitions() (+7 more)

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
Cohesion: 0.25
Nodes (4): nextConfig, inter, metadata, next

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
Cohesion: 0.15
Nodes (4): AsyncSessionMock, setup_in_memory_backend_db(), override_async_session_local(), override_get_db()

### Community 90 - "frontend/AGENTS.md"
Cohesion: 0.33
Nodes (4): 📐 Architecture & Principles, 🛠️ Build & Test Commands, 📁 Directory Structure, 🚀 Project Overview

### Community 92 - "test_challenger_empirical.py"
Cohesion: 0.09
Nodes (4): ensure_frontend_out_fixture(), frozen_clock(), isolate_spark_db(), prevent_telegram_network()

### Community 93 - "test_compliance_guardrails.py"
Cohesion: 0.08
Nodes (12): _get_sender_name(), TelegramRateLimiter, TokenBucket, CircuitState, WorkspaceCircuitBreaker, isolate_env(), test_r_ban_1_rate_limiter_routing(), test_r_ban_1_token_bucket_acquire() (+4 more)

### Community 94 - "2. STRIDE Threat Analysis by Component"
Cohesion: 0.17
Nodes (9): 1. System Architecture & Trust Boundaries, 2.1 Ingestion Layer (Telethon Listener), 2.2 Parsing & LLM Layer (Regex & Gemini), 2.3 Workspace Synchronization Layer (Calendar, Tasks, Sheets), 2.4 State & Persistence Layer (SQLite Database), 2.5 Supply Chain & CI/CD Layer, 2. STRIDE Threat Analysis by Component, STRIDE Threat Model: ChatLens & SPARK PA Assistant (+1 more)

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

### Community 113 - "test_empirical_erp_concurrency_lock_serialization"
Cohesion: 0.40
Nodes (4): test_empirical_erp_concurrency_lock_serialization(), mock_solve_captcha(), simulated_login_process(), test_empirical_erp_session_expiry_triggers_ocr_reauth()

### Community 117 - "Toast.tsx"
Cohesion: 0.38
Nodes (6): icons, styles, Toast(), ToastItem(), ToastProps, ToastData

### Community 118 - "test_performance_optimization.py"
Cohesion: 0.14
Nodes (4): ContiguousVectorBuffer, test_bunk_command_fast_path_from_cache(), test_contiguous_vector_buffer_search(), test_deterministic_slash_commands()

### Community 144 - "ADR 0008: Adoption of Microsoft Agent Governance Principles and In-Process Turbovec RAG"
Cohesion: 0.22
Nodes (8): ADR 0008: Adoption of Microsoft Agent Governance Principles and In-Process Turbovec RAG, Considered Options, Context and Problem Statement, Decision Drivers, Decision Outcome, Negative Consequences, Positive Consequences, Rationale & Comparison

### Community 145 - ".get"
Cohesion: 0.13
Nodes (6): CaseInsensitiveHeaderDict, E2EResponse, test_f1_root_request_routes_to_frontend(), test_f6_async_task_status_endpoint(), test_pairwise_celery_task_update_to_api_poll(), test_scenario_1_stack_health_probe_convergence()

### Community 146 - "typing"
Cohesion: 0.08
Nodes (3): redact_pii(), guard(), test_r_ban_4_pii_redaction_patterns()

### Community 148 - "get_standard_navigation_buttons"
Cohesion: 0.17
Nodes (11): 1. The 4-Part Message Anatomy, 2. Core Operational Rules, 3. Template Reference Implementations, ChatLens Universal Message Formatting Rules & Standards, [R-UI-1] No Raw Technical Jargon, [R-UI-2] Semantic Emoji Contract, [R-UI-3] Link Sanitization & Markdown Safety, [R-UI-4] Course Grouping & Semantic Deduplication (+3 more)

### Community 149 - "templates.py"
Cohesion: 0.18
Nodes (7): sanitize_markdown(), render_attendance_card(), render_day_schedule(), render_proactive_reminder(), render_status_card(), test_render_proactive_reminder(), test_sanitize_markdown_balances_tokens()

### Community 151 - "re"
Cohesion: 0.25
Nodes (4): check_adrs(), main(), main(), scan_motion()

### Community 154 - "src/main.py"
Cohesion: 0.18
Nodes (5): create_telegram_client(), _install_signal_handlers(), _listen(), _sleep_or_stop(), supervise()

### Community 155 - "2. Phase-by-Phase Implementation Specifications"
Cohesion: 0.13
Nodes (12): _escape_like(), lifespan(), 1. Prioritization & Sequencing Strategy, 2. Phase-by-Phase Implementation Specifications, 3. End-to-End Verification Matrix, 4. Risks, Dependencies & Rollback Strategy, ChatLens Remediation Plan: Implementation Roadmap, Phase 1: Security Hardening & Authentication Enforcement (P0) (+4 more)

### Community 156 - "ActionTier"
Cohesion: 0.22
Nodes (4): ActionTier, test_action_tier_classification(), test_high_impact_holiday_and_cancellation_always_mandates_hitl(), test_tier_0_read_allowed_in_all_modes()

### Community 159 - "no-mistakes"
Cohesion: 0.18
Nodes (10): Active validation-step boundary, Before you start, Escalate `ask-user` findings, Inspecting state, Intent is required, no-mistakes, Reading the output, Test-quality rule (+2 more)

### Community 164 - "devDependencies"
Cohesion: 0.20
Nodes (10): devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/node, @types/react, @types/react-dom (+2 more)

### Community 165 - "Test Infrastructure Specification: ChatLens PA Daemon Remediation"
Cohesion: 0.22
Nodes (8): 2. Directory Layout & Artifact Index, 3. Tier Coverage Matrix (`tests/test_e2e_remediation.py`), 4. Execution & Verification Commands, 5. Invariant Gates & Quality Enforcements, Running Specific Tiers, Running the Remediation Acceptance Suite, Static Analysis & Linter Verification, Test Infrastructure Specification: ChatLens PA Daemon Remediation

## Knowledge Gaps
- **8 isolated node(s):** `tailwind-merge`, `@tailwindcss/postcss`, `@types/node`, `@types/react`, `@types/react-dom` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1158 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **55 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `2. Phase-by-Phase Implementation Specifications` connect `2. Phase-by-Phase Implementation Specifications` to `types.ts`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `handle_bot_command()` (e.g. with `Code Layout` and `PolicyVerdict`) actually correct?**
  _`handle_bot_command()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `tailwind-merge`, `@tailwindcss/postcss`, `@types/node` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `types.ts` be split into smaller, more focused modules?**
  _Cohesion score 0.12688172043010754 - nodes in this community are weakly interconnected._
- **Why does `Phase 2: Frontend Restoration & Static Export Configuration (P1)` connect `types.ts` to `2. Phase-by-Phase Implementation Specifications`, `Dashboard.tsx`?**
  _High betweenness centrality (0.105) - this node is a cross-community bridge._
- **Are the 39 inferred relationships involving `E2EClient` (e.g. with `e2e_client()` and `test_f1_api_chats_endpoint_routed()`) actually correct?**
  _`E2EClient` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Should `E2EClient` be split into smaller, more focused modules?**
  _Cohesion score 0.0596078431372549 - nodes in this community are weakly interconnected._