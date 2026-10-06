"""Structured JSON logging configuration and Sentry initialization."""

import logging
import sys

import sentry_sdk
import structlog
from sentry_sdk.integrations.logging import LoggingIntegration

from src.config import settings


def _scrub_secrets(logger, method_name, event_dict):
    import re

    if "error" in event_dict:
        msg = str(event_dict["error"])
        msg = re.sub(r"bot\d+:[\w-]+", "***", msg)
        msg = re.sub(r"AIza[\w-]{35}|FxxxFAKE[\w-]{31}", "***", msg)
        event_dict["error"] = msg
    msg = str(event_dict.get("event", ""))
    msg = re.sub(r"bot\d+:[\w-]+", "***", msg)
    msg = re.sub(r"AIza[\w-]{35}|FxxxFAKE[\w-]{31}", "***", msg)
    event_dict["event"] = msg
    return event_dict


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


def _sentry_before_send(event, hint):
    import re
    # Sentry scrubber for bot\d+:[\w-]+ and AIza[\w-]{35}|FxxxFAKE[\w-]{31}

    if "logentry" in event and "message" in event["logentry"]:
        msg = event["logentry"]["message"]
        msg = re.sub(r"bot\d+:[\w-]+", "***", msg)
        msg = re.sub(r"AIza[\w-]{35}|FxxxFAKE[\w-]{31}", "***", msg)
        event["logentry"]["message"] = msg

    if "exception" in event and "values" in event["exception"]:
        for exc in event["exception"]["values"]:
            if "value" in exc:
                msg = exc["value"]
                msg = re.sub(r"bot\d+:[\w-]+", "***", msg)
                msg = re.sub(r"AIza[\w-]{35}|FxxxFAKE[\w-]{31}", "***", msg)
                exc["value"] = msg

    if "extra" in event:
        event["extra"].pop("msg_text", None)
        event["extra"].pop("message_text", None)

    return event

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
