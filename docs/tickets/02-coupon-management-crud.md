# 02: Full Coupon Management Console & REST APIs

**What to build:**
Complete administrative CRUD console and REST API for promotional discount coupons, including code generation, percentage discount, min spend, max discount caps, category targeting, expiration scheduling, and claimed user wallet inspection.

**Blocked by:** 01-core-navigation-and-layout.md

**Status:** ready-for-agent

- [ ] Provide backend REST APIs: `GET/POST /api/admin/coupons/`, `PUT/DELETE /api/admin/coupons/<id>/`, and `GET /api/admin/coupons/<id>/claims/`.
- [ ] Admin can view a searchable, filterable table of coupons with active status toggle switch.
- [ ] Admin can add or edit coupons with full parameter validation (code, title, icon, discount %, min spend, max discount, applicable categories, expiration date, terms).
- [ ] Admin can inspect which users claimed each coupon and whether it was redeemed.
