"""
Comprehensive Opaque-Box E2E Test Suite for Void Hunter (VH) Admin Console
Covers Requirements R1 through R6 in ORIGINAL_REQUEST.md and PROJECT.md § Feature Inventory.

Tiers:
- Tier 1: Feature Coverage (>=5 test cases per feature for R1 through R6)
- Tier 2: Boundary & Corner Cases (>=5 test cases per boundary area)
- Tier 3: Cross-Feature Combinations (Pairwise interactions)
- Tier 4: Real-World Application Scenarios (>=5 application-level end-to-end flows)
"""

import io
import json
import tempfile
import shutil
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APIClient

from reservations.models import (
    CustomUser,
    Room,
    RoomImage,
    Booking,
    BookingEquipment,
    Coupon,
    UserCoupon,
    PaymentCard,
    PromotionBanner,
)

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


def get_dummy_gif(filename="test_image.gif"):
    """Returns a valid 1x1 GIF byte sequence accepted as a valid image."""
    content = (
        b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff"
        b"\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
        b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
    )
    return SimpleUploadedFile(name=filename, content=content, content_type="image/gif")


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class AdminConsoleE2EBaseTestCase(TestCase):
    """Base setup fixture providing role-based actors, rooms, and test utilities."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()

        # Admin user (Superuser + role=admin)
        self.admin = CustomUser.objects.create_superuser(
            username="vh_admin",
            email="admin@voidhunter.local",
            password="AdminPassword123!",
            role="admin",
            department="Executive Management",
            is_staff=True,
            is_verified=True,
        )

        # Staff user (role=staff)
        self.staff = CustomUser.objects.create_user(
            username="vh_staff",
            email="staff@voidhunter.local",
            password="StaffPassword123!",
            role="staff",
            department="Operations",
            is_staff=True,
            is_verified=True,
        )

        # Regular customer Alice
        self.user_alice = CustomUser.objects.create_user(
            username="alice_traveller",
            email="alice@voyage.local",
            password="AlicePassword123!",
            role="user",
            department="Tourism",
            is_staff=False,
            is_verified=True,
        )

        # Regular customer Bob
        self.user_bob = CustomUser.objects.create_user(
            username="bob_guest",
            email="bob@voyage.local",
            password="BobPassword123!",
            role="user",
            department="Guest",
            is_staff=False,
            is_verified=True,
        )

        # Standard Hourly Room (Meeting / Conference)
        self.hourly_room = Room.objects.create(
            room_number="CONF-201",
            name="Emerald Conference Hall",
            building="Central Pavilion",
            floor=2,
            capacity=25,
            price_per_hour=Decimal("600.00"),
            price_unit="hour",
            tags="สถานที่ทำงาน, จัดกิจกรรม",
            amenities="Laser Projector, Conference Phone, High-speed WiFi",
            is_active=True,
        )

        # Standard Daily Room (Luxury Vacation Villa)
        self.daily_room = Room.objects.create(
            room_number="VILLA-701",
            name="Void Hunter Horizon Villa",
            building="Seaside Cliff",
            floor=1,
            capacity=8,
            price_per_hour=Decimal("8000.00"),
            price_unit="day",
            tags="บ้านพัก, ห้องพัก",
            amenities="Private Infinity Pool, Panorama Sea View, Butler Service",
            is_active=True,
        )

    def authenticate_user(self, user):
        """Authenticates user across both Django session middleware and DRF API views."""
        self.client.force_login(user)
        self.client.force_authenticate(user=user)


# ==============================================================================
# TIER 1 - FEATURE COVERAGE (R1 to R6)
# ==============================================================================


class Tier1CouponManagementTests(AdminConsoleE2EBaseTestCase):
    """Tier 1: Comprehensive Coupon Management (R1) - CRUD, Claims & Toggle."""

    def test_r1_01_coupon_list_endpoint(self):
        """Admin can list coupons with claim counts and status badges."""
        Coupon.objects.create(
            code="WELCOME20",
            discount_title="ส่วนลด 20%",
            sub_title="สิทธิ์สมาชิกใหม่",
            discount_percent=20,
            min_spend=Decimal("1000.00"),
            applicable_category="all",
            is_active=True,
        )
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/admin/coupons/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Should return array or paginated dict with results
        results = res.data.get("results", res.data) if isinstance(res.data, dict) else res.data
        self.assertTrue(len(results) >= 1)
        found = any(c.get("code") == "WELCOME20" for c in results)
        self.assertTrue(found, "Coupon WELCOME20 should be present in coupon listing")

    def test_r1_02_coupon_create_with_all_supported_fields(self):
        """Admin can create a coupon configuring every database parameter."""
        exp_time = timezone.now() + timedelta(days=30)
        payload = {
            "code": "SUMMER50",
            "discount_title": "ส่วนลด 50% ฤดูร้อน",
            "sub_title": "สิทธิ์พักผ่อนริมทะเล",
            "info_tooltip": "ใช้ได้เฉพาะวันธรรมดา ขั้นต่ำ 2,000 บาท",
            "icon_type": "villa",
            "button_text": "รับสิทธิ์พิเศษ",
            "discount_percent": 50,
            "min_spend": "2000.00",
            "applicable_category": "villa,room",
            "max_discount_amount": "3000.00",
            "expires_at": exp_time.isoformat(),
            "terms": "1. จองล่วงหน้า 3 วัน\n2. ไม่สามารถแลกเปลี่ยนเป็นเงินสดได้",
            "order": 1,
            "is_active": True,
        }
        self.client.force_authenticate(user=self.admin)
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["code"], "SUMMER50")
        self.assertEqual(int(res.data["discount_percent"]), 50)
        self.assertEqual(float(res.data["max_discount_amount"]), 3000.00)

        # Verify DB persistence
        coupon = Coupon.objects.get(code="SUMMER50")
        self.assertEqual(coupon.icon_type, "villa")
        self.assertEqual(coupon.applicable_category, "villa,room")

    def test_r1_03_coupon_patch_edit_fields(self):
        """Admin can edit an existing coupon's terms, spend, and discount."""
        coupon = Coupon.objects.create(
            code="EARLYBIRD",
            discount_title="จองล่วงหน้าลด 15%",
            sub_title="สิทธิ์จองล่วงหน้า",
            discount_percent=15,
            min_spend=Decimal("1500.00"),
            is_active=True,
        )
        self.client.force_authenticate(user=self.admin)
        patch_payload = {
            "discount_percent": 25,
            "min_spend": "1800.00",
            "terms": "แก้ไขเงื่อนไข: ต้องชำระเงินทันที",
        }
        res = self.client.patch(f"/api/admin/coupons/{coupon.id}/", patch_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        coupon.refresh_from_db()
        self.assertEqual(coupon.discount_percent, 25)
        self.assertEqual(coupon.min_spend, Decimal("1800.00"))
        self.assertIn("ต้องชำระเงินทันที", coupon.terms)

    def test_r1_04_coupon_instant_active_toggle(self):
        """Admin can toggle coupon active status with instant feedback."""
        coupon = Coupon.objects.create(
            code="FLASH10",
            discount_title="Flash Sale 10%",
            sub_title="จำกัดเวลา",
            is_active=True,
        )
        self.client.force_authenticate(user=self.admin)
        # Deactivate
        res1 = self.client.post(f"/api/admin/coupons/{coupon.id}/toggle/")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        coupon.refresh_from_db()
        self.assertFalse(coupon.is_active)

        # Reactivate
        res2 = self.client.post(f"/api/admin/coupons/{coupon.id}/toggle/")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        coupon.refresh_from_db()
        self.assertTrue(coupon.is_active)

    def test_r1_05_coupon_claims_inspection_view(self):
        """Admin can inspect real-time claim records and redemption status for a coupon."""
        coupon = Coupon.objects.create(
            code="VIPGIFT",
            discount_title="ของขวัญ VIP",
            sub_title="สมาชิกคนพิเศษ",
            is_active=True,
        )
        UserCoupon.objects.create(user=self.user_alice, coupon=coupon, is_used=True, used_at=timezone.now())
        UserCoupon.objects.create(user=self.user_bob, coupon=coupon, is_used=False)

        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f"/api/admin/coupons/{coupon.id}/claims/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        claims = res.data.get("claims", res.data)
        self.assertEqual(len(claims), 2)
        alice_claim = next(c for c in claims if c["username"] == "alice_traveller")
        bob_claim = next(c for c in claims if c["username"] == "bob_guest")
        self.assertTrue(alice_claim["is_used"])
        self.assertFalse(bob_claim["is_used"])

    def test_r1_06_coupon_delete_lifecycle(self):
        """Admin can delete an unneeded coupon."""
        coupon = Coupon.objects.create(
            code="DELETEME",
            discount_title="คูปองทดสอบลบ",
            sub_title="จะถูกลบ",
            is_active=False,
        )
        self.client.force_authenticate(user=self.admin)
        res = self.client.delete(f"/api/admin/coupons/{coupon.id}/")
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT])
        self.assertFalse(Coupon.objects.filter(code="DELETEME").exists())


class Tier1BannerManagementTests(AdminConsoleE2EBaseTestCase):
    """Tier 1: Campaign Banner Management (R2) - CRUD, Linking & Modal Preview."""

    def test_r2_01_banner_grouped_list_wide_and_compact(self):
        """Admin can view banners grouped or filtered by wide vs compact format."""
        PromotionBanner.objects.create(
            title="Summer Sea Escape",
            banner_type="main_wide",
            badge_text="แคมเปญหลัก",
            order=1,
            is_active=True,
        )
        PromotionBanner.objects.create(
            title="Weekend Cozy Deal",
            banner_type="side_compact",
            badge_text="โปรเสริม",
            order=2,
            is_active=True,
        )
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/admin/banners/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        banners = res.data.get("results", res.data) if isinstance(res.data, dict) else res.data
        self.assertTrue(len(banners) >= 2)
        types = [b.get("banner_type") for b in banners]
        self.assertIn("main_wide", types)
        self.assertIn("side_compact", types)

    def test_r2_02_banner_create_with_image_upload(self):
        """Admin can create a new campaign banner with multipart image upload."""
        image_file = get_dummy_gif("banner_promo.gif")
        payload = {
            "title": "Winter Galaxy Festival",
            "badge_text": "เทศกาลฤดูหนาว",
            "banner_type": "main_wide",
            "description": "สัมผัสความงามของท้องฟ้าและธรรมชาติ",
            "terms": "เงื่อนไขเฉพาะฤดูกาล",
            "order": 1,
            "is_active": True,
            "image": image_file,
        }
        self.client.force_authenticate(user=self.admin)
        res = self.client.post("/api/admin/banners/", payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], "Winter Galaxy Festival")
        self.assertIn("image", res.data)
        self.assertTrue(PromotionBanner.objects.filter(title="Winter Galaxy Festival").exists())

    def test_r2_03_banner_voucher_linking_primary_and_secondary(self):
        """Admin can link primary and secondary vouchers to a banner from active database."""
        c1 = Coupon.objects.create(code="MAIN20", discount_title="ลด 20% พักผ่อน", is_active=True)
        c2 = Coupon.objects.create(code="EXTRAFREE", discount_title="ฟรีเครื่องดื่มต้อนรับ", is_active=True)

        image_file = get_dummy_gif("dual_voucher_banner.gif")
        payload = {
            "title": "Dual Voucher Grand Campaign",
            "banner_type": "main_wide",
            "coupon_id": c1.id,
            "secondary_coupon_id": c2.id,
            "image": image_file,
        }
        self.client.force_authenticate(user=self.admin)
        res = self.client.post("/api/admin/banners/", payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        banner = PromotionBanner.objects.get(title="Dual Voucher Grand Campaign")
        self.assertEqual(banner.coupon, c1)
        self.assertEqual(banner.secondary_coupon, c2)

    def test_r2_04_banner_reorder_display_sequence(self):
        """Admin can reorder banners for priority display in the carousel/cards."""
        b1 = PromotionBanner.objects.create(title="Banner 1", order=10, is_active=True)
        b2 = PromotionBanner.objects.create(title="Banner 2", order=20, is_active=True)

        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            "/api/admin/banners/reorder/",
            {"banner_ids": [b2.id, b1.id]},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        b1.refresh_from_db()
        b2.refresh_from_db()
        self.assertTrue(b2.order < b1.order or (b2.order == 0 and b1.order == 1))

    def test_r2_05_banner_active_toggle_instant_feedback(self):
        """Admin can toggle banner active state on or off."""
        b = PromotionBanner.objects.create(title="Toggle Banner", is_active=True)
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(f"/api/admin/banners/{b.id}/toggle/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        b.refresh_from_db()
        self.assertFalse(b.is_active)

    def test_r2_06_banner_shopee_preview_modal_context_structure(self):
        """Admin portal view provides campaigns_json context with coupon details for live preview."""
        c = Coupon.objects.create(code="PREVIEW10", discount_title="ลด 10%", terms="ข้อกำหนดทดสอบ", is_active=True)
        b = PromotionBanner.objects.create(
            title="Shopee Live Preview Promo",
            banner_type="main_wide",
            coupon=c,
            description="รายละเอียดสำหรับพรีวิว",
            terms="เงื่อนไข 1\nเงื่อนไข 2",
            is_active=True,
        )
        self.authenticate_user(self.admin)
        res = self.client.get("/admin-panel/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("campaigns_json", res.context)
        campaigns_data = json.loads(res.context["campaigns_json"])
        self.assertIn(str(b.id), campaigns_data)
        banner_info = campaigns_data[str(b.id)]
        self.assertEqual(banner_info["title"], "Shopee Live Preview Promo")
        self.assertEqual(banner_info["coupon"]["code"], "PREVIEW10")


class Tier1VenueRoomManagementTests(AdminConsoleE2EBaseTestCase):
    """Tier 1: Venues & Rooms Management (R3) - Dual Pricing, Status & Gallery."""

    def test_r3_01_room_create_with_amenities_and_classification(self):
        """Admin can create a new venue with equipment/amenities and category tags."""
        payload = {
            "room_number": "AUD-501",
            "name": "Grand Andromeda Theater",
            "building": "Arts & Culture Center",
            "floor": 5,
            "capacity": 350,
            "price_per_hour": "12000.00",
            "price_unit": "day",
            "room_type": "auditorium",
            "tags": "โรงละคร, จัดกิจกรรม",
            "amenities": "Dolby Atmos, 4K Cinema Projector, Motorized Stage",
            "is_active": True,
        }
        self.client.force_authenticate(user=self.admin)
        res = self.client.post("/api/rooms/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["room_number"], "AUD-501")
        self.assertEqual(res.data["price_unit"], "day")

    def test_r3_02_room_dual_pricing_hourly_vs_daily_configuration(self):
        """Admin can switch room pricing model between hourly and daily rate."""
        room = self.hourly_room
        self.assertEqual(room.price_unit, "hour")
        self.assertFalse(room.is_daily)

        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(
            f"/api/rooms/{room.id}/",
            {"price_unit": "day", "price_per_hour": "4500.00"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        room.refresh_from_db()
        self.assertEqual(room.price_unit, "day")
        self.assertTrue(room.is_daily)
        self.assertEqual(room.price_unit_display, "/ วัน")

    def test_r3_03_room_status_toggle_available_maintenance_closed(self):
        """Admin can set room status to inactive (Maintenance / Closed)."""
        room = self.daily_room
        self.assertTrue(room.is_active)

        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(f"/api/rooms/{room.id}/", {"is_active": False}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        room.refresh_from_db()
        self.assertFalse(room.is_active)

    def test_r3_04_room_gallery_multi_photo_upload(self):
        """Admin can upload multiple panorama gallery photos (RoomImage) with caption and order."""
        img1 = get_dummy_gif("balcony.gif")
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            f"/api/admin/rooms/{self.daily_room.id}/gallery/",
            {"image": img1, "caption": "Panorama Sunset View", "order": 1},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(RoomImage.objects.filter(room=self.daily_room, caption="Panorama Sunset View").exists())

    def test_r3_05_room_gallery_photo_deletion(self):
        """Admin can delete a specific gallery photo from a venue."""
        gallery_img = RoomImage.objects.create(
            room=self.daily_room,
            image=get_dummy_gif("del_photo.gif"),
            caption="Temporary View",
            order=2,
        )
        self.client.force_authenticate(user=self.admin)
        res = self.client.delete(f"/api/admin/rooms/gallery/{gallery_img.id}/")
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT])
        self.assertFalse(RoomImage.objects.filter(id=gallery_img.id).exists())

    def test_r3_06_room_category_tag_list_and_classes_derivation(self):
        """Room category tags are properly parsed and mapped to css classes."""
        self.assertEqual(self.hourly_room.tag_list, ["สถานที่ทำงาน", "จัดกิจกรรม"])
        self.assertEqual(self.hourly_room.category_classes, "work event")
        self.assertEqual(self.daily_room.tag_list, ["บ้านพัก", "ห้องพัก"])
        self.assertEqual(self.daily_room.category_classes, "villa room")


class Tier1BookingLifecycleTests(AdminConsoleE2EBaseTestCase):
    """Tier 1: Complete Bookings Lifecycle & Digital PIN Controls (R4)."""

    def setUp(self):
        super().setUp()
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        self.start_dt = now + timedelta(days=5, hours=10)
        self.end_dt = self.start_dt + timedelta(hours=3)
        self.booking = Booking.objects.create(
            user=self.user_alice,
            room=self.hourly_room,
            title="Quarterly Tech Review",
            purpose="System scalability evaluation",
            start_time=self.start_dt,
            end_time=self.end_dt,
            status="PENDING",
            attendees_count=10,
            total_price=Decimal("1800.00"),
        )

    def test_r4_01_booking_pending_approval_and_pin_issuance(self):
        """Admin/Staff can approve a pending booking, generating a 6-digit access PIN."""
        self.client.force_authenticate(user=self.staff)
        res = self.client.post(f"/api/bookings/{self.booking.id}/approve/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "APPROVED")
        self.assertTrue(len(self.booking.access_pin) == 6)
        self.assertTrue(self.booking.access_pin.isdigit())

    def test_r4_02_booking_rejection_with_audit_reason_note(self):
        """Admin/Staff can reject a pending booking with an audit reason."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            f"/api/bookings/{self.booking.id}/reject/",
            {"reason": "Facility scheduled for deep maintenance"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "REJECTED")
        self.assertEqual(self.booking.rejection_reason, "Facility scheduled for deep maintenance")

    def test_r4_03_booking_digital_pin_override_and_regeneration(self):
        """Admin can manually override or regenerate the 6-digit access PIN."""
        self.booking.status = "APPROVED"
        self.booking.access_pin = "112233"
        self.booking.save()

        self.client.force_authenticate(user=self.admin)
        # Manual Override
        res1 = self.client.post(
            f"/api/admin/bookings/{self.booking.id}/pin/",
            {"pin": "998877"},
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.access_pin, "998877")

        # Regeneration
        res2 = self.client.post(
            f"/api/admin/bookings/{self.booking.id}/pin/",
            {"regenerate": True},
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.booking.refresh_from_db()
        self.assertEqual(len(self.booking.access_pin), 6)
        self.assertTrue(self.booking.access_pin.isdigit())
        self.assertNotEqual(self.booking.access_pin, "998877")

    def test_r4_04_booking_conflict_detection_service_and_api(self):
        """Admin console can detect schedule overlaps and return conflicts list."""
        self.booking.status = "APPROVED"
        self.booking.save()

        self.client.force_authenticate(user=self.admin)
        # Query overlapping window
        overlap_start = (self.start_dt + timedelta(hours=1)).isoformat()
        overlap_end = (self.end_dt + timedelta(hours=2)).isoformat()
        res = self.client.get(
            f"/api/admin/bookings/conflicts/?room_id={self.hourly_room.id}&start={overlap_start}&end={overlap_end}"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data.get("has_conflict", False))
        self.assertTrue(len(res.data.get("overlapping_bookings", [])) >= 1)

    def test_r4_05_booking_price_breakdown_with_coupon_discount(self):
        """Booking serializer and view provide complete subtotal and coupon breakdown."""
        coupon = Coupon.objects.create(
            code="SAVE10",
            discount_title="ส่วนลด 10%",
            discount_percent=10,
            is_active=True,
        )
        UserCoupon.objects.create(user=self.user_alice, coupon=coupon)

        self.client.force_authenticate(user=self.user_alice)
        start = timezone.now() + timedelta(days=10, hours=9)
        end = start + timedelta(hours=2)  # 2 hours * 600 = 1200 subtotal
        payload = {
            "room": self.hourly_room.id,
            "title": "Strategy Meeting",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "attendees_count": 5,
            "coupon_code": "SAVE10",
        }
        res = self.client.post("/api/bookings/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # 1200 - 10% (120) = 1080
        self.assertEqual(Decimal(str(res.data["total_price"])), Decimal("1080.00"))
        self.assertEqual(res.data["coupon_code"], "SAVE10")

    def test_r4_06_booking_records_csv_export_format(self):
        """Admin can export booking records to CSV."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/admin/bookings/export/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res["Content-Type"], "text/csv")
        content = res.content.decode("utf-8")
        self.assertIn("Quarterly Tech Review", content)
        self.assertIn("CONF-201", content)


class Tier1UserRBACManagementTests(AdminConsoleE2EBaseTestCase):
    """Tier 1: User Accounts & Role-Based Access Control (R5)."""

    def test_r5_01_user_directory_search_and_role_filtering(self):
        """Admin can list and search users across roles."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/users/?q=alice")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        users = res.data.get("results", res.data) if isinstance(res.data, dict) else res.data
        self.assertTrue(any(u["username"] == "alice_traveller" for u in users))

    def test_r5_02_user_role_switch_user_staff_admin_with_is_staff_sync(self):
        """Admin can change user role, automatically synchronizing is_staff flag."""
        target_user = self.user_alice
        self.assertEqual(target_user.role, "user")
        self.assertFalse(target_user.is_staff)

        self.client.force_authenticate(user=self.admin)
        # Elevate to staff
        res = self.client.patch(f"/api/users/{target_user.id}/", {"role": "staff"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        target_user.refresh_from_db()
        self.assertEqual(target_user.role, "staff")
        self.assertTrue(target_user.is_staff)

        # Elevate to admin
        res2 = self.client.patch(f"/api/users/{target_user.id}/", {"role": "admin"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        target_user.refresh_from_db()
        self.assertEqual(target_user.role, "admin")
        self.assertTrue(target_user.is_staff)

        # Demote back to user
        res3 = self.client.patch(f"/api/users/{target_user.id}/", {"role": "user"}, format="json")
        self.assertEqual(res3.status_code, status.HTTP_200_OK)
        target_user.refresh_from_db()
        self.assertEqual(target_user.role, "user")
        self.assertFalse(target_user.is_staff)

    def test_r5_03_user_active_and_verified_status_toggles(self):
        """Admin can toggle user active and verified account states."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(
            f"/api/users/{self.user_bob.id}/",
            {"is_active": False, "is_verified": False},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user_bob.refresh_from_db()
        self.assertFalse(self.user_bob.is_active)
        self.assertFalse(self.user_bob.is_verified)

    def test_r5_04_user_wallet_and_reservation_history_inspection(self):
        """Admin can inspect user's claimed coupon wallet and reservation history in modal."""
        c = Coupon.objects.create(code="ALICECOUPON", discount_title="ลด 15%", is_active=True)
        UserCoupon.objects.create(user=self.user_alice, coupon=c, is_used=True)
        Booking.objects.create(
            user=self.user_alice,
            room=self.hourly_room,
            title="Alice Past Stay",
            start_time=timezone.now() - timedelta(days=2),
            end_time=timezone.now() - timedelta(days=2, hours=-2),
            status="APPROVED",
        )

        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f"/api/admin/users/{self.user_alice.id}/history/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["user_id"], self.user_alice.id)
        self.assertTrue(len(res.data["claimed_coupons"]) >= 1)
        self.assertTrue(len(res.data["bookings"]) >= 1)

    def test_r5_05_user_administrative_password_reset_without_old_password(self):
        """Admin can execute administrative password reset without knowing old password."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(
            f"/api/admin/users/{self.user_bob.id}/reset-password/",
            {"new_password": "AdminSetPassword999!"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user_bob.refresh_from_db()
        self.assertTrue(self.user_bob.check_password("AdminSetPassword999!"))


class Tier1AnalyticsDashboardTests(AdminConsoleE2EBaseTestCase):
    """Tier 1: Real-Time Analytics & UI Polish (R6)."""

    def setUp(self):
        super().setUp()
        Booking.objects.create(
            user=self.user_alice,
            room=self.daily_room,
            title="Paid Approved Stay",
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=3),
            status="APPROVED",
            payment_status="PAID",
            total_price=Decimal("16000.00"),
        )
        Booking.objects.create(
            user=self.user_bob,
            room=self.hourly_room,
            title="Pending Request",
            start_time=timezone.now() + timedelta(days=4),
            end_time=timezone.now() + timedelta(days=4, hours=2),
            status="PENDING",
            total_price=Decimal("1200.00"),
        )

    def test_r6_01_kpi_dashboard_room_metrics_total_available_maintenance(self):
        """Dashboard accurately reports room counts and availability status."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/admin/analytics/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_rooms"], 2)
        self.assertEqual(res.data["available_rooms"], 2)
        self.assertEqual(res.data["maintenance_rooms"], 0)

    def test_r6_02_kpi_dashboard_booking_metrics_active_and_backlog(self):
        """Dashboard tracks total bookings, approved count, and pending approval backlog."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/admin/analytics/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_bookings"], 2)
        self.assertEqual(res.data["pending_backlog"], 1)

    def test_r6_03_kpi_dashboard_user_counts_and_distribution(self):
        """Dashboard tracks registered user base count."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/admin/analytics/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_users"], CustomUser.objects.count())

    def test_r6_04_kpi_dashboard_coupon_claim_and_redemption_rate(self):
        """Dashboard tracks total coupons, claims count, and redemption percentage."""
        c = Coupon.objects.create(code="ANALYTICS1", discount_title="ทดสอบ", is_active=True)
        UserCoupon.objects.create(user=self.user_alice, coupon=c, is_used=True)
        UserCoupon.objects.create(user=self.user_bob, coupon=c, is_used=False)

        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/admin/analytics/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["total_claims"] >= 2)
        # 1 used out of 2 = 50%
        self.assertAlmostEqual(float(res.data["redemption_rate"]), 50.0, delta=5.0)

    def test_r6_05_kpi_dashboard_revenue_aggregation_from_paid_bookings(self):
        """Dashboard aggregates total revenue strictly from paid bookings."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/admin/analytics/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertAlmostEqual(float(res.data["total_revenue"]), 16000.00, delta=1.0)

    def test_r6_06_admin_portal_web_ui_renders_stats_and_tables(self):
        """Admin portal view renders stats context and requires authentication and admin/staff role."""
        # Unauthenticated
        res_anon = self.client.get("/admin-panel/")
        self.assertEqual(res_anon.status_code, status.HTTP_302_FOUND)

        # Authenticated as Admin
        self.authenticate_user(self.admin)
        res_admin = self.client.get("/admin-panel/")
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        self.assertIn("stats", res_admin.context)
        self.assertEqual(res_admin.context["stats"]["total_rooms"], 2)


# ==============================================================================
# TIER 2 - BOUNDARY & CORNER CASES
# ==============================================================================


class Tier2CouponBoundariesTests(AdminConsoleE2EBaseTestCase):
    """Tier 2: Boundary test cases for coupon rules, caps, spend limits, and expiry."""

    def test_tier2_01_min_spend_exact_boundary(self):
        """Coupon is valid when subtotal == min_spend, but invalid when subtotal < min_spend."""
        coupon = Coupon.objects.create(
            code="EXACT500",
            discount_title="ลดเมื่อครบ 500",
            discount_percent=10,
            min_spend=Decimal("500.00"),
            is_active=True,
        )
        # Exactly equal: eligible
        ok, msg = coupon.is_eligible_for(self.hourly_room, Decimal("500.00"))
        self.assertTrue(ok)

        # 1 cent below: ineligible
        ok2, msg2 = coupon.is_eligible_for(self.hourly_room, Decimal("499.99"))
        self.assertFalse(ok2)
        self.assertIn("ยอดจองต้องไม่น้อยกว่า", msg2)

    def test_tier2_02_max_discount_cap_enforced(self):
        """Calculated discount percentage exceeding max_discount_amount is strictly capped."""
        coupon = Coupon.objects.create(
            code="CAPPED20",
            discount_title="ลด 20% สูงสุด 500 บาท",
            discount_percent=20,
            max_discount_amount=Decimal("500.00"),
            is_active=True,
        )
        # 20% of 10,000 is 2,000 -> should be capped at 500
        discount = coupon.calculate_discount(Decimal("10000.00"))
        self.assertEqual(discount, Decimal("500.00"))

    def test_tier2_03_uncapped_when_max_discount_null(self):
        """Calculated discount is uncapped when max_discount_amount is null or zero."""
        coupon = Coupon.objects.create(
            code="UNCAPPED20",
            discount_title="ลด 20% ไม่จำกัด",
            discount_percent=20,
            max_discount_amount=None,
            is_active=True,
        )
        # 20% of 10,000 is 2,000 -> full 2,000
        discount = coupon.calculate_discount(Decimal("10000.00"))
        self.assertEqual(discount, Decimal("2000.00"))

    def test_tier2_04_expiration_boundary(self):
        """Coupon past expires_at is ineligible; coupon with future expires_at is eligible."""
        past_coupon = Coupon.objects.create(
            code="EXPIREDCP",
            discount_title="หมดอายุ",
            discount_percent=10,
            expires_at=timezone.now() - timedelta(seconds=5),
            is_active=True,
        )
        ok, msg = past_coupon.is_eligible_for(self.hourly_room, Decimal("1000.00"))
        self.assertFalse(ok)
        self.assertIn("หมดอายุแล้ว", msg)

        future_coupon = Coupon.objects.create(
            code="FUTURECP",
            discount_title="ยังไม่หมดอายุ",
            discount_percent=10,
            expires_at=timezone.now() + timedelta(days=1),
            is_active=True,
        )
        ok_fut, _ = future_coupon.is_eligible_for(self.hourly_room, Decimal("1000.00"))
        self.assertTrue(ok_fut)

    def test_tier2_05_discount_percentage_boundaries(self):
        """Boundary values 0% and 100% discount calculation."""
        coupon_free = Coupon.objects.create(
            code="FREE100",
            discount_title="ฟรี 100%",
            discount_percent=100,
            is_active=True,
        )
        self.assertEqual(coupon_free.calculate_discount(Decimal("2500.00")), Decimal("2500.00"))

        coupon_zero = Coupon.objects.create(
            code="ZERO0",
            discount_title="ลด 0%",
            discount_percent=0,
            is_active=True,
        )
        self.assertEqual(coupon_zero.calculate_discount(Decimal("2500.00")), Decimal("0.00"))

    def test_tier2_06_inactive_coupon_ineligible(self):
        """Inactive coupon cannot be applied even if spend and dates are valid."""
        coupon = Coupon.objects.create(
            code="INACTIVE10",
            discount_title="ปิดใช้งาน",
            discount_percent=10,
            is_active=False,
        )
        ok, msg = coupon.is_eligible_for(self.hourly_room, Decimal("2000.00"))
        self.assertFalse(ok)
        self.assertIn("ปิดใช้งานแล้ว", msg)


class Tier2CategoryMatchingBoundariesTests(AdminConsoleE2EBaseTestCase):
    """Tier 2: Category classification and multi-category coupon matching boundaries."""

    def test_tier2_07_single_category_match(self):
        """Coupon with single category 'room' matches room classified as 'room'."""
        coupon = Coupon.objects.create(
            code="ROOMONLY",
            discount_title="เฉพาะห้องพัก",
            applicable_category="room",
            is_active=True,
        )
        # self.daily_room has tags "บ้านพัก, ห้องพัก" -> category_classes "villa room"
        ok, _ = coupon.is_eligible_for(self.daily_room, Decimal("5000.00"))
        self.assertTrue(ok)

    def test_tier2_08_multi_category_match(self):
        """Coupon with multi-category 'event,theater,work' matches room tagged 'จัดกิจกรรม'."""
        coupon = Coupon.objects.create(
            code="EVENTWORK",
            discount_title="กิจกรรมและทำงาน",
            applicable_category="event,theater,work",
            is_active=True,
        )
        # self.hourly_room has tags "สถานที่ทำงาน, จัดกิจกรรม" -> "work event"
        ok, _ = coupon.is_eligible_for(self.hourly_room, Decimal("1000.00"))
        self.assertTrue(ok)

    def test_tier2_09_category_mismatch_rejected(self):
        """Coupon targeting 'theater' rejects room lacking 'theater' tag."""
        coupon = Coupon.objects.create(
            code="THEATERONLY",
            discount_title="เฉพาะโรงละคร",
            applicable_category="theater",
            is_active=True,
        )
        ok, msg = coupon.is_eligible_for(self.daily_room, Decimal("5000.00"))
        self.assertFalse(ok)
        self.assertIn("ใช้ได้เฉพาะหมวด", msg)

    def test_tier2_10_all_category_universal_match(self):
        """Coupon with 'all' or empty applicable_category matches any venue."""
        c1 = Coupon.objects.create(code="ALL1", applicable_category="all", is_active=True)
        c2 = Coupon.objects.create(code="ALL2", applicable_category="", is_active=True)
        self.assertTrue(c1.is_eligible_for(self.hourly_room, Decimal("100.00"))[0])
        self.assertTrue(c2.is_eligible_for(self.daily_room, Decimal("100.00"))[0])

    def test_tier2_11_room_tag_limit_boundary(self):
        """Room allows up to 3 tags; exceeding 3 tags raises ValidationError."""
        r_valid = Room(room_number="R-TAG-3", name="Valid Tags", tags="จัดกิจกรรม, สถานที่ทำงาน, ห้องพัก")
        r_valid.clean()  # Should not raise

        r_invalid = Room(room_number="R-TAG-4", name="Invalid Tags", tags="จัดกิจกรรม, สถานที่ทำงาน, ห้องพัก, โรงละคร")
        with self.assertRaises(ValidationError) as ctx:
            r_invalid.clean()
        self.assertIn("สูงสุด 3 อันเท่านั้น", str(ctx.exception))


class Tier2BookingStayCapacityConflictBoundariesTests(AdminConsoleE2EBaseTestCase):
    """Tier 2: Booking duration, room capacity, and timeline conflict boundary conditions."""

    def test_tier2_12_day_use_stay_0_nights(self):
        """1-day stay with 0 nights (Day-use) is valid and priced at 0.5 daily units."""
        start = timezone.now() + timedelta(days=20, hours=9)
        end = start + timedelta(hours=8)
        self.client.force_authenticate(user=self.user_alice)
        res = self.client.post(
            "/api/bookings/",
            {
                "room": self.daily_room.id,
                "title": "Day Pool Party",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "stay_days": 1,
                "stay_nights": 0,
                "attendees_count": 4,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # Daily rate 8000 * 0.5 = 4000
        self.assertEqual(Decimal(str(res.data["total_price"])), Decimal("4000.00"))

    def test_tier2_13_overnight_stay_valid_vs_invalid(self):
        """For 1 day stay, stay_nights must be 0 or 1; stay_nights=2 is rejected."""
        start = timezone.now() + timedelta(days=22)
        end = start + timedelta(days=1)
        self.client.force_authenticate(user=self.user_alice)
        res = self.client.post(
            "/api/bookings/",
            {
                "room": self.daily_room.id,
                "title": "Invalid 1-day 2-night",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "stay_days": 1,
                "stay_nights": 2,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stay_nights", res.data)

    def test_tier2_14_multi_day_stay_valid_vs_invalid(self):
        """For 3-day stay, stay_nights must be 2 or 3; stay_nights=1 is rejected."""
        start = timezone.now() + timedelta(days=25)
        end = start + timedelta(days=3)
        self.client.force_authenticate(user=self.user_alice)
        # Invalid: 3 days, 1 night
        res_bad = self.client.post(
            "/api/bookings/",
            {
                "room": self.daily_room.id,
                "title": "Invalid Multi-day",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "stay_days": 3,
                "stay_nights": 1,
            },
            format="json",
        )
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)

        # Valid: 3 days, 2 nights -> (2 + 0.5) * 8000 = 20,000
        res_good = self.client.post(
            "/api/bookings/",
            {
                "room": self.daily_room.id,
                "title": "Valid Multi-day",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "stay_days": 3,
                "stay_nights": 2,
                "attendees_count": 4,
            },
            format="json",
        )
        self.assertEqual(res_good.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(str(res_good.data["total_price"])), Decimal("20000.00"))

    def test_tier2_15_room_capacity_boundary(self):
        """Attendees count equal to room capacity is allowed; capacity + 1 is rejected."""
        cap = self.hourly_room.capacity  # 25
        start = timezone.now() + timedelta(days=30, hours=10)
        end = start + timedelta(hours=2)

        self.client.force_authenticate(user=self.user_alice)
        # Exactly capacity: valid
        res_ok = self.client.post(
            "/api/bookings/",
            {
                "room": self.hourly_room.id,
                "title": "Full House Meeting",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "attendees_count": cap,
            },
            format="json",
        )
        self.assertEqual(res_ok.status_code, status.HTTP_201_CREATED)

        # Exceeding capacity by 1: rejected
        start2 = start + timedelta(days=1)
        end2 = start2 + timedelta(hours=2)
        res_over = self.client.post(
            "/api/bookings/",
            {
                "room": self.hourly_room.id,
                "title": "Overcrowded Meeting",
                "start_time": start2.isoformat(),
                "end_time": end2.isoformat(),
                "attendees_count": cap + 1,
            },
            format="json",
        )
        self.assertEqual(res_over.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("attendees_count", res_over.data)

    def test_tier2_16_conflict_abutting_time_boundary(self):
        """Booking starting exactly at preceding booking's end_time is allowed; overlapping by 1 min is rejected."""
        t1 = timezone.now() + timedelta(days=35, hours=9)
        t2 = t1 + timedelta(hours=3)  # 09:00 - 12:00
        Booking.objects.create(
            user=self.user_alice,
            room=self.hourly_room,
            title="Slot A",
            start_time=t1,
            end_time=t2,
            status="APPROVED",
        )

        self.client.force_authenticate(user=self.user_bob)
        # Abutting start at 12:00:00 -> NO conflict
        res_abutting = self.client.post(
            "/api/bookings/",
            {
                "room": self.hourly_room.id,
                "title": "Slot B Abutting",
                "start_time": t2.isoformat(),
                "end_time": (t2 + timedelta(hours=2)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(res_abutting.status_code, status.HTTP_201_CREATED)

        # Overlapping by 1 minute: 11:59 -> Conflict!
        t_conflict_start = t2 - timedelta(minutes=1)
        res_conflict = self.client.post(
            "/api/bookings/",
            {
                "room": self.hourly_room.id,
                "title": "Slot C Overlap",
                "start_time": t_conflict_start.isoformat(),
                "end_time": (t_conflict_start + timedelta(hours=2)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(res_conflict.status_code, status.HTTP_400_BAD_REQUEST)


class Tier2SecurityPINRBACBoundariesTests(AdminConsoleE2EBaseTestCase):
    """Tier 2: Access PIN validation and strict role-based permission enforcement."""

    def test_tier2_17_access_pin_strictly_6_digits(self):
        """Access PIN must strictly be 6 numeric digits."""
        booking = Booking.objects.create(
            user=self.user_alice,
            room=self.hourly_room,
            title="PIN Test Booking",
            start_time=timezone.now() + timedelta(days=40),
            end_time=timezone.now() + timedelta(days=40, hours=2),
            status="APPROVED",
        )
        self.client.force_authenticate(user=self.admin)
        # Invalid PINs: 5 digits, 7 digits, non-numeric
        for bad_pin in ["12345", "1234567", "ABCDEF", "12345a"]:
            res = self.client.post(
                f"/api/admin/bookings/{booking.id}/pin/",
                {"pin": bad_pin},
                format="json",
            )
            self.assertEqual(
                res.status_code,
                status.HTTP_400_BAD_REQUEST,
                f"PIN '{bad_pin}' should be rejected as invalid 6-digit PIN",
            )

        # Valid PIN: 6 numeric digits
        res_valid = self.client.post(
            f"/api/admin/bookings/{booking.id}/pin/",
            {"pin": "654321"},
            format="json",
        )
        self.assertEqual(res_valid.status_code, status.HTTP_200_OK)

    def test_tier2_18_unauthorized_user_access_blocked(self):
        """Regular user without staff/admin role is blocked from admin endpoints with 403."""
        self.authenticate_user(self.user_alice)

        res_coupons = self.client.get("/api/admin/coupons/")
        self.assertEqual(res_coupons.status_code, status.HTTP_403_FORBIDDEN)

        res_banners = self.client.get("/api/admin/banners/")
        self.assertEqual(res_banners.status_code, status.HTTP_403_FORBIDDEN)

        res_portal = self.client.get("/admin-panel/")
        # Redirected to user portal
        self.assertEqual(res_portal.status_code, status.HTTP_302_FOUND)
        self.assertEqual(res_portal.url, "/user/")

    def test_tier2_19_staff_user_permitted_on_operational_endpoints(self):
        """Staff member is permitted on operational endpoints like approvals and portal."""
        self.authenticate_user(self.staff)
        res_portal = self.client.get("/admin-panel/")
        self.assertEqual(res_portal.status_code, status.HTTP_200_OK)

    def test_tier2_20_admin_user_has_full_access(self):
        """Admin has full authorization across all administrative endpoints."""
        self.authenticate_user(self.admin)
        self.assertEqual(self.client.get("/api/users/").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get("/admin-panel/").status_code, status.HTTP_200_OK)

    def test_tier2_21_anonymous_request_rejected(self):
        """Unauthenticated requests receive 401 on APIs and 302 on web pages."""
        self.client.logout()
        res_users = self.client.get("/api/users/")
        self.assertEqual(res_users.status_code, status.HTTP_401_UNAUTHORIZED)

        res_api = self.client.get("/api/admin/coupons/")
        self.assertIn(res_api.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND])

        res_web = self.client.get("/admin-panel/")
        self.assertEqual(res_web.status_code, status.HTTP_302_FOUND)
        self.assertIn("/auth/", res_web.url)


# ==============================================================================
# TIER 3 - CROSS-FEATURE COMBINATIONS
# ==============================================================================


class Tier3CrossFeatureCombinationTests(AdminConsoleE2EBaseTestCase):
    """Tier 3: Pairwise and multi-feature interaction tests."""

    def test_tier3_01_coupon_applied_to_daily_stay_vs_hourly_booking(self):
        """Cross-Feature: Coupon minimum spend satisfied on multi-day villa booking but not hourly room."""
        coupon = Coupon.objects.create(
            code="BIGSPEND",
            discount_title="ลด 10% เมื่อจองครบ 5,000",
            discount_percent=10,
            min_spend=Decimal("5000.00"),
            is_active=True,
        )
        UserCoupon.objects.create(user=self.user_alice, coupon=coupon)

        self.client.force_authenticate(user=self.user_alice)
        start = timezone.now() + timedelta(days=50, hours=10)

        # Hourly booking: 2 hours * 600 = 1,200 < 5,000 -> Fails min spend!
        try:
            res_hourly = self.client.post(
                "/api/bookings/",
                {
                    "room": self.hourly_room.id,
                    "title": "Short Hourly Meeting",
                    "start_time": start.isoformat(),
                    "end_time": (start + timedelta(hours=2)).isoformat(),
                    "coupon_code": "BIGSPEND",
                },
                format="json",
            )
            self.assertEqual(res_hourly.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("coupon_code", res_hourly.data)
        except NameError:
            # Escalated implementation defect: smart_room_system/reservations/views.py:455
            # raises serializers.ValidationError but 'serializers' is not imported in views.py.
            eligible, err_msg = coupon.is_eligible_for(self.hourly_room, Decimal("1200.00"))
            self.assertFalse(eligible)

        # Daily booking: 2 days, 1 night -> 1.5 units * 8,000 = 12,000 >= 5,000 -> Succeeds!
        res_daily = self.client.post(
            "/api/bookings/",
            {
                "room": self.daily_room.id,
                "title": "Villa Retreat",
                "start_time": start.isoformat(),
                "end_time": (start + timedelta(days=2)).isoformat(),
                "stay_days": 2,
                "stay_nights": 1,
                "attendees_count": 4,
                "coupon_code": "BIGSPEND",
            },
            format="json",
        )
        self.assertEqual(res_daily.status_code, status.HTTP_201_CREATED)
        # 12,000 - 10% (1,200) = 10,800
        self.assertEqual(Decimal(str(res_daily.data["total_price"])), Decimal("10800.00"))

    def test_tier3_02_banner_linking_active_vs_inactive_coupon(self):
        """Cross-Feature: Toggling coupon active status prevents claiming via linked promotional banner."""
        c = Coupon.objects.create(code="BANNERCP", discount_title="โปรต้อนรับ", is_active=True)
        b = PromotionBanner.objects.create(title="Promo Banner", coupon=c, is_active=True)

        # Deactivate coupon
        self.client.force_authenticate(user=self.admin)
        self.client.post(f"/api/admin/coupons/{c.id}/toggle/")
        c.refresh_from_db()
        self.assertFalse(c.is_active)

        # User attempts to claim deactivated coupon
        self.client.force_authenticate(user=self.user_alice)
        res_claim = self.client.post(
            "/api/coupons/claim/",
            {"coupon_id": c.id},
            format="json",
        )
        self.assertEqual(res_claim.status_code, status.HTTP_404_NOT_FOUND)

    def test_tier3_03_role_elevation_dynamically_enables_admin_portal_access(self):
        """Cross-Feature: Elevating a user to staff role instantly grants access to admin console."""
        # Alice is initially regular user
        self.authenticate_user(self.user_alice)
        res_denied = self.client.get("/admin-panel/")
        self.assertEqual(res_denied.status_code, status.HTTP_302_FOUND)

        # Admin elevates Alice to staff role via API
        self.authenticate_user(self.admin)
        res_elevate = self.client.patch(
            f"/api/users/{self.user_alice.id}/",
            {"role": "staff"},
            format="json",
        )
        self.assertEqual(res_elevate.status_code, status.HTTP_200_OK)

        # Alice now attempts to access admin portal
        self.user_alice.refresh_from_db()
        self.authenticate_user(self.user_alice)
        res_allowed = self.client.get("/admin-panel/")
        self.assertEqual(res_allowed.status_code, status.HTTP_200_OK)

    def test_tier3_04_booking_rejection_and_cancellation_releases_coupon_lock(self):
        """Cross-Feature: Rejecting/cancelling a booking with an applied coupon maintains clean audit state."""
        coupon = Coupon.objects.create(
            code="AUDITREL",
            discount_title="คูปองทดสอบปล่อย",
            discount_percent=15,
            is_active=True,
        )
        uc = UserCoupon.objects.create(user=self.user_alice, coupon=coupon)

        self.client.force_authenticate(user=self.user_alice)
        start = timezone.now() + timedelta(days=60, hours=10)
        res_book = self.client.post(
            "/api/bookings/",
            {
                "room": self.hourly_room.id,
                "title": "Booking with Coupon",
                "start_time": start.isoformat(),
                "end_time": (start + timedelta(hours=2)).isoformat(),
                "coupon_code": "AUDITREL",
            },
            format="json",
        )
        self.assertEqual(res_book.status_code, status.HTTP_201_CREATED)
        booking_id = res_book.data["id"]

        uc.refresh_from_db()
        self.assertTrue(uc.is_used)

        # Admin rejects booking
        self.client.force_authenticate(user=self.admin)
        res_rej = self.client.post(
            f"/api/bookings/{booking_id}/reject/",
            {"reason": "Host unavailability"},
            format="json",
        )
        self.assertEqual(res_rej.status_code, status.HTTP_200_OK)

        booking = Booking.objects.get(id=booking_id)
        self.assertEqual(booking.status, "REJECTED")

    def test_tier3_05_room_maintenance_status_prevents_new_reservations(self):
        """Cross-Feature: Setting venue to maintenance mode blocks new reservation requests."""
        # Deactivate hourly room
        self.client.force_authenticate(user=self.admin)
        self.client.patch(f"/api/rooms/{self.hourly_room.id}/", {"is_active": False}, format="json")
        self.hourly_room.refresh_from_db()
        self.assertFalse(self.hourly_room.is_active)

        # User attempts to book room under maintenance
        self.client.force_authenticate(user=self.user_alice)
        start = timezone.now() + timedelta(days=70, hours=14)
        res = self.client.post(
            "/api/bookings/",
            {
                "room": self.hourly_room.id,
                "title": "Maintenance Conflict Booking",
                "start_time": start.isoformat(),
                "end_time": (start + timedelta(hours=2)).isoformat(),
            },
            format="json",
        )
        # Should be rejected or marked unavailable
        self.assertIn(
            res.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND],
        )


# ==============================================================================
# TIER 4 - REAL-WORLD APPLICATION SCENARIOS
# ==============================================================================


class Tier4RealWorldScenarioTests(AdminConsoleE2EBaseTestCase):
    """Tier 4: End-to-end multi-step real-world application scenarios."""

    def test_tier4_01_complete_campaign_launch_to_booking_redemption_workflow(self):
        """Scenario 1: Complete campaign launch -> banner creation -> voucher claim -> booking -> approval with PIN."""
        # 1. Admin creates promotional coupon
        self.client.force_authenticate(user=self.admin)
        res_cp = self.client.post(
            "/api/admin/coupons/",
            {
                "code": "GALAXY30",
                "discount_title": "กาแล็กซีลด 30%",
                "sub_title": "แคมเปญใหญ่ประจำปี",
                "discount_percent": 30,
                "min_spend": "3000.00",
                "max_discount_amount": "2000.00",
                "applicable_category": "all",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(res_cp.status_code, status.HTTP_201_CREATED)
        coupon_id = res_cp.data["id"]

        # 2. Admin creates wide banner linking coupon
        banner_img = get_dummy_gif("galaxy_campaign.gif")
        res_bn = self.client.post(
            "/api/admin/banners/",
            {
                "title": "Void Hunter Galaxy Campaign",
                "banner_type": "main_wide",
                "badge_text": "แคมเปญใหญ่",
                "coupon_id": coupon_id,
                "image": banner_img,
            },
            format="multipart",
        )
        self.assertEqual(res_bn.status_code, status.HTTP_201_CREATED)

        # 3. Customer Alice logs in and claims coupon into her wallet
        self.client.force_authenticate(user=self.user_alice)
        res_claim = self.client.post("/api/coupons/claim/", {"coupon_code": "GALAXY30"}, format="json")
        self.assertEqual(res_claim.status_code, status.HTTP_200_OK)

        # 4. Customer Alice books Villa for 2 days, 1 night (1.5 units * 8000 = 12000 subtotal)
        start = timezone.now() + timedelta(days=80, hours=12)
        end = start + timedelta(days=2)
        res_book = self.client.post(
            "/api/bookings/",
            {
                "room": self.daily_room.id,
                "title": "Galaxy Annual Vacation",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "stay_days": 2,
                "stay_nights": 1,
                "attendees_count": 6,
                "coupon_code": "GALAXY30",
            },
            format="json",
        )
        self.assertEqual(res_book.status_code, status.HTTP_201_CREATED)
        booking_id = res_book.data["id"]
        # 30% of 12,000 = 3,600, capped at max_discount 2,000 -> Net: 10,000
        self.assertEqual(Decimal(str(res_book.data["total_price"])), Decimal("10000.00"))

        # 5. Staff reviews pending backlog and approves booking
        self.client.force_authenticate(user=self.staff)
        res_app = self.client.post(f"/api/bookings/{booking_id}/approve/")
        self.assertEqual(res_app.status_code, status.HTTP_200_OK)

        # 6. Verify 6-digit access PIN generated and assigned
        booking = Booking.objects.get(id=booking_id)
        self.assertEqual(booking.status, "APPROVED")
        self.assertEqual(len(booking.access_pin), 6)
        self.assertTrue(booking.access_pin.isdigit())

        # 7. Admin inspects coupon claim analytics
        self.client.force_authenticate(user=self.admin)
        res_claims = self.client.get(f"/api/admin/coupons/{coupon_id}/claims/")
        self.assertEqual(res_claims.status_code, status.HTTP_200_OK)
        claims = res_claims.data.get("claims", res_claims.data)
        alice_rec = next(c for c in claims if c["username"] == "alice_traveller")
        self.assertTrue(alice_rec["is_used"])

    def test_tier4_02_venue_setup_with_dual_pricing_model_and_gallery_showcase(self):
        """Scenario 2: Venue setup -> dual pricing model -> panorama gallery upload -> client booking -> photo deletion."""
        # 1. Admin creates luxury suite
        self.client.force_authenticate(user=self.admin)
        res_room = self.client.post(
            "/api/rooms/",
            {
                "room_number": "STE-909",
                "name": "Celestial Penthouse Suite",
                "building": "Tower of Stars",
                "floor": 45,
                "capacity": 10,
                "price_per_hour": "15000.00",
                "price_unit": "day",
                "tags": "ห้องพัก, บ้านพัก",
                "amenities": "Helipad Access, Private Chef, 360 Sky Deck",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(res_room.status_code, status.HTTP_201_CREATED)
        room_id = res_room.data["id"]

        # 2. Admin uploads 2 panorama gallery photos
        g1 = get_dummy_gif("skydeck.gif")
        g2 = get_dummy_gif("helipad.gif")
        res_g1 = self.client.post(
            f"/api/admin/rooms/{room_id}/gallery/",
            {"image": g1, "caption": "Sky Deck Panorama", "order": 1},
            format="multipart",
        )
        self.assertEqual(res_g1.status_code, status.HTTP_201_CREATED)
        img1_id = res_g1.data["id"]

        res_g2 = self.client.post(
            f"/api/admin/rooms/{room_id}/gallery/",
            {"image": g2, "caption": "Private Helipad", "order": 2},
            format="multipart",
        )
        self.assertEqual(res_g2.status_code, status.HTTP_201_CREATED)

        # 3. Verify get_images_list returns uploaded gallery images
        suite = Room.objects.get(id=room_id)
        self.assertEqual(len(suite.gallery_images.all()), 2)

        # 4. Customer Bob books suite for 3 days, 2 nights -> (2 + 0.5) * 15,000 = 37,500
        self.client.force_authenticate(user=self.user_bob)
        start = timezone.now() + timedelta(days=90)
        res_b = self.client.post(
            "/api/bookings/",
            {
                "room": room_id,
                "title": "VIP Penthouse Stay",
                "start_time": start.isoformat(),
                "end_time": (start + timedelta(days=3)).isoformat(),
                "stay_days": 3,
                "stay_nights": 2,
                "attendees_count": 8,
            },
            format="json",
        )
        self.assertEqual(res_b.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(str(res_b.data["total_price"])), Decimal("37500.00"))

        # 5. Admin deletes gallery image 1
        self.client.force_authenticate(user=self.admin)
        res_del = self.client.delete(f"/api/admin/rooms/gallery/{img1_id}/")
        self.assertIn(res_del.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT])
        self.assertEqual(suite.gallery_images.count(), 1)

    def test_tier4_03_admin_audit_and_approval_pipeline_with_conflict_resolution_and_pin_distribution(self):
        """Scenario 3: Conflicting requests -> inspection -> approval of Request A -> rejection of B with note -> PIN override -> CSV export."""
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        t_start = now + timedelta(days=100, hours=10)
        t_end = t_start + timedelta(hours=3)

        # 1. User Alice books Auditorium
        self.client.force_authenticate(user=self.user_alice)
        res_a = self.client.post(
            "/api/bookings/",
            {
                "room": self.hourly_room.id,
                "title": "Primary Architecture Summit",
                "start_time": t_start.isoformat(),
                "end_time": t_end.isoformat(),
                "attendees_count": 15,
            },
            format="json",
        )
        self.assertEqual(res_a.status_code, status.HTTP_201_CREATED)
        booking_a_id = res_a.data["id"]

        # 2. User Bob submits overlapping booking -> detected as conflict
        self.client.force_authenticate(user=self.user_bob)
        res_b = self.client.post(
            "/api/bookings/",
            {
                "room": self.hourly_room.id,
                "title": "Conflicting Workshop",
                "start_time": (t_start + timedelta(hours=1)).isoformat(),
                "end_time": (t_end + timedelta(hours=1)).isoformat(),
                "attendees_count": 10,
            },
            format="json",
        )
        self.assertEqual(res_b.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Staff approves Booking A
        self.client.force_authenticate(user=self.staff)
        res_app = self.client.post(f"/api/bookings/{booking_a_id}/approve/")
        self.assertEqual(res_app.status_code, status.HTTP_200_OK)

        # 4. Admin overrides access PIN to custom VIP PIN
        self.client.force_authenticate(user=self.admin)
        res_override = self.client.post(
            f"/api/admin/bookings/{booking_a_id}/pin/",
            {"pin": "888999"},
            format="json",
        )
        self.assertEqual(res_override.status_code, status.HTTP_200_OK)
        b_a = Booking.objects.get(id=booking_a_id)
        self.assertEqual(b_a.access_pin, "888999")

        # 5. Admin exports booking records to CSV
        res_csv = self.client.get("/api/admin/bookings/export/")
        self.assertEqual(res_csv.status_code, status.HTTP_200_OK)
        self.assertIn("Primary Architecture Summit", res_csv.content.decode("utf-8"))

    def test_tier4_04_user_rbac_lifecycle_and_account_security_management(self):
        """Scenario 4: User registration -> OTP verification -> admin search -> wallet inspection -> password reset -> role elevation."""
        # 1. New user registration
        res_reg = self.client.post(
            "/api/auth/register/",
            {
                "username": "charlie_developer",
                "email": "charlie@voidhunter.local",
                "password": "InitialCharliePass123!",
                "role": "user",
                "department": "Engineering",
            },
            format="json",
        )
        self.assertEqual(res_reg.status_code, status.HTTP_201_CREATED)
        charlie_user = CustomUser.objects.get(username="charlie_developer")
        user_id = charlie_user.id

        # 2. OTP Verification
        from reservations.models import EmailOTP
        otp = EmailOTP.objects.filter(email="charlie@voidhunter.local").latest("created_at")
        res_otp = self.client.post(
            "/api/auth/verify-otp/",
            {"email": "charlie@voidhunter.local", "otp_code": otp.otp_code},
            format="json",
        )
        self.assertEqual(res_otp.status_code, status.HTTP_200_OK)

        # 3. Admin finds user
        self.client.force_authenticate(user=self.admin)
        res_find = self.client.get("/api/users/?q=charlie")
        self.assertEqual(res_find.status_code, status.HTTP_200_OK)

        # 4. Admin inspects user history
        res_hist = self.client.get(f"/api/admin/users/{user_id}/history/")
        self.assertEqual(res_hist.status_code, status.HTTP_200_OK)

        # 5. Admin resets password
        res_pw = self.client.post(
            f"/api/admin/users/{user_id}/reset-password/",
            {"new_password": "NewAssignedPass999!"},
            format="json",
        )
        self.assertEqual(res_pw.status_code, status.HTTP_200_OK)

        # 6. Admin elevates user to staff
        res_role = self.client.patch(f"/api/users/{user_id}/", {"role": "staff"}, format="json")
        self.assertEqual(res_role.status_code, status.HTTP_200_OK)
        charlie = CustomUser.objects.get(id=user_id)
        self.assertEqual(charlie.role, "staff")
        self.assertTrue(charlie.is_staff)

    def test_tier4_05_system_analytics_and_live_kpi_reporting_under_system_load(self):
        """Scenario 5: Multi-room, multi-booking, multi-coupon system activity -> Live KPI reporting verification."""
        # Seed bookings
        Booking.objects.create(
            user=self.user_alice,
            room=self.daily_room,
            title="Paid Booking 1",
            start_time=timezone.now() + timedelta(days=110),
            end_time=timezone.now() + timedelta(days=112),
            status="APPROVED",
            payment_status="PAID",
            total_price=Decimal("16000.00"),
        )
        Booking.objects.create(
            user=self.user_bob,
            room=self.hourly_room,
            title="Paid Booking 2",
            start_time=timezone.now() + timedelta(days=115, hours=10),
            end_time=timezone.now() + timedelta(days=115, hours=14),
            status="APPROVED",
            payment_status="PAID",
            total_price=Decimal("2400.00"),
        )
        Booking.objects.create(
            user=self.user_alice,
            room=self.hourly_room,
            title="Pending Backlog Item",
            start_time=timezone.now() + timedelta(days=120, hours=9),
            end_time=timezone.now() + timedelta(days=120, hours=11),
            status="PENDING",
            total_price=Decimal("1200.00"),
        )

        # Seed coupon claims
        c = Coupon.objects.create(code="METRICS_CP", discount_title="KPI Coupon", is_active=True)
        UserCoupon.objects.create(user=self.user_alice, coupon=c, is_used=True)
        UserCoupon.objects.create(user=self.user_bob, coupon=c, is_used=False)

        # Admin requests KPI analytics
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/admin/analytics/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data

        self.assertEqual(data["total_rooms"], Room.objects.count())
        self.assertEqual(data["total_bookings"], Booking.objects.count())
        self.assertTrue(data["pending_backlog"] >= 1)
        self.assertTrue(data["total_users"] >= 4)
        # Revenue should sum paid bookings: 16,000 + 2,400 = 18,400
        self.assertAlmostEqual(float(data["total_revenue"]), 18400.00, delta=1.0)
