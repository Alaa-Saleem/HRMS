# HRMS API deployment notes

## Secrets and configuration

- Never commit `.env` or real credentials. Use platform environment variables or a secret manager (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault, etc.) and inject `DATABASE_URL`, `JWT_SECRET`, and other settings at runtime.
- For local development, copy `.env.example` to `.env` and edit values there.

## JWT and tokens

- **`JWT_SECRET`**: long random string (e.g. `openssl rand -base64 48`). Rotate only with a coordinated logout of all users.
- **`JWT_ACCESS_EXPIRE_MINUTES`**: short-lived access JWT (default **30**). Legacy `.env` keys **`JWT_EXPIRE_MINUTES`** still map to this setting for compatibility.
- **`JWT_REFRESH_EXPIRE_DAYS`**: refresh token lifetime (default **14**); refresh tokens are stored hashed in Postgres and rotated on each `/auth/refresh` call.

## CORS

- Set **`CORS_ORIGINS`** to a comma-separated list of **exact** browser origins that serve the static UI (scheme + host + port), for example:  
  `https://app.example.com,https://www.example.com`
- Do not use `*` when the browser sends credentials or `Authorization` headers with cross-origin requests.

## HTTPS

- Terminate TLS at your reverse proxy or load balancer (nginx, Caddy, Traefik, cloud LB). Enable **HSTS** for browser clients.
- The FastAPI process typically listens on HTTP behind the proxy; configure **`X-Forwarded-Proto`** / **`Forwarded`** only when you trust the proxy path.

## Rate limiting

- **`LOGIN_RATE_PER_MINUTE`** caps failed/successful login attempts per client IP per rolling minute in **process memory** (default **10**). Multi-worker deployments should use a reverse-proxy rate limit or shared store (Redis) for consistent enforcement. Behind a trusted reverse proxy, ensure the app sees the real client IP if you configure forwarded headers.

## Database

- Run migrations on deploy: `alembic upgrade head`.
- Back up Postgres on a schedule appropriate to your compliance needs.

## Production hardening (optional)

- Set **`ENVIRONMENT=production`** if you add middleware that enforces extra checks (document any such behavior in code comments).
- Monitor `/healthz` for database connectivity.

## API surface

- **Versioned routes**: The same routers are mounted at the root and under **`/v1`** (for example `/employees` and `/v1/employees`). Prefer **`/v1`** for new integrations; unversioned paths remain for backward compatibility.
- **Prometheus metrics**: When `prometheus-fastapi-instrumentator` is installed, **`GET /metrics`** exposes process metrics. If the dependency is missing or initialization fails, `/metrics` may not be registered.
- **Request IDs**: Responses include **`X-Request-ID`** for correlating logs.

## Notifications (leave workflow)

- **`SLACK_WEBHOOK_URL`**: optional Slack incoming webhook for leave request / decision notifications.
- **`SMTP_HOST`**, **`SMTP_PORT`**, **`SMTP_USER`**, **`SMTP_PASSWORD`**, **`SMTP_FROM`**: optional SMTP for outbound mail (leave alerts, **password reset / invite** links). Leave empty to skip SMTP — **`POST /auth/forgot-password`** returns HTTP **503** until SMTP is configured.

## Password reset / invites

- **`PUBLIC_UI_BASE_URL`**: optional base URL for links in reset and invite emails (no trailing slash). If unset, the first entry in **`CORS_ORIGINS`** is used (fallback **`http://127.0.0.1:8787`**).
- **`PASSWORD_RESET_EXPIRE_HOURS`**: lifetime of reset tokens (default **24**).
- **`PASSWORD_MIN_LENGTH`**: enforced on **`POST /auth/reset-password`** (default **8**).

## File uploads

- **`UPLOAD_DIR`**: directory for employee document uploads (default `./uploads`). Ensure the process can write here and exclude this path from backups if inappropriate.
- **`MAX_UPLOAD_BYTES`**: maximum upload size in bytes (default 5 MB).
- **`DOCUMENT_RETENTION_YEARS`**: retention horizon stored on each upload metadata row (default **7**).
- **Expiry purge**: run periodically from `backend/`: `PYTHONPATH=. python scripts/purge_expired_documents.py` to delete expired rows and their files from **`UPLOAD_DIR`**.
