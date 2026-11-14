"""Celery worker entry point for ChatLens v2 workers package."""

try:
    from celery_worker import (
        backfill_embeddings_sync,
        backfill_embeddings_task,
        celery_app,
        generate_embeddings_batch,
        parse_and_save_sync,
        parse_file_task,
        run_backfill_embeddings_sync,
        run_system_diagnostics_sync,
        run_system_diagnostics_task,
        save_messages,
    )
except ImportError:
    from ..celery_worker import (  # type: ignore
        backfill_embeddings_sync,
        backfill_embeddings_task,
        celery_app,
        generate_embeddings_batch,
        parse_and_save_sync,
        parse_file_task,
        run_backfill_embeddings_sync,
        run_system_diagnostics_sync,
        run_system_diagnostics_task,
        save_messages,
    )

__all__ = [
    "celery_app",
    "generate_embeddings_batch",
    "save_messages",
    "parse_and_save_sync",
    "parse_file_task",
    "run_system_diagnostics_sync",
    "run_system_diagnostics_task",
    "backfill_embeddings_sync",
    "run_backfill_embeddings_sync",
    "backfill_embeddings_task",
]
