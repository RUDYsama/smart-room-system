# Original User Request

## 2026-10-24T14:47:32Z

Build a comprehensive, enterprise-grade Admin Console for the Void Hunter (VH) Vacation & Hotel Reservation System, enabling full control over Coupons, Promotional Campaign Banners, Venues/Rooms, Bookings, User Accounts, and Live System Analytics directly through the web interface without requiring raw database access.

Working directory: c:/Users/nutbo/Documents/Django

## Requirements

### R1. Comprehensive Coupon Management (Full CRUD, Targeting & Expiration)
Provide an end-to-end coupon management module in the Admin Console. Administrators must be able to list, search, filter, create, edit, deactivate, and delete coupons. Every parameter supported by the database model must be configurable: coupon code, discount title, subtitle, tooltip, icon type, discount percent, minimum spend, maximum discount cap, applicable categories (multi-select: all, room, villa, event, theater, work), expiration date/time (`expires_at`), display order, active status, and terms & conditions. The console must also display real-time claim analytics showing which users have claimed each coupon and whether it has been redeemed.

### R2. Promotional Campaign Banners Console (Full CRUD & Voucher Linking)
Provide a visual campaign banner manager supporting both wide landscape banners (`main_wide`) and compact side promo cards (`side_compact`). Administrators must be able to upload banner images, set titles, badge texts, link primary and secondary coupons from the coupon database, configure campaign descriptions and terms, reorder banners, and preview the live Shopee-style coupon details modal directly within the console before publishing.

### R3. Advanced Venues & Rooms Management Console
Provide an interactive venue management module allowing administrators to create, update, and manage all venues and rooms. Configurable properties include room number, name, category classification tags, capacity, pricing models (hourly rate vs. daily stay rate), active/maintenance status, cover image, multi-photo panorama gallery (`RoomImage`), and equipment/amenity specifications.

### R4. Complete Bookings Lifecycle, Conflict Detection & Digital PIN Controls
Provide a full-featured reservation management system with dedicated Pending Approvals and Historical Bookings tables. Administrators must be able to approve or reject requests with audit reasons, view applied coupon codes and discount calculations, inspect schedule conflicts on a timeline, override or regenerate 6-digit digital door access PINs, and export reservation records.

### R5. User Accounts & Role-Based Access Control (RBAC)
Provide user management features allowing administrators to search users, inspect booking histories and claimed coupon wallets, adjust roles (`user`, `staff`, `admin`), toggle account active/verified status, update department and contact info, and execute administrative password resets.

### R6. Real-Time Analytics & UI Polish
Provide a live KPI dashboard tracking total rooms, active bookings, approval backlogs, user count, coupon claim rates, and revenue. The UI must strictly follow the modern rounded travel-portal design system, replace any remaining legacy emojis with clean SVG icons, and integrate with the smooth loading screen.

## Acceptance Criteria

### Coupon Management
- [ ] Admin can view a paginated, searchable table of all coupons with status badges and claim statistics.
- [ ] Admin can create a new coupon with code, discount %, min spend, max discount cap, category multi-select, expiration date, and terms.
- [ ] Admin can toggle active status with instant feedback and edit or delete existing coupons.
- [ ] Claimed coupon details for each coupon show the list of users who claimed it, claim timestamp, and whether it was used.

### Campaign Banner Management
- [ ] Admin can view existing banners grouped by type (Wide vs. Compact) with live cover thumbnails.
- [ ] Admin can create, edit, reorder, and delete banners with image upload.
- [ ] Admin can link primary and secondary coupons via dropdown selectors populated from active database coupons.
- [ ] Admin can preview the Shopee-style campaign details pop-up modal directly from the admin console.

### Venues & Rooms Management
- [ ] Admin can create, edit, and toggle status (Available, Maintenance, Closed) for any room or venue.
- [ ] Admin can configure daily stay vs. hourly pricing rates and upload gallery images.

### Bookings & Approvals Management
- [ ] Admin can approve or reject pending bookings with reason notes.
- [ ] On approval, a 6-digit access PIN is verified/generated.
- [ ] Admin can view applied coupons and total price breakdowns for every booking.

### User Management
- [ ] Admin can view all registered users and adjust roles between user, staff, and admin.
- [ ] Admin can view an individual user's claimed coupon wallet and reservation history.
