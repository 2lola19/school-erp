# Production data readiness

Do not create invented personal student, guardian, staff, medical, or financial
records in production. The production subscription catalog is safe to seed and
contains no personal data. Real school data must come from an approved source,
with ownership, consent, retention, and migration reconciliation documented.

Before production import:

1. Restore a recent source backup into an isolated rehearsal environment.
2. Inventory tenants, row counts, identifiers, duplicates, orphaned references,
   date formats, currencies, and sensitive health/finance columns.
3. Map every source record to a validated tenant and stable external identifier.
4. Transform and validate in staging; never repair source records silently.
5. Compare pre/post row counts and financial totals, then sample records with
   school representatives.
6. Test forced RLS using a non-superuser application role for every tenant table.
7. Assign each tenant a reviewed plan, effective dates, and negotiated overrides.
8. Back up production, run migration preflight, apply migrations, seed catalogs,
   import in a controlled window, and retain a tested rollback plan.

Synthetic acceptance data may be used in staging, clearly labelled and kept
separate from production. Provider secrets, real payment references, and live
webhook URLs must be supplied through the deployment secret store, never source
control or frontend environment variables.
