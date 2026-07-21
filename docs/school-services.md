# School services

The school-services release adds finance, health, counselling, library,
transport, hostel, and extracurricular operations without widening the access
of academic or technical staff.

## Security boundaries

- Finance uses fixed-precision amounts. Payments and refunds remain pending
  until a different user approves them. The built-in Bursar and Payment
  Approver roles conflict and cannot be assigned together.
- Health records and encounter notes live in dedicated tenant-isolated tables.
  General administrators do not receive `health.records.read` by default.
- Emergency health flags are a limited safety projection and never include the
  underlying conditions, medication history, or clinical encounter notes.
- Break-glass grants are student-specific, last no more than eight hours, and
  every protected read is recorded distinctly in the append-only audit log.
- Counselling cases are returned only to their assigned counsellor. Encounter
  notes remain separate from attendance and discipline records.
- Activity patrons operate through an `activity_id` scope. Achievements require
  independent verification before they become official.

## Operational controls

- Library issue and return operations lock inventory before changing available
  copies.
- Transport assignments enforce route capacity and configured pickup points.
- Hostel assignments enforce room capacity and one current placement per
  student.
- Every service write is tenant-scoped and audited. PostgreSQL row-level
  security is enabled and forced on all 22 service tables.

The permission-aware UI is available at `/school/services`. The API remains the
authoritative enforcement layer when users switch workspaces.
