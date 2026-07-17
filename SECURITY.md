# Security

## API keys

HandDraft does not persist the API key entered in the experimental AI panel.
The key stays in request memory, is redacted from logs, and is cleared from the
browser field after the request. Do not commit real keys to the repository or
place them in frontend source files.

## Public deployment

The current version has no user accounts, access control, rate limiting, or
automatic job cleanup. Uploaded documents and generated files are temporarily
stored under `data/jobs` on the machine running the service. Use a trusted
network or add authentication and cleanup before operating a permanent public
instance.

Report security issues through GitHub private vulnerability reporting when it
is enabled. Do not include secrets or private documents in a public issue.
