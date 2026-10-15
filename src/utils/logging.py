"""Structured JSON logging configuration and Sentry initialization."""

import logging
import re
import sys
from typing import Any

import sentry_sdk
import structlog
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.types import Event, Hint
from structlog.types import EventDict, WrappedLogger

from src.config import settings

_SECRET_PATTERNS = [
    re.compile(r"bot\d+:[\w-]+"),
    re.compile(r"[AF]Iza[\w-]{35}|FxxxFAKE[\w-]{31}"),
    re.compile(r"ghp_[\w]+"),
    re.compile(r"github_pat_[\w]+"),
    re.compile(r"sk-[\w-]+"),
]


def _redact_str(val: str) -> str:
    res = val
    for pattern in _SECRET_PATTERNS:
        res = pattern.sub("***", res)
    return res


def _scrub_value(val: Any) -> Any:
    if isinstance(val, str):
        return _redact_str(val)
    if isinstance(val, dict):
        return {k: _scrub_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_scrub_value(item) for item in val]
    return val


def _scrub_secrets(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    for k, v in list(event_dict.items()):
        event_dict[k] = _scrub_value(v)
    return event_dict


def _sentry_before_send(event: Event, hint: Hint) -> Event | None:
    if "logentry" in event and event["logentry"]:
        logentry = dict(event["logentry"])
        if "message" in logentry:
            logentry["message"] = _redact_str(str(logentry["message"]))
        event["logentry"] = logentry  # type: ignore[typeddict-item]

    if "exception" in event and "values" in event["exception"] and event["exception"]["values"]:
        for exc in event["exception"]["values"]:
            if "value" in exc:
                exc["value"] = _redact_str(str(exc["value"]))

    if "extra" in event and isinstance(event["extra"], dict):
        event["extra"].pop("msg_text", None)
        event["extra"].pop("message_text", None)
        event["extra"].pop("sender_name", None)
        event["extra"].pop("chat_title", None)

    return event


def configure_logging() -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            _scrub_secrets,
            structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)],
            traces_sample_rate=0.1,
            include_local_variables=False,
            send_default_pii=False,
            before_send=_sentry_before_send,
        )


get_logger = structlog.get_logger
