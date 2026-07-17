import os

dirs = [
    "backend/app/api/v1/endpoints", "backend/app/core", "backend/app/db",
    "backend/app/models", "backend/app/schemas", "backend/app/services",
    "backend/app/utils", "backend/alembic/versions", "backend/scripts",
    "backend/docs", "backend/tests/api/api_v1"
]

files = [
    "backend/app/__init__.py", "backend/app/api/__init__.py", "backend/app/api/v1/__init__.py",
    "backend/app/api/v1/endpoints/__init__.py", "backend/app/core/__init__.py",
    "backend/app/db/__init__.py", "backend/app/models/__init__.py", "backend/app/schemas/__init__.py",
    "backend/app/services/__init__.py", "backend/app/main.py", "backend/app/api/v1/dependencies.py",
    "backend/app/api/v1/endpoints/auth.py", "backend/app/core/config.py", "backend/app/core/security.py",
    "backend/app/db/session.py", "backend/app/db/base_class.py", "backend/app/models/core.py",
    "backend/app/schemas/auth.py", "backend/app/services/auth_service.py", "backend/scripts/seed.py",
    "backend/docs/rls_policies.sql", "backend/tests/api/api_v1/test_auth.py", "backend/alembic.ini",
    "backend/Dockerfile", "backend/docker-compose.yml", "backend/requirements.txt", "backend/.env.example"
]

for d in dirs:
    os.makedirs(d, exist_ok=True)

for f in files:
    with open(f, 'a') as file_obj:
        pass

print("Phase 1 backend directory structure generated successfully.")