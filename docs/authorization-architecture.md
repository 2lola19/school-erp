# Authorization architecture

## Identity hierarchy

`User` represents authentication only. `Staff` represents employment identity.
Operational access comes from historical `StaffRoleAssignment` records, not a
job title or fixed role columns.

Each staff member has one active primary assignment and no more than four active
secondary assignments. The primary role controls the default workspace; a
secondary role adds a switchable workspace. Workspace selection never replaces
API authorization.

## Authorization decision

Every protected request evaluates:

1. Signature, expiry, token type, and session revocation.
2. Tenant and active user status.
3. Permission version against the database.
4. Effective permissions from role grants, permission bundles, active and unexpired assignments, and approved direct grants.
5. Explicit denials.
6. Assignment scope against the requested resource.
7. Separation-of-duty and approval requirements for sensitive transitions.
8. PostgreSQL row-level security as the final tenant boundary.

Access tokens contain only user ID, tenant ID, session ID, permission version,
timestamps, and token type. Permissions are cached under
`permissions:{tenant_id}:{user_id}:{permission_version}` and are recalculated
after any assignment transition.

## Role assignment controls

- Partial unique indexes enforce one active primary assignment and prevent duplicate active/pending roles.
- Row locks serialize concurrent assignments and prevent a fifth secondary role.
- Management, finance, health, and platform secondary roles default to one per category.
- Scoped roles require an explicit operational scope.
- Sensitive roles and `REQUIRE_APPROVAL` conflicts remain pending.
- The assigning user cannot approve the same sensitive assignment.
- Approval rechecks role limits and conflicts while holding the staff assignment lock.
- Active primary roles can only be replaced, never simply removed.
- The expiry worker transitions elapsed roles to `EXPIRED`, invalidates permissions, and audits the event.

## API surface

```text
GET    /api/v1/staff/{staff_id}/roles
POST   /api/v1/staff/{staff_id}/roles/primary
PUT    /api/v1/staff/{staff_id}/roles/primary
POST   /api/v1/staff/{staff_id}/roles/secondary
DELETE /api/v1/staff/{staff_id}/roles/secondary/{assignment_id}
PATCH  /api/v1/staff/{staff_id}/roles/{assignment_id}
POST   /api/v1/staff/{staff_id}/roles/{assignment_id}/approve
POST   /api/v1/staff/{staff_id}/roles/{assignment_id}/suspend
POST   /api/v1/staff/{staff_id}/roles/{assignment_id}/revoke
GET    /api/v1/staff/{staff_id}/permissions
GET    /api/v1/staff/{staff_id}/role-history
GET    /api/v1/staff/{staff_id}/role-conflicts
POST   /api/v1/staff/{staff_id}/permission-preview
```

Permission preview is a POST because scope and effective dates are structured,
sensitive input and should not be placed in a query string.

## Academic phase-one controls

Teacher creation links a user, staff profile, primary role, and teacher record in
one transaction. Grade entry requires `scores.enter` and a matching class/subject
scope. A teacher submits their own draft, while a separate holder of
`scores.approve` approves it. Self-approval is rejected.

Finance, medical, counselling, extracurricular, transport, hostel, and library
entities remain later roadmap modules. Their future permissions and privacy rules
must build on this authorization layer rather than bypassing it.
