# Security

## API keys

HandDraft does not persist the API key entered in the experimental AI panel.
The key stays in request memory, is redacted from logs, and is cleared from the
browser field after the request. Do not commit real keys to the repository or
place them in frontend source files.

## Public deployment

Set `HANDDRAFT_DEMO_MODE=1` for a public demonstration. Demo mode applies a
per-IP render rate limit, caps page and upload sizes, disables API-key input,
and deletes expired jobs. Uploaded documents and generated files are stored
under `data/jobs` until the configured retention window expires. These controls
reduce casual abuse but are not a replacement for authentication on a
permanent or high-traffic deployment.

Report security issues through GitHub private vulnerability reporting when it
is enabled. Do not include secrets or private documents in a public issue.
