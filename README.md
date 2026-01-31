# gmail-cleanup

I ran out of Google space, so I built this to yeet redundant archived emails. It finds Gmail messages that are archived (not in Inbox) and have no user labels, then moves them to Trash. It uses the Gmail API and only moves messages to Trash (not permanent delete), so you can undo if you change your mind.

## What it does
- Searches with a Gmail query (default: `-in:inbox has:nouserlabels -in:trash -in:spam`)
- Lists matching message IDs
- Optionally trashes those messages in batches
- Supports a dry run to preview counts

## Setup
1) Create OAuth client credentials in Google Cloud Console and download `credentials.json`.
2) Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage
Dry run (no changes):

```bash
python trash_unlabeled_archived.py --dry-run
```

Trash matching messages:

```bash
python trash_unlabeled_archived.py
```

Optional flags:
- `--query` to override the Gmail search query
- `--max` to limit how many messages are processed
- `--batch-size` to control progress chunking
- `--credentials` / `--token` to change OAuth file paths

## Getting started (example queries)
Try a dry run first, then narrow or widen the query:

- Archived + unlabeled (default):
```bash
python trash_unlabeled_archived.py --dry-run
```

- Older than 2 years:
```bash
python trash_unlabeled_archived.py --dry-run --query "-in:inbox has:nouserlabels older_than:2y -in:trash -in:spam"
```

- Promotions only:
```bash
python trash_unlabeled_archived.py --dry-run --query "-in:inbox has:nouserlabels category:promotions -in:trash -in:spam"
```

- Big emails (5MB+):
```bash
python trash_unlabeled_archived.py --dry-run --query "-in:inbox has:nouserlabels larger:5M -in:trash -in:spam"
```

## Notes
- First run will open a browser for OAuth; a `token.json` will be written.
- Trashed messages can be restored until Trash is emptied (Gmail auto‑deletes after ~30 days).
