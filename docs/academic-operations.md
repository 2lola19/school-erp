# Academic operations

The academic administration module builds on the tenant-aware staff role and
permission foundation. It adds official workflows for:

- academic sessions and terms;
- applicants, guardians, admission decisions, and class placement;
- scoped daily attendance with submission and independent approval;
- teacher and classroom timetable conflict prevention;
- examination cycles and weighted assessment components;
- report-card generation from approved grades, independent approval, and
  controlled publication.

Every write uses the current tenant RLS context and creates an audit record.
Attendance corrections return a record to draft state. Applicant decisions,
attendance approval, grade approval, and report-card approval use row locks and
explicit workflow states.

The school dashboard exposes `/school/academic` only when the signed-in user has
an academic administration permission. The API remains authoritative even when
the user changes workspaces.
