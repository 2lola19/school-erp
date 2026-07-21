# School ERP frontend

The Next.js application consumes the FastAPI service as an external zero-trust
HTTP API. Authorization remains in the backend and PostgreSQL; hiding a frontend
module is never treated as permission enforcement.

Access tokens are held only in memory. A rotating refresh token is provided by
the API as an HTTP-only, SameSite cookie. Role workspace switching changes the
visible navigation and scope summary without changing effective permissions.

Run `npm ci`, `npm run lint`, and `npm run build` before publishing changes.
