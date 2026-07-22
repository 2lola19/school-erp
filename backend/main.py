"""Vercel service entrypoint for the School ERP API."""

import os

# The Vercel service is mounted below /backend. Cookie paths are browser-facing,
# so they must include that external prefix even though FastAPI does not see it.
os.environ.setdefault("REFRESH_COOKIE_PATH", "/backend/api/v1/auth")
os.environ.setdefault("SECURE_COOKIES", "true")

from app.main import app  # noqa: E402, F401
