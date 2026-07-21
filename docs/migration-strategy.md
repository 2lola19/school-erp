# Database migration strategy

## Decision

The discarded repository migration chain was a prototype: it created academic
tables out of dependency order and was never a safe production history. The
approved strategy is therefore:

- recreate local, test, demo, and staging databases from the
  `0001_initial_schema` baseline;
- never automatically drop or rewrite a database containing prototype tables;
- require a separately reviewed, data-preserving migration for any database
  containing real records.

The application startup now runs `scripts.migration_preflight` before Alembic.
It permits an empty database or the current baseline and refuses unknown or
prototype schemas.

## Prototype environment procedure

1. Export any fixtures that still have value.
2. Stop the application.
3. Recreate the non-production database or its disposable volume.
4. Run `alembic upgrade head`.
5. Bootstrap the platform administrator.
6. Run the authorization E2E suite and staging smoke test.

## Production-data procedure

Do not use the prototype reset procedure. First capture a verified backup and
inventory table counts, constraints, tenant ownership, and orphaned references.
Build a forward-only migration that maps legacy identities, academic records,
and audit data into the baseline schema. Rehearse it against a restored copy,
compare row counts and checksums, validate RLS for every tenant, and obtain
explicit approval before scheduling a production cutover.

No production database was supplied or modified during this work.
