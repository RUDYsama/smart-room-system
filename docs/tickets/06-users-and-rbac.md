# 06: User Accounts, Department RBAC & Security Audit Console

**What to build:**
User administration module allowing searching users, modifying RBAC roles, toggling active/verified flags, resetting passwords, and inspecting individual user coupon wallets and bookings.

**Blocked by:** 01-core-navigation-and-layout.md

**Status:** ready-for-agent

- [ ] Provide backend REST APIs: `/users/`, `/users/<id>/role/`, `/users/<id>/toggle-status/`, and `/users/<id>/reset-password/`.
- [ ] Admin can view user directory, filter by role (user, staff, admin), and adjust user permissions.
- [ ] Admin can view any user's claimed coupon wallet and reservation history.
