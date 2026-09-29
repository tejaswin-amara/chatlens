#!/usr/bin/env python3
"""One-time local helper to generate Telethon StringSession for headless deployments."""

import os
import sys

from telethon.sessions import StringSession
from telethon.sync import TelegramClient


def main() -> None:
    print("=== ChatLens Telegram StringSession Generator ===")
    api_id = os.getenv("TELEGRAM_API_ID") or input("Enter TELEGRAM_API_ID: ").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH") or input("Enter TELEGRAM_API_HASH: ").strip()

    if not api_id or not api_hash:
        print("Error: TELEGRAM_API_ID and TELEGRAM_API_HASH are required.")
        sys.exit(1)

    print("\nConnecting to Telegram...")
    client = TelegramClient(StringSession(), int(api_id), api_hash)
    client.start()

    session_string = client.session.save()
    print("\n" + "=" * 60)
    print("SUCCESS! Your TELEGRAM_SESSION_STRING is generated below:")
    print("=" * 60)
    print(session_string)
    print("=" * 60)
    print("\nCopy this string and set it as TELEGRAM_SESSION_STRING in your environment.")
    client.disconnect()


if __name__ == "__main__":
    main()
