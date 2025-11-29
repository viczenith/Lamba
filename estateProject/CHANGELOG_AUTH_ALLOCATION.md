2025-11-28 - Multi-tenant auth & allocation fixes

- Pass tenant `company` context from `CustomAuthenticationForm` into `authenticate()`
  so auth backends can disambiguate users with the same email across companies.

- Hardened several allocation-related views to scope queries by
  `request.user.company_profile` to avoid cross-tenant data leakage.

- Added targeted unit tests:
  - `tests/test_auth_form_backend_unit.py` (mocks ORM to validate auth flow)
  - `tests/test_allocation_isolation.py` (integration-style; requires DB migrations)

- Notes: Running the full `manage.py test` triggers migrations; in this workspace
  some existing migration files expect different DB states and may fail when
  running against a fresh test database. I made a couple migration files
  (`0071`, `0072`) more idempotent to help test runs, but further migration
  reconciliation may be required in CI or a developer environment.
