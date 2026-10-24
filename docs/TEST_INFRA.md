# Test Infrastructure & Specification Guide
**Void Hunter (VH) Vacation & Hotel Reservation System - Admin Console**

## 1. Overview & Architecture

The Void Hunter Admin Console E2E test suite provides rigorous, opaque-box, contract-driven test coverage for all features across requirements **R1 through R6** defined in `ORIGINAL_REQUEST.md` and `PROJECT.md § Feature Inventory`.

The test infrastructure is designed following the **4-Tier Test Design Methodology**:
- **Tier 1 — Feature Coverage**: Comprehensive CRUD, listing, inspection, and lifecycle operations (>= 5 test cases per feature for R1 through R6).
- **Tier 2 — Boundary & Corner Cases**: Strict mathematical boundaries, caps, expiry limits, category tags, stay duration, room capacity, abutting booking intervals, and RBAC security gates (>= 5 test cases per boundary domain).
- **Tier 3 — Cross-Feature Combinations**: Pairwise interactions between coupons, daily/hourly stays, banner linking states, role elevation, and maintenance mode gating.
- **Tier 4 — Real-World Application Scenarios**: Multi-step application workflows simulating real user and administrator operations (>= 5 realistic scenarios).

---

## 2. Test Environment & Execution

### Runtime Environment
- **Python Runtime**: `c:\Users\nutbo\Documents\Django\ITDS_Site\venv\Scripts\python.exe`
- **Django Version**: 6.0.7
- **Test Framework**: `django.test.TestCase`, `rest_framework.test.APIClient`
- **Database**: SQLite in-memory / temporary test database created dynamically per test run
- **Media Isolation**: Temporary directory created per test run using `tempfile.mkdtemp()` and cleaned up in `tearDownClass()` via `shutil.rmtree()`

### Test Execution Commands

#### Run Entire Suite (Baseline + Admin Console E2E):
```bash
c:\Users\nutbo\Documents\Django\ITDS_Site\venv\Scripts\python.exe smart_room_system/manage.py test reservations
```

#### Run Only Admin Console E2E Suite:
```bash
c:\Users\nutbo\Documents\Django\ITDS_Site\venv\Scripts\python.exe smart_room_system/manage.py test reservations.tests.test_admin_console_e2e
```

#### Run Specific Test Tier:
```bash
# Tier 1 - Coupon Management
c:\Users\nutbo\Documents\Django\ITDS_Site\venv\Scripts\python.exe smart_room_system/manage.py test reservations.tests.test_admin_console_e2e.Tier1CouponManagementTests

# Tier 2 - Boundary Cases
c:\Users\nutbo\Documents\Django\ITDS_Site\venv\Scripts\python.exe smart_room_system/manage.py test reservations.tests.test_admin_console_e2e.Tier2CouponBoundariesTests

# Tier 4 - Real-World Scenarios
c:\Users\nutbo\Documents\Django\ITDS_Site\venv\Scripts\python.exe smart_room_system/manage.py test reservations.tests.test_admin_console_e2e.Tier4RealWorldScenarioTests
```

---

## 3. Test Layout & Organization

```
smart_room_system/reservations/tests/
├── __init__.py                               # Test package initializer
├── test_baseline.py                          # Existing baseline system tests (auth, rooms, bookings, OTP)
└── test_admin_console_e2e.py                 # Comprehensive 4-Tier Admin Console E2E test suite
```

---

## 4. Test Matrix & Requirement Mapping

| Tier | Test Class | Req | Feature / Boundary Covered |
| :--- | :--- | :---: | :--- |
| **Tier 1** | `Tier1CouponManagementTests` | R1 | Listing with claim stats, Full CRUD, Active Toggle, Claims Inspection, Deletion |
| **Tier 1** | `Tier1BannerManagementTests` | R2 | Grouped Wide/Compact View, Multipart Image Creation, Dual Voucher Linking, Reordering, Active Toggle, Shopee Modal Preview |
| **Tier 1** | `Tier1VenueRoomManagementTests` | R3 | Venue Creation with Amenities, Dual Pricing (Hourly vs Daily), Maintenance Status Toggle, Panorama Gallery Upload & Deletion, Tag Mapping |
| **Tier 1** | `Tier1BookingLifecycleTests` | R4 | Pending Approvals & PIN Issuance, Audit Rejection with Reason, PIN Override & Regeneration, Conflict Detection API, Price Breakdown, CSV Export |
| **Tier 1** | `Tier1UserRBACManagementTests` | R5 | User Directory Search, Role Switching with `is_staff` Sync, Active/Verified Toggles, Wallet & History Inspection, Admin Password Reset |
| **Tier 1** | `Tier1AnalyticsDashboardTests` | R6 | Live KPI Metrics (Rooms, Bookings, Backlog, Users, Claim/Redemption Rates, Revenue), Admin Portal Auth Gating |
| **Tier 2** | `Tier2CouponBoundariesTests` | R1 | Exact min spend threshold, Max discount cap vs uncapped, Expiration boundaries, 0% vs 100% discount, Inactive coupon rejection |
| **Tier 2** | `Tier2CategoryMatchingBoundariesTests` | R1, R3 | Single category match, Multi-category comma matching, Mismatch rejection, 'all' universal match, <= 3 tags limit validation |
| **Tier 2** | `Tier2BookingStayCapacityConflictBoundariesTests` | R3, R4 | Day-use (0 nights) pricing (0.5 units), 1-day overnight vs multi-night validation, Multi-day rules, Room capacity limit, Abutting time slots |
| **Tier 2** | `Tier2SecurityPINRBACBoundariesTests` | R4, R5 | Strictly 6-digit access PIN validation, Unauthorized regular user 403 / redirect, Staff operational permission, Admin full access, Anonymous 401 |
| **Tier 3** | `Tier3CrossFeatureCombinationTests` | R1-R5 | Coupon on daily stay vs hourly booking, Banner linking active vs inactive coupon, Role elevation dynamically unlocking console, Booking rejection releasing coupon lock, Maintenance mode blocking new bookings |
| **Tier 4** | `Tier4RealWorldScenarioTests` | R1-R6 | Scenario 1: Campaign Launch to Booking Redemption Workflow<br>Scenario 2: Venue Setup with Dual Pricing & Gallery Showcase<br>Scenario 3: Administrative Audit & Approval Pipeline with Conflict Resolution & PIN Distribution<br>Scenario 4: User RBAC Lifecycle & Account Security Management<br>Scenario 5: Live KPI Reporting under Full System Load |

---

## 5. Test Fixtures & Media Isolation

- **In-Memory Dummy Images**: `get_dummy_gif()` creates valid 1x1 GIF byte payloads for file upload tests (`SimpleUploadedFile`), avoiding disk dependency.
- **Media Root Isolation**: Decorator `@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)` redirects image file uploads to a dedicated temporary folder which is recursively cleaned up after test execution.
- **Transactional State**: All tests inherit from `django.test.TestCase` ensuring automatic rollback of database changes between test cases.
