"""Markdown safety utilities and URL sanitization for Telegram formatting."""

import re
from urllib.parse import urlparse

URL_REGEX = re.compile(
    r"(?:\[)?(https?://[^\s)\]]+)(?:\]\()?|(?:\bhttps?://[^\s)\]]+)", re.IGNORECASE
)


def extract_and_clean_urls(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Extract raw or malformed URLs from text and return cleaned prose and named links."""
    links: list[tuple[str, str]] = []

    def _replace(match: re.Match) -> str:
        url = match.group(1) or match.group(0)
        url = url.rstrip(")].,;\"'")
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()

        if "drive.google.com" in netloc:
            label = "Google Drive Folder"
        elif "forms.gle" in netloc or ("docs.google.com" in netloc and "forms" in parsed.path):
            label = "Google Form"
        elif "codetantra" in netloc:
            label = "CodeTantra Portal"
        elif "github.com" in netloc:
            label = "GitHub Repository"
        else:
            label = "Submission Link"

        links.append((label, url))
        return f"🔗 [{label}]({url})"

    cleaned_text = URL_REGEX.sub(_replace, text)

    # Clean up broken brackets or trailing syntax debris
    cleaned_text = re.sub(r"\[\s*🔗", "🔗", cleaned_text)
    cleaned_text = re.sub(r"\(\s*🔗", "🔗", cleaned_text)
    cleaned_text = re.sub(r"\s{2,}", " ", cleaned_text).strip()

    return cleaned_text, links


def sanitize_markdown(text: str) -> str:
    """Balance asterisks, backticks, and fix malformed markdown syntax to prevent Telegram 400."""
    if not text:
        return ""

    # Fix unclosed markdown links: e.g. "[https://... (" -> clean url
    text = re.sub(r"\[(https?://[^\s\]]+)\]\(?", r"\1", text)

    # Fix unbalanced single backticks
    backtick_count = text.count("`")
    if backtick_count % 2 != 0:
        text += "`"

    # Fix unbalanced asterisks (double or single)
    # Check bold asterisks first
    bold_tokens = text.count("**")
    if bold_tokens % 2 != 0:
        text += "**"

    return text
