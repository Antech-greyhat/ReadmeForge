# Deploying the web app

The web UI is a regular Flask app. `wsgi.py` exposes it as `app` for any WSGI server and
defaults to **public mode**.

## Configuration

All settings are environment variables.

| Variable | Default | Purpose |
| --- | --- | --- |
| `GITHUB_TOKEN` | unset | Server-side token for the GitHub API. Without it the server gets 60 requests per hour, shared by every visitor. A classic token with no scopes is enough. |
| `READMEFORGE_MODE` | `public` via `wsgi.py`, `local` via `readme-forge serve` | `public` applies stricter rate limits and hides local-only UI. |
| `READMEFORGE_TRUSTED_PROXIES` | `0` | Number of reverse proxies in front of the app. Set it to `1` on Render and Vercel so rate limits apply per visitor, not per proxy. Leave it at `0` when nothing sits in front of the app, or clients could spoof their IP. |
| `READMEFORGE_RATELIMIT_STORAGE` | `memory://` | Flask-Limiter storage URI. Use Redis (`redis://...`, and `pip install redis`) when running several workers or instances. |
| `READMEFORGE_CACHE_TTL` | `600` | Seconds to cache GitHub responses in memory. |
| `READMEFORGE_INSTANCE_<NAME>` | public instances | Default widget base URL for `STATS`, `STREAK`, `TROPHY`, `ACTIVITY` or `SUMMARY`. Point these at your own deployments to avoid the shared instances' rate limits. |

Visitors never send a token. The browser only talks to this server, and only the server
talks to GitHub.

### Rate limits

| Mode | `/api/profile` | `/api/generate`, `/api/config/validate` |
| --- | --- | --- |
| `local` | 30/minute | 120/minute |
| `public` | 6/minute, 60/hour | 60/minute, 600/hour |

A profile lookup costs up to 42 GitHub API calls, which is why it is limited hardest.

### Caching

The GitHub response cache and the default rate-limit storage live in process memory.
Each gunicorn worker and each serverless instance has its own copy, so:

- a cold instance refetches profiles a warm one already has;
- per-IP limits are per instance unless `READMEFORGE_RATELIMIT_STORAGE` points at a
  shared store.

That is acceptable for a small deployment. Add Redis for the rate limits once traffic
spreads across instances.

## Render

1. Create a **Web Service** from the repository.
2. Runtime: Python 3. Build command:

   ```bash
   pip install ".[deploy]"
   ```

3. Start command:

   ```bash
   gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60
   ```

4. Environment: set `GITHUB_TOKEN`, `READMEFORGE_TRUSTED_PROXIES=1` and, if you want
   it, `PYTHON_VERSION=3.12.7`.

With more than one worker, either accept per-worker limits or set
`READMEFORGE_RATELIMIT_STORAGE` to a Render Key Value (Redis) URL.

## Vercel

The repository includes `vercel.json`, which builds `wsgi.py` with the Python runtime
and routes every path to it. Dependencies come from `requirements.txt`.

1. Import the repository in Vercel. No framework preset or build command is needed.
2. Add the environment variables `GITHUB_TOKEN` and `READMEFORGE_TRUSTED_PROXIES=1`.
3. Deploy.

Serverless instances are short-lived, so the in-memory cache and rate limits reset
often and are not shared between instances. For a public deployment with real traffic,
set `READMEFORGE_RATELIMIT_STORAGE` to a hosted Redis such as Upstash.

## Any other host

```bash
pip install ".[deploy]"
GITHUB_TOKEN=... READMEFORGE_TRUSTED_PROXIES=1 gunicorn wsgi:app --bind 0.0.0.0:8000
```

gunicorn does not run on Windows. Use `readme-forge serve` locally there, or run the
app in WSL or a container.
