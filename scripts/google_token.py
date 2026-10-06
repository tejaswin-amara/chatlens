#!/usr/bin/env python3
import base64
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/spreadsheets",
]


def main():
    secret_file = sys.argv[1] if len(sys.argv) > 1 else "client_secret.json"
    try:
        flow = InstalledAppFlow.from_client_secrets_file(secret_file, SCOPES)
        creds = flow.run_local_server(port=0)

        creds_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }

        json_str = json.dumps(creds_data)
        b64_creds = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")

        print("\n=== GOOGLE_CREDENTIALS_BASE64 ===")
        print(b64_creds)
        print("=================================")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
