# Project: Void Hunter (VH) Vacation & Hotel Reservation System Admin Console

## Architecture
- **Environment**: Django 6.0.7 with Django REST Framework (DRF), SimpleJWT, and SQLite backend.
- **Python Runtime**: `c:\Users\nutbo\Documents\Django\ITDS_Site\venv\Scripts\python.exe`
- **Application Path**: `smart_room_system/reservations/`
- **Template Workspace**: `smart_room_system/templates/admin_portal.html`
- **Authentication**: Dual mechanism (7-day Django Sessions + SimpleJWT Bearer tokens).
- **Access Control**: Role-based access control with `CustomUser.role` in `['admin', 'staff', 'user']`, gated via `IsAdminRole` and `IsStaffOrAdminRole`.
- **UI Architecture**: Tailwind CSS CDN, Google Fonts `Prompt` (primary) + `JetBrains Mono` (code/PINs), modern rounded travel-portal design system (`rounded-2xl`, `rounded-3xl`), inline Heroicon SVGs, hardware-accelerated smooth loading overlay.

## Code Layout
- `smart_room_system/reservations/models.py`: Data models (`Coupon`, `UserCoupon`, `PromotionBanner`, `Room`, `RoomImage`, `Booking`, `CustomUser`, `PaymentCard`).
- `smart_room_system/reservations/serializers.py`: DRF serializers for API endpoints.
- `smart_room_system/reservations/views.py`: Admin API controllers, FBVs, and `admin_portal_view` context provider.
- `smart_room_system/reservations/urls.py`: URL route definitions for admin endpoints and portal.
- `smart_room_system/templates/admin_portal.html`: Enterprise Admin Console UI template and frontend controllers.
- `smart_room_system/reservations/tests/`: E2E, integration, and unit tests.

## Feature Inventory
Every feature from the Survey phase appears here with its assigned milestone:
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Coupon List, Search & Filter | Paginated and searchable table with status badges and claim counts | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Coupon Full CRUD | Create, edit, and delete coupons with all parameters | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Coupon Instant Active Toggle | Quick toggle endpoint and UI button for coupon active status | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Coupon Targeting & Expiration | Min spend, max discount cap, category multi-select, and expiration date/time | M1 | ORIGINAL_REQUEST §R1 |
| 5 | Coupon Claim Analytics | Inspection modal displaying users who claimed each coupon and redemption status | M1 | ORIGINAL_REQUEST §R1 |
| 6 | Campaign Banner Grouped View | Grouped display of Wide (`main_wide`) and Compact (`side_compact`) banners with thumbnails | M1 | ORIGINAL_REQUEST §R2 |
| 7 | Campaign Banner Full CRUD | Create, edit, reorder, and delete banners with image upload | M1 | ORIGINAL_REQUEST §R2 |
| 8 | Banner Voucher Linking | Dropdown selectors to link primary and secondary coupons from active database | M1 | ORIGINAL_REQUEST §R2 |
| 9 | Shopee-Style Live Preview Modal | In-console preview modal rendering the live Shopee coupon card experience | M1 | ORIGINAL_REQUEST §R2 |
| 10 | Room / Venue Edit & Management | Update venue details, capacity, tags, building, and amenities | M2 | ORIGINAL_REQUEST §R3 |
| 11 | Dual Pricing Model Configuration | Toggle and configure hourly rate vs daily stay rate (`price_unit`) | M2 | ORIGINAL_REQUEST §R3 |
| 12 | Room Status Management | Toggle Available, Maintenance, and Closed statuses with visual badges | M2 | ORIGINAL_REQUEST §R3 |
| 13 | Multi-Photo Panorama Gallery | Gallery photo manager (`RoomImage`) to upload, view, caption, and delete photos | M2 | ORIGINAL_REQUEST §R3 |
| 14 | Dedicated Bookings Tables | Separate Pending Approvals and Historical Reservations with search and filters | M3 | ORIGINAL_REQUEST §R4 |
| 15 | Booking Approval & Rejection Modal | Approve or reject requests with mandatory audit reason notes | M3 | ORIGINAL_REQUEST §R4 |
| 16 | Coupon & Discount Breakdown | Display applied coupon codes, original subtotal, discount, and net total | M3 | ORIGINAL_REQUEST §R4 |
| 17 | Schedule Conflict Detection | Detect overlapping bookings on the same venue with timeline warning alerts | M3 | ORIGINAL_REQUEST §R4 |
| 18 | Digital Access PIN Controls | Verify 6-digit access PIN, one-click PIN regeneration, and manual PIN override | M3 | ORIGINAL_REQUEST §R4 |
| 19 | Reservation Records Export | Export booking records to CSV format directly from the console | M3 | ORIGINAL_REQUEST §R4 |
| 20 | User Search & Directory | Searchable user directory with role filtering (Admin, Staff, User) | M4 | ORIGINAL_REQUEST §R5 |
| 21 | RBAC Role Adjustment | Interactive role selector (`admin`, `staff`, `user`) with automatic `is_staff` sync | M4 | ORIGINAL_REQUEST §R5 |
| 22 | User Status Toggles | Instant toggle for account active (`is_active`) and verified (`is_verified`) status | M4 | ORIGINAL_REQUEST §R5 |
| 23 | User Wallet & History Inspector | Modal to inspect an individual user's claimed coupon wallet and reservation history | M4 | ORIGINAL_REQUEST §R5 |
| 24 | Administrative Password Reset | Dedicated admin action to reset passwords for users without old password | M4 | ORIGINAL_REQUEST §R5 |
| 25 | Live KPI Dashboard | Metrics for total rooms, active bookings, backlog, users, claim rate, revenue | M5 | ORIGINAL_REQUEST §R6 |
| 26 | SVG Iconography Standardization | Complete replacement of all legacy emojis with clean Heroicon SVGs | M5 | ORIGINAL_REQUEST §R6 |
| 27 | Smooth Loading Screen Integration | Hardware-accelerated spinner (`#globalLoadingScreen`, `vhLoading`) on load & async operations | M5 | ORIGINAL_REQUEST §R6 |
| 28 | Comprehensive E2E Test Suite | 4-tier requirement-driven opaque-box test suite verifying all console capabilities | E2E Track | ORIGINAL_REQUEST Acceptance Criteria |
| 29 | Adversarial Coverage Hardening | White-box stress testing and gap remediation (Tier 5) | Final Milestone | Project Pattern Phase 2 |

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Coupons & Promotional Banners Console | Features #1-9: Serializers, CRUD endpoints, claim analytics, voucher linking, and Shopee preview modal in Admin Console | none | IN_PROGRESS (Worker: 679fa701-0861-4f2b-8048-eddff937502b) |
| M2 | Venues, Rooms & Panorama Gallery Console | Features #10-13: Pricing model configuration, status management, room editing, and RoomImage gallery upload/delete APIs & UI | none | PLANNED |
| M3 | Bookings Lifecycle, Conflict Detection & PINs | Features #14-19: Dedicated tables, audit reason rejection modal, PIN override/regen, conflict detection, price breakdown, CSV export | M1, M2 | PLANNED |
| M4 | User Accounts, RBAC & Wallet Inspector | Features #20-24: User search, role switcher, active/verified toggles, wallet/history inspector modal, admin password reset | M1, M3 | PLANNED |
| M5 | Real-Time Analytics & UI Polish | Features #25-27: Live KPI metrics computation, zero emoji replacement with SVGs, smooth loading screen integration | M1-M4 | PLANNED |
| M6 | Final Milestone: 100% E2E Pass & Adversarial Hardening | Features #28-29: Verification of full E2E test suite (Tiers 1-4) and Tier 5 adversarial stress testing | M1-M5, E2E Track | PLANNED |

## Interface Contracts

### Coupon Admin API (`/api/admin/coupons/`)
- `GET /api/admin/coupons/` -> List of coupons with `claims_count`, `used_count`, `is_active`.
- `POST /api/admin/coupons/` -> Create coupon (validates `code`, `discount_percent`, `min_spend`, `applicable_category`, `expires_at`, `terms`).
- `GET/PUT/PATCH/DELETE /api/admin/coupons/<id>/` -> CRUD operations on coupon.
- `POST /api/admin/coupons/<id>/toggle/` -> Toggles `is_active`, returns `{id, is_active, status: "success"}`.
- `GET /api/admin/coupons/<id>/claims/` -> Returns `{coupon_id, coupon_code, claims: [{user_id, username, email, claimed_at, is_used, used_at}]}`.

### Banner Admin API (`/api/admin/banners/`)
- `GET /api/admin/banners/` -> List of banners with linked coupon details.
- `POST /api/admin/banners/` -> Create banner (supports multipart image, `title`, `badge_text`, `banner_type`, `coupon_id`, `secondary_coupon_id`, `description`, `terms`, `order`, `is_active`).
- `GET/PUT/PATCH/DELETE /api/admin/banners/<id>/` -> CRUD operations on banner.
- `POST /api/admin/banners/<id>/toggle/` -> Toggles `is_active`.

### Room Gallery & Status API (`/api/admin/rooms/`)
- `POST /api/admin/rooms/<room_id>/gallery/` -> Upload gallery image (`RoomImage`), returns `{image_id, room_id, url, caption, order}`.
- `DELETE /api/admin/rooms/gallery/<image_id>/` -> Delete gallery image.
- `PATCH /api/rooms/<id>/` -> Extended to support `price_unit` ('hour', 'day'), `tags`, and status toggle.

### Booking Access PIN, Conflict & Export API (`/api/admin/bookings/`)
- `POST /api/admin/bookings/<id>/pin/` -> Body: `{pin?: "6-digits", regenerate?: boolean}`. Returns `{booking_id, access_pin}`.
- `GET /api/admin/bookings/conflicts/` -> Query params: `?room_id=X&start=ISO&end=ISO`. Returns `{has_conflict: boolean, overlapping_bookings: [...]}`.
- `GET /api/admin/bookings/export/` -> Returns `Content-Type: text/csv` with all booking records.

### User RBAC, Wallet & Password Reset API (`/api/admin/users/`)
- `GET /api/admin/users/<id>/history/` -> Returns `{user_id, username, claimed_coupons: [...], bookings: [...]}`.
- `POST /api/admin/users/<id>/reset-password/` -> Body: `{new_password: "..."}`. Returns `{status: "success", message: "Password updated"}`.
- `PATCH /api/users/<id>/` -> Updates role ('admin', 'staff', 'user'), automatically synchronizing `is_staff` when role is admin or staff.

### Analytics KPI API (`/api/admin/analytics/` or `/api/dashboard/stats/`)
- `GET /api/admin/analytics/` -> Returns `{total_rooms, available_rooms, maintenance_rooms, active_bookings, pending_backlog, total_users, total_coupons, total_claims, redemption_rate, total_revenue}`.
