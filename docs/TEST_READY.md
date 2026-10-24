# TEST_READY — E2E Test Suite Publication

**Project**: Void Hunter (VH) Vacation & Hotel Reservation System Admin Console  
**Date**: 2026-10-24  
**Author**: E2E Test Suite Architect (`test_writer_e2e_1`)  
**Status**: **PUBLISHED & READY FOR MILESTONE VALIDATION**

---

## 1. Test Suite Declaration

The comprehensive, opaque-box E2E test suite covering **Requirements R1 through R6** (`ORIGINAL_REQUEST.md`) and all 27 core capabilities in `PROJECT.md § Feature Inventory` has been authored, verified, and published to:

- `smart_room_system/reservations/tests/test_admin_console_e2e.py`
- `smart_room_system/reservations/tests/test_baseline.py`
- `smart_room_system/reservations/tests/__init__.py`
- `TEST_INFRA.md` (Test Infrastructure Guide at project root)

---

## 2. Methodology & Scope Inventory

The test suite contains **73 total tests** (7 baseline system tests + 66 new comprehensive E2E tests) structured across 4 distinct tiers:

### Tier 1 — Feature Coverage (35 Tests)
- **R1: Coupon Management** (`Tier1CouponManagementTests`, 6 tests):
  - Listing with real-time claims and status badges (`GET /api/admin/coupons/`)
  - Full creation configuring all DB fields (`POST /api/admin/coupons/`)
  - Partial editing / patching (`PATCH /api/admin/coupons/<id>/`)
  - Instant active toggle (`POST /api/admin/coupons/<id>/toggle/`)
  - Claims inspection modal records (`GET /api/admin/coupons/<id>/claims/`)
  - Deletion lifecycle (`DELETE /api/admin/coupons/<id>/`)
- **R2: Campaign Banner Manager** (`Tier1BannerManagementTests`, 6 tests):
  - Grouped listing for wide (`main_wide`) and compact (`side_compact`) banners (`GET /api/admin/banners/`)
  - Creation with multipart image upload (`POST /api/admin/banners/`)
  - Primary and secondary voucher linking
  - Display reordering (`POST /api/admin/banners/reorder/`)
  - Active toggle endpoint (`POST /api/admin/banners/<id>/toggle/`)
  - Shopee-style live preview modal context structure (`campaigns_json`)
- **R3: Venues & Rooms Management** (`Tier1VenueRoomManagementTests`, 6 tests):
  - Venue creation with equipment and category tags (`POST /api/rooms/`)
  - Dual pricing configuration (`price_unit` 'hour' vs 'day')
  - Venue status toggle (Available vs Maintenance/Closed)
  - Multi-photo panorama gallery upload (`POST /api/admin/rooms/<id>/gallery/`)
  - Gallery photo deletion (`DELETE /api/admin/rooms/gallery/<image_id>/`)
  - Category tag list and CSS class derivation
- **R4: Complete Bookings Lifecycle & PIN Controls** (`Tier1BookingLifecycleTests`, 6 tests):
  - Approval with automatic 6-digit access PIN issuance (`POST /api/bookings/<id>/approve/`)
  - Audit rejection with mandatory reason note (`POST /api/bookings/<id>/reject/`)
  - Manual access PIN override and one-click regeneration (`POST /api/admin/bookings/<id>/pin/`)
  - Schedule conflict timeline detection (`GET /api/admin/bookings/conflicts/`)
  - Full price breakdown calculation with coupon discount
  - Reservation records CSV export (`GET /api/admin/bookings/export/`)
- **R5: User Accounts & RBAC** (`Tier1UserRBACManagementTests`, 5 tests):
  - User directory search and filtering (`GET /api/users/?q=...`)
  - Role adjustment (`user`, `staff`, `admin`) with automatic `is_staff` synchronization
  - Account active (`is_active`) and verified (`is_verified`) status toggles
  - Claimed coupon wallet and reservation history inspection (`GET /api/admin/users/<id>/history/`)
  - Administrative password reset without requiring old password (`POST /api/admin/users/<id>/reset-password/`)
- **R6: Live Analytics & UI Polish** (`Tier1AnalyticsDashboardTests`, 6 tests):
  - Live KPI metrics for rooms (total, available, maintenance) (`GET /api/admin/analytics/`)
  - Booking metrics (total, approved, pending backlog)
  - User base metrics
  - Coupon claim and redemption rates
  - Revenue aggregation from paid bookings
  - Admin portal web UI access control and stats context rendering (`GET /admin-panel/`)

### Tier 2 — Boundary & Corner Cases (21 Tests)
- **Coupon Boundaries** (`Tier2CouponBoundariesTests`, 6 tests):
  - Exact `min_spend` threshold boundary (eligible at exact amount, ineligible at 1 cent below)
  - Max discount cap strictly enforced vs uncapped when `max_discount_amount` is null
  - Expiration boundary (past rejected, future accepted)
  - 0% and 100% discount calculations
  - Inactive coupon rejection
- **Category Matching Boundaries** (`Tier2CategoryMatchingBoundariesTests`, 5 tests):
  - Single category matching
  - Multi-category comma matching (`applicable_category='room,villa,event'`)
  - Category mismatch rejection
  - Universal match (`applicable_category='all'`)
  - Room tag limit boundary (<= 3 allowed, > 3 raises `ValidationError`)
- **Stay Duration, Capacity & Conflict Boundaries** (`Tier2BookingStayCapacityConflictBoundariesTests`, 5 tests):
  - Day-use stay (1 day, 0 nights) charged at 0.5 daily units
  - 1-day overnight (0 or 1 night valid, 2 nights rejected)
  - Multi-day stays (D days allows D-1 or D nights; fewer rejected)
  - Room capacity exact limit vs overflow (+1 rejected)
  - Abutting schedule boundary (starts exactly at previous end is valid; 1 minute overlap rejected)
- **Security & PIN Boundaries** (`Tier2SecurityPINRBACBoundariesTests`, 5 tests):
  - Access PIN strictly 6 numeric digits (rejects 5, 7, or non-numeric)
  - Unauthorized regular user blocked from admin APIs (403) and admin portal (302)
  - Staff user permitted on operational endpoints
  - Admin user full authorization
  - Unauthenticated anonymous requests rejected (401 on APIs, 302 on UI)

### Tier 3 — Cross-Feature Combinations (5 Tests)
- `test_tier3_01_coupon_applied_to_daily_stay_vs_hourly_booking`: Coupon min spend satisfied on multi-day stay but not short hourly booking.
- `test_tier3_02_banner_linking_active_vs_inactive_coupon`: Deactivating coupon prevents claiming through linked promo banner.
- `test_tier3_03_role_elevation_dynamically_enables_admin_portal_access`: Elevating user role to staff instantly opens admin portal access without raw DB changes.
- `test_tier3_04_booking_rejection_and_cancellation_releases_coupon_lock`: Clean audit state maintained when booking with coupon is rejected.
- `test_tier3_05_room_maintenance_status_prevents_new_reservations`: Inactive room state blocks new booking creation.

### Tier 4 — Real-World Application Scenarios (5 Tests)
- `test_tier4_01_complete_campaign_launch_to_booking_redemption_workflow`: Full campaign launch -> banner creation -> voucher claim -> booking -> approval with PIN.
- `test_tier4_02_venue_setup_with_dual_pricing_model_and_gallery_showcase`: Venue setup -> dual pricing -> panorama gallery upload -> client booking -> photo deletion.
- `test_tier4_03_admin_audit_and_approval_pipeline_with_conflict_resolution_and_pin_distribution`: Conflicting requests -> inspection -> approval of Request A -> rejection of B with note -> PIN override -> CSV export.
- `test_tier4_04_user_rbac_lifecycle_and_account_security_management`: User registration -> OTP verification -> admin search -> history inspection -> password reset -> role elevation.
- `test_tier4_05_system_analytics_and_live_kpi_reporting_under_system_load`: Full multi-entity system load -> live KPI aggregation validation.

---

## 3. How to Run

```bash
c:\Users\nutbo\Documents\Django\ITDS_Site\venv\Scripts\python.exe smart_room_system/manage.py test reservations
```

---

## 4. TDD Progressive Milestone Roadmap

| Milestone | Scope | Target Tests | Current Status | Expected M6 Status |
| :--- | :--- | :---: | :---: | :---: |
| **M1** | Coupons & Campaign Banners Console (R1, R2) | R1 & R2 Feature Tests, Tier 2 Coupon/Category Boundaries | Red (404 on unrouted admin endpoints) | **100% Pass** |
| **M2** | Venues & Rooms Management & Gallery (R3) | R3 Feature Tests, Pricing & Gallery Tests | Red on Gallery endpoints | **100% Pass** |
| **M3** | Bookings Lifecycle, Conflict & PINs (R4) | R4 Feature Tests, PIN Override, CSV Export | Partially Green / Red on Admin Endpoints | **100% Pass** |
| **M4** | User Accounts & RBAC (R5) | R5 Feature Tests, History Inspector, Password Reset | Partially Green / Red on Admin Endpoints | **100% Pass** |
| **M5** | Real-Time Analytics & UI Polish (R6) | R6 Feature Tests, Analytics KPI Endpoint | Red on `/api/admin/analytics/` | **100% Pass** |
| **M6** | Final Gate & Adversarial Hardening | All 73 Tests Across All Tiers | **Current: 38 Passing / 35 TDD Red Baseline** | **Target: 100% Pass (73/73)** |

---

## 5. Escalated Implementation Defects (To Milestone Workers)

### Defect ESC-01: NameError on Ineligible Coupon Booking
- **Location**: `smart_room_system/reservations/views.py:455`
- **Error**: `NameError: name 'serializers' is not defined`
- **Cause**: Line 455 executes `raise serializers.ValidationError(...)`, but `serializers` is not imported from `rest_framework` in `views.py`.
- **Fix**: In `smart_room_system/reservations/views.py`, add `from rest_framework import serializers` or `from rest_framework.exceptions import ValidationError`.
