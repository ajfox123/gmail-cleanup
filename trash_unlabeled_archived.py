#!/usr/bin/env python3
import argparse
import time
from typing import List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

DEFAULT_QUERY = "-in:inbox has:nouserlabels -in:trash -in:spam"

def get_gmail_service(credentials_path: str, token_path: str):
    creds: Optional[Credentials] = None
    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    except Exception:
        creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def list_message_ids(service, user_id: str, query: str, max_messages: Optional[int] = None) -> List[str]:
    ids: List[str] = []
    page_token = None

    while True:
        res = service.users().messages().list(
            userId=user_id,
            q=query,
            pageToken=page_token,
            maxResults=500
        ).execute()

        msgs = res.get("messages", [])
        ids.extend([m["id"] for m in msgs])

        if max_messages is not None and len(ids) >= max_messages:
            return ids[:max_messages]

        page_token = res.get("nextPageToken")
        if not page_token:
            break

    return ids

def batch_trash(service, user_id: str, message_ids: List[str], dry_run: bool, batch_size: int = 100, sleep_s: float = 0.2):
    """
    Gmail API has users.messages.trash for a single message.
    We'll call it in chunks with light throttling + basic retry.
    """
    trashed = 0

    for i in range(0, len(message_ids), batch_size):
        chunk = message_ids[i:i+batch_size]
        for mid in chunk:
            if dry_run:
                trashed += 1
                continue

            # Basic retry for rate limits / transient errors
            for attempt in range(5):
                try:
                    service.users().messages().trash(userId=user_id, id=mid).execute()
                    trashed += 1
                    break
                except HttpError as e:
                    status = getattr(e.resp, "status", None)
                    if status in (429, 500, 503):
                        backoff = (2 ** attempt) * 0.5
                        time.sleep(backoff)
                        continue
                    raise

            time.sleep(sleep_s)

        print(f"Processed {min(i+batch_size, len(message_ids))}/{len(message_ids)}")

    return trashed

def main():
    parser = argparse.ArgumentParser(description="Move archived + unlabeled Gmail messages to Trash (not permanent delete).")
    parser.add_argument("--credentials", default="credentials.json", help="Path to OAuth client credentials JSON.")
    parser.add_argument("--token", default="token.json", help="Path to saved OAuth token JSON.")
    parser.add_argument("--user", default="me", help="Gmail userId (default: me).")
    parser.add_argument("--query", default=DEFAULT_QUERY, help=f'Gmail search query (default: "{DEFAULT_QUERY}")')
    parser.add_argument("--max", type=int, default=None, help="Max messages to process (for testing).")
    parser.add_argument("--dry-run", action="store_true", help="Only count what would be trashed; do not change anything.")
    parser.add_argument("--batch-size", type=int, default=100, help="How many message IDs to process per progress chunk.")
    args = parser.parse_args()

    service = get_gmail_service(args.credentials, args.token)

    print(f"Searching with query:\n  {args.query}")
    ids = list_message_ids(service, args.user, args.query, args.max)
    print(f"Matched messages: {len(ids)}")

    if len(ids) == 0:
        return

    if args.dry_run:
        print("Dry run enabled — no messages will be changed.")
    else:
        print("Trashing messages... (reversible until Trash is emptied / auto-deletes after ~30 days)")

    trashed = batch_trash(service, args.user, ids, dry_run=args.dry_run, batch_size=args.batch_size)
    print(f"Done. {'Would trash' if args.dry_run else 'Trashed'}: {trashed}")

if __name__ == "__main__":
    main()
