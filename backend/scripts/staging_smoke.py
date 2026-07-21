"""Run a small user-acceptance smoke test against a deployed staging stack."""

import os

import httpx


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Set {name} before running staging UAT")
    return value


def main() -> None:
    api_root = os.getenv("STAGING_API_URL", "http://localhost:18000").rstrip("/")
    web_root = os.getenv("STAGING_WEB_URL", "http://localhost:13001").rstrip("/")
    email = required("STAGING_ADMIN_EMAIL")
    password = required("STAGING_ADMIN_PASSWORD")

    with httpx.Client(timeout=20, follow_redirects=True) as client:
        health = client.get(f"{api_root}/healthz")
        health.raise_for_status()
        assert health.json()["status"] == "ok"

        login_page = client.get(f"{web_root}/login")
        login_page.raise_for_status()
        assert "School ERP" in login_page.text

        schema = client.get(f"{api_root}/api/v1/openapi.json")
        schema.raise_for_status()
        paths = schema.json()["paths"]
        for expected in (
            "/api/v1/auth/login",
            "/api/v1/auth/me",
            "/api/v1/staff/{staff_id}/roles/secondary",
            "/api/v1/academic/grades/{grade_id}/approve",
            "/api/v1/academic-admin/sessions",
            "/api/v1/academic-admin/attendance/{attendance_id}/approve",
            "/api/v1/academic-admin/report-cards/{report_card_id}/publish",
            "/api/v1/school-services/finance/payments/{payment_id}/decision",
            "/api/v1/school-services/health/break-glass",
            "/api/v1/school-services/activities/achievements/{achievement_id}/decision",
        ):
            assert expected in paths

        login = client.post(
            f"{api_root}/api/v1/auth/login",
            json={"domain": "platform.local", "email": email, "password": password},
        )
        login.raise_for_status()
        access_token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        context = client.get(f"{api_root}/api/v1/auth/me", headers=headers)
        context.raise_for_status()
        assert context.json()["email"] == email.lower()
        assert context.json()["workspaces"]

        refreshed = client.post(f"{api_root}/api/v1/auth/refresh")
        refreshed.raise_for_status()
        assert refreshed.json()["access_token"] != access_token

    print("Staging UAT passed: web, API, schema, login, workspace, and refresh")


if __name__ == "__main__":
    main()
