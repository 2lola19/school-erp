# School ERP

A multi-tenant school management foundation built with FastAPI, PostgreSQL,
Redis, and Next.js. The current release combines secure identity, academic
operations, school services, and auditable multi-role staff authorization.

## Security model

- One active primary role and up to four active secondary roles per staff member.
- Time-bound, scope-bound role assignments with approval and revocation history.
- PostgreSQL row-level security on every tenant-owned table.
- Permission-versioned sessions and Redis caching for immediate revocation.
- Explicit denials override role and direct permission grants.
- Reusable permission bundles can be attached to roles without duplicating grants.
- Role conflicts, category limits, delegation rules, and dual-control approval.
- Append-only audit records for role and protected academic changes.
- Short-lived access tokens in memory and rotating refresh tokens in HTTP-only cookies.
- Admissions, attendance, timetables, examinations, and published report-card workflows.
- Dual-controlled finance, isolated health and counselling records, and audited break-glass access.
- Library, transport, hostel, and extracurricular workflows with capacity and approval controls.

See [docs/authorization-architecture.md](docs/authorization-architecture.md) for
the detailed model and endpoint map.
See [docs/academic-operations.md](docs/academic-operations.md) for the academic
administration workflows.
See [docs/school-services.md](docs/school-services.md) for finance, welfare, and
student-life service boundaries.

## Local setup

1. Copy `.env.example` to `.env` and replace both placeholder secrets.
2. Start the stack:

   ```sh
   docker compose up --build
   ```

3. Bootstrap the first platform administrator from inside the backend container:

   ```sh
   docker compose exec \
     -e BOOTSTRAP_ADMIN_EMAIL=admin@example.com \
     -e BOOTSTRAP_ADMIN_PASSWORD='use-a-long-unique-password' \
     backend python -m scripts.seed
   ```

4. Sign in at `http://localhost:3001/login` using domain `platform.local`.

The API is available at `http://localhost:8000`, with health status at `/healthz`.

## Development checks

Backend:

```sh
python -m pip install -r backend/requirements-dev.txt
cd backend
pytest
ruff check app tests scripts
```

Frontend:

```sh
cd frontend
npm ci
npm run lint
npm run build
```

## Migration note

The earlier repository contained an unreleased migration chain that referenced
students and classrooms before creating them. It has been replaced by a coherent
`0001_initial_schema` baseline. Existing prototype databases should be recreated
before applying this baseline; do not point it at production data without a
bespoke data migration.

The automated migration preflight refuses legacy managed tables instead of
dropping them. See [docs/migration-strategy.md](docs/migration-strategy.md) for
the approved prototype-reset and production-data procedures.
