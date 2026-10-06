from datetime import UTC, date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), "IST")


def now_ist() -> datetime:
    return datetime.now(IST)


def today_ist() -> date:
    return now_ist().date()


def to_ist(dt: datetime) -> datetime:
    """Aware datetimes are converted; naive ones are treated as UTC (Telethon dates are UTC)."""
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).astimezone(IST)
