# Staging deployment

This stack creates an isolated PostgreSQL database, Redis instance, API, and web
application. Services bind only to localhost by default.

1. Copy `.env.example` to `.env` and replace every secret.
2. From the repository root, start the stack:

   ```sh
   docker compose --env-file deploy/staging/.env -f deploy/staging/docker-compose.yml up -d --build
   ```

3. Bootstrap the staging platform administrator:

   ```sh
   docker compose --env-file deploy/staging/.env -f deploy/staging/docker-compose.yml exec backend python -m scripts.seed
   ```

4. Export the same administrator email and password, then run:

   ```sh
   cd backend
   python -m scripts.staging_smoke
   ```

The default endpoints are `http://localhost:13001` and
`http://localhost:18000`. This local staging environment is disposable and is
not a substitute for an externally hosted pre-production environment with TLS.
The database and Redis ports bind to localhost only so the same UAT can also be
run with host application processes when a container registry is unavailable.
