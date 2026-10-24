"""
Adversarial Empirical Stress Test Suite for Void Hunter (VH) Coupon Management (R1)
Thoroughly stress-tests all boundary conditions, validation logic, RBAC, expiration,
claim analytics, and edge cases.
"""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from reservations.models import (
    CustomUser,
    Room,
    Coupon,
    UserCoupon,
)


class CouponStressAdversarialBaseTestCase(TestCase):
    """Base setup fixture providing role-based actors and standard test venues."""

    def setUp(self):
        self.client = APIClient()

        # Admin user
        self.admin = CustomUser.objects.create_superuser(
            username="stress_admin",
            email="admin@adversarial.local",
            password="AdminPassword123!",
            role="admin",
            department="QA Engineering",
            is_staff=True,
            is_verified=True,
        )

        # Staff user
        self.staff = CustomUser.objects.create_user(
            username="stress_staff",
            email="staff@adversarial.local",
            password="StaffPassword123!",
            role="staff",
            department="Operations",
            is_staff=True,
            is_verified=True,
        )

        # Regular user
        self.regular_user = CustomUser.objects.create_user(
            username="stress_user",
            email="user@adversarial.local",
            password="UserPassword123!",
            role="user",
            department="Customer",
            is_staff=False,
            is_verified=True,
        )

        # Test room 1: Meeting room (work, event)
        self.room_meeting = Room.objects.create(
            room_number="CONF-901",
            name="Alpha Boardroom",
            building="Tower A",
            floor=9,
            capacity=20,
            price_per_hour=Decimal("500.00"),
            price_unit="hour",
            tags="สถานที่ทำงาน, จัดกิจกรรม",
            is_active=True,
        )

        # Test room 2: Vacation villa (room, villa)
        self.room_villa = Room.objects.create(
            room_number="VILLA-301",
            name="Sunset Cliff Villa",
            building="Zone B",
            floor=1,
            capacity=6,
            price_per_hour=Decimal("5000.00"),
            price_unit="day",
            tags="บ้านพัก, ห้องพัก",
            is_active=True,
        )

        # Test room 3: Theater room (theater)
        self.room_theater = Room.objects.create(
            room_number="THEAT-101",
            name="Cinema Hall",
            building="Arts Block",
            floor=1,
            capacity=100,
            price_per_hour=Decimal("8000.00"),
            price_unit="day",
            tags="โรงละคร",
            is_active=True,
        )


class CouponMinSpendBoundaryAdversarialTests(CouponStressAdversarialBaseTestCase):
    """Stress tests for min_spend boundaries, decimal precision, and negative values."""

    def test_min_spend_boundary_exact_match(self):
        """Coupon is eligible when subtotal exactly equals min_spend."""
        coupon = Coupon.objects.create(
            code="EXACT1000",
            discount_title="ลดเมื่อครบ 1,000",
            discount_percent=10,
            min_spend=Decimal("1000.00"),
            is_active=True,
        )
        ok, msg = coupon.is_eligible_for(self.room_meeting, Decimal("1000.00"))
        self.assertTrue(ok, f"Exact min_spend match should be eligible, got: {msg}")

    def test_min_spend_boundary_one_cent_below(self):
        """Coupon is ineligible when subtotal is 0.01 below min_spend."""
        coupon = Coupon.objects.create(
            code="EXACT1000B",
            discount_title="ลดเมื่อครบ 1,000",
            discount_percent=10,
            min_spend=Decimal("1000.00"),
            is_active=True,
        )
        ok, msg = coupon.is_eligible_for(self.room_meeting, Decimal("999.99"))
        self.assertFalse(ok)
        self.assertIn("ยอดจองต้องไม่น้อยกว่า", msg)

    def test_min_spend_boundary_one_cent_above(self):
        """Coupon is eligible when subtotal is 0.01 above min_spend."""
        coupon = Coupon.objects.create(
            code="EXACT1000C",
            discount_title="ลดเมื่อครบ 1,000",
            discount_percent=10,
            min_spend=Decimal("1000.00"),
            is_active=True,
        )
        ok, msg = coupon.is_eligible_for(self.room_meeting, Decimal("1000.01"))
        self.assertTrue(ok)

    def test_min_spend_zero_accepts_any_subtotal(self):
        """Coupon with min_spend=0 is eligible for positive and zero subtotals."""
        coupon = Coupon.objects.create(
            code="NOMINSPEND",
            discount_title="ไม่มีขั้นต่ำ",
            discount_percent=15,
            min_spend=Decimal("0.00"),
            is_active=True,
        )
        ok_pos, _ = coupon.is_eligible_for(self.room_meeting, Decimal("50.00"))
        self.assertTrue(ok_pos)
        ok_zero, _ = coupon.is_eligible_for(self.room_meeting, Decimal("0.00"))
        self.assertTrue(ok_zero)

    def test_admin_create_negative_min_spend_rejected(self):
        """Serializer strictly rejects negative min_spend."""
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "NEGSPEND",
            "discount_title": "ส่วนลดติดลบ",
            "discount_percent": 10,
            "min_spend": "-100.00",
            "applicable_category": "all",
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("min_spend", res.data)

    def test_admin_patch_negative_min_spend_rejected(self):
        """Serializer strictly rejects updating min_spend to negative value."""
        coupon = Coupon.objects.create(
            code="VALIDSPEND",
            discount_title="ส่วนลด",
            discount_percent=10,
            min_spend=Decimal("500.00"),
            is_active=True,
        )
        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(f"/api/admin/coupons/{coupon.id}/", {"min_spend": "-50.00"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("min_spend", res.data)


class CouponDiscountPercentBoundaryAdversarialTests(CouponStressAdversarialBaseTestCase):
    """Stress tests for discount percent limits: 0%, 100%, negative, and > 100%."""

    def test_model_discount_zero_percent_returns_zero(self):
        """Model calculate_discount computes 0.00 discount for 0%."""
        coupon = Coupon.objects.create(
            code="ZERO_PCT",
            discount_title="ลด 0%",
            discount_percent=0,
            is_active=True,
        )
        discount = coupon.calculate_discount(Decimal("2500.00"))
        self.assertEqual(discount, Decimal("0.00"))

    def test_model_discount_100_percent_returns_full_subtotal(self):
        """Model calculate_discount computes full subtotal for 100%."""
        coupon = Coupon.objects.create(
            code="FULL_100",
            discount_title="ลด 100%",
            discount_percent=100,
            is_active=True,
        )
        discount = coupon.calculate_discount(Decimal("3750.50"))
        self.assertEqual(discount, Decimal("3750.50"))

    def test_admin_create_zero_percent_rejected_by_serializer(self):
        """AdminCouponSerializer strictly rejects 0% (requires 1-100%)."""
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "ZERO_DISC",
            "discount_title": "ส่วนลด 0%",
            "discount_percent": 0,
            "min_spend": "0.00",
            "applicable_category": "all",
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("discount_percent", res.data)

    def test_admin_create_100_percent_accepted_by_serializer(self):
        """AdminCouponSerializer accepts 100% boundary value."""
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "MAX_100_PCT",
            "discount_title": "ส่วนลด 100%",
            "sub_title": "สิทธิ์สมาชิกสูงสุด",
            "discount_percent": 100,
            "min_spend": "0.00",
            "applicable_category": "all",
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(int(res.data["discount_percent"]), 100)

    def test_admin_create_1_percent_boundary_accepted(self):
        """AdminCouponSerializer accepts 1% lower boundary value."""
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "MIN_1_PCT",
            "discount_title": "ส่วนลด 1%",
            "sub_title": "สิทธิ์ขั้นต่ำ",
            "discount_percent": 1,
            "min_spend": "0.00",
            "applicable_category": "all",
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(int(res.data["discount_percent"]), 1)

    def test_admin_create_over_100_percent_rejected(self):
        """AdminCouponSerializer rejects discount_percent > 100 (e.g. 101, 150)."""
        self.client.force_authenticate(user=self.admin)
        for bad_val in [101, 150, 999]:
            payload = {
                "code": f"OVER_{bad_val}",
                "discount_title": f"ส่วนลด {bad_val}%",
                "discount_percent": bad_val,
                "applicable_category": "all",
            }
            res = self.client.post("/api/admin/coupons/", payload, format="json")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("discount_percent", res.data)

    def test_admin_create_negative_percent_rejected(self):
        """AdminCouponSerializer rejects negative discount_percent."""
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "NEGATIVE_PCT",
            "discount_title": "ส่วนลดติดลบ",
            "discount_percent": -10,
            "applicable_category": "all",
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("discount_percent", res.data)


class CouponDiscountCapAdversarialTests(CouponStressAdversarialBaseTestCase):
    """Stress tests for max_discount_amount caps, uncapped behavior, and subtotal clamping."""

    def test_discount_strictly_capped_at_max_discount_amount(self):
        """When computed discount exceeds cap, discount equals max_discount_amount."""
        coupon = Coupon.objects.create(
            code="CAP500",
            discount_title="ลด 50% สูงสุด 500",
            discount_percent=50,
            max_discount_amount=Decimal("500.00"),
            is_active=True,
        )
        # 50% of 2000 is 1000 -> capped at 500
        discount = coupon.calculate_discount(Decimal("2000.00"))
        self.assertEqual(discount, Decimal("500.00"))

    def test_discount_not_capped_when_below_max_discount_amount(self):
        """When computed discount is below cap, actual percentage discount is used."""
        coupon = Coupon.objects.create(
            code="CAP500B",
            discount_title="ลด 10% สูงสุด 500",
            discount_percent=10,
            max_discount_amount=Decimal("500.00"),
            is_active=True,
        )
        # 10% of 2000 is 200 (< 500) -> 200
        discount = coupon.calculate_discount(Decimal("2000.00"))
        self.assertEqual(discount, Decimal("200.00"))

    def test_discount_uncapped_when_max_discount_is_none(self):
        """When max_discount_amount is None, full percentage discount is applied."""
        coupon = Coupon.objects.create(
            code="NOCAP",
            discount_title="ลด 30% ไม่จำกัด",
            discount_percent=30,
            max_discount_amount=None,
            is_active=True,
        )
        # 30% of 100,000 is 30,000
        discount = coupon.calculate_discount(Decimal("100000.00"))
        self.assertEqual(discount, Decimal("30000.00"))

    def test_discount_uncapped_when_max_discount_is_zero(self):
        """When max_discount_amount is 0.00, it is treated as uncapped."""
        coupon = Coupon.objects.create(
            code="CAPZERO",
            discount_title="ลด 20%",
            discount_percent=20,
            max_discount_amount=Decimal("0.00"),
            is_active=True,
        )
        discount = coupon.calculate_discount(Decimal("5000.00"))
        self.assertEqual(discount, Decimal("1000.00"))

    def test_discount_never_exceeds_subtotal(self):
        """Discount is clamped so it never exceeds the subtotal amount."""
        coupon = Coupon.objects.create(
            code="HIGH_CAP",
            discount_title="ลด 100% สูงสุด 10,000",
            discount_percent=100,
            max_discount_amount=Decimal("10000.00"),
            is_active=True,
        )
        # Subtotal is only 500 -> discount must not exceed 500
        discount = coupon.calculate_discount(Decimal("500.00"))
        self.assertEqual(discount, Decimal("500.00"))

    def test_admin_create_negative_max_discount_rejected(self):
        """Serializer strictly rejects negative max_discount_amount."""
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "NEGCAP",
            "discount_title": "ส่วนลด",
            "discount_percent": 10,
            "max_discount_amount": "-200.00",
            "applicable_category": "all",
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("max_discount_amount", res.data)


class CouponCategoryMultiSelectAdversarialTests(CouponStressAdversarialBaseTestCase):
    """Stress tests for category multi-select formatting, normalization, and room tag matching."""

    def test_category_comma_separated_string_stored_correctly(self):
        """Comma-separated string 'room,villa,event' is normalized and persisted."""
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "MULTICAT1",
            "discount_title": "หลายหมวดหมู่",
            "sub_title": "สิทธิ์พิเศษ",
            "discount_percent": 20,
            "applicable_category": "room,villa,event",
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["applicable_category"], "room,villa,event")
        self.assertEqual(res.data["applicable_categories"], ["room", "villa", "event"])

    def test_category_list_of_strings_converted_to_comma_string(self):
        """JSON list of categories ['villa', 'theater'] is converted into 'villa,theater'."""
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "MULTICAT2",
            "discount_title": "ลิสต์หมวดหมู่",
            "sub_title": "สิทธิ์พิเศษ",
            "discount_percent": 15,
            "applicable_category": ["villa", "theater"],
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["applicable_category"], "villa,theater")
        self.assertEqual(res.data["applicable_categories"], ["villa", "theater"])

    def test_category_whitespace_and_case_insensitive(self):
        """Categories with whitespace and uppercase ' Room , Villa ' are cleaned to 'room,villa'."""
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "CLEANCAT",
            "discount_title": "คลีนหมวดหมู่",
            "sub_title": "สิทธิ์พิเศษ",
            "discount_percent": 10,
            "applicable_category": " Room , Villa ",
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["applicable_category"], "room,villa")

    def test_category_all_with_specific_categories_removes_all(self):
        """Submitting 'all,room,villa' strips 'all' leaving 'room,villa'."""
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "STRIPALL",
            "discount_title": "ตัด all ออก",
            "sub_title": "สิทธิ์พิเศษ",
            "discount_percent": 10,
            "applicable_category": ["all", "room", "villa"],
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["applicable_category"], "room,villa")

    def test_category_invalid_choice_rejected(self):
        """Invalid category like 'flights' is rejected with descriptive error."""
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "BADCAT",
            "discount_title": "หมวดผิด",
            "sub_title": "สิทธิ์พิเศษ",
            "discount_percent": 10,
            "applicable_category": "room,flights",
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("applicable_category", res.data)
        self.assertIn("flights", str(res.data["applicable_category"]))

    def test_category_empty_string_or_list_defaults_to_all(self):
        """Empty category string or empty array defaults to 'all'."""
        self.client.force_authenticate(user=self.admin)
        res1 = self.client.post(
            "/api/admin/coupons/",
            {"code": "EMPTYCAT1", "discount_title": "ว่าง 1", "sub_title": "สิทธิ์พิเศษ", "discount_percent": 10, "applicable_category": ""},
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res1.data["applicable_category"], "all")

        res2 = self.client.post(
            "/api/admin/coupons/",
            {"code": "EMPTYCAT2", "discount_title": "ว่าง 2", "sub_title": "สิทธิ์พิเศษ", "discount_percent": 10, "applicable_category": []},
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res2.data["applicable_category"], "all")

    def test_room_category_matching_against_multiple_categories(self):
        """Multi-category coupon matches if room has at least one matching category."""
        coupon = Coupon.objects.create(
            code="MULTI_MATCH",
            discount_title="แมตช์หลายหมวด",
            applicable_category="theater,event",
            is_active=True,
        )
        # room_meeting has tags: สถานที่ทำงาน, จัดกิจกรรม -> category_classes: 'work event'
        ok_meeting, _ = coupon.is_eligible_for(self.room_meeting, Decimal("500.00"))
        self.assertTrue(ok_meeting)

        # room_theater has tags: โรงละคร -> category_classes: 'theater'
        ok_theater, _ = coupon.is_eligible_for(self.room_theater, Decimal("500.00"))
        self.assertTrue(ok_theater)

        # room_villa has tags: บ้านพัก, ห้องพัก -> category_classes: 'villa room' -> should fail
        ok_villa, msg_villa = coupon.is_eligible_for(self.room_villa, Decimal("500.00"))
        self.assertFalse(ok_villa)
        self.assertIn("ใช้ได้เฉพาะหมวด", msg_villa)


class CouponActiveToggleAdversarialTests(CouponStressAdversarialBaseTestCase):
    """Stress tests for coupon active/inactive status toggle endpoint and RBAC."""

    def test_toggle_active_status_cycle(self):
        """Toggling active status inverts boolean correctly and returns success response."""
        coupon = Coupon.objects.create(
            code="TOGGLE_ME",
            discount_title="ทดสอบสลับสถานะ",
            is_active=True,
        )
        self.client.force_authenticate(user=self.admin)

        # Cycle 1: True -> False
        res1 = self.client.post(f"/api/admin/coupons/{coupon.id}/toggle/")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertFalse(res1.data["is_active"])
        coupon.refresh_from_db()
        self.assertFalse(coupon.is_active)

        # Cycle 2: False -> True
        res2 = self.client.post(f"/api/admin/coupons/{coupon.id}/toggle/")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertTrue(res2.data["is_active"])
        coupon.refresh_from_db()
        self.assertTrue(coupon.is_active)

    def test_toggle_nonexistent_coupon_returns_404(self):
        """Toggling non-existent coupon ID returns 404 Not Found."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.post("/api/admin/coupons/999999/toggle/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_toggle_forbidden_for_regular_user(self):
        """Regular user without admin or staff role is denied (403 Forbidden)."""
        coupon = Coupon.objects.create(code="RBAC_TOGGLE", discount_title="ทดสอบสิทธิ์", is_active=True)
        self.client.force_authenticate(user=self.regular_user)
        res = self.client.post(f"/api/admin/coupons/{coupon.id}/toggle/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_toggle_unauthenticated_rejected(self):
        """Unauthenticated request is rejected (401 or 403)."""
        coupon = Coupon.objects.create(code="ANON_TOGGLE", discount_title="ทดสอบไม่ล็อกอิน", is_active=True)
        res = self.client.post(f"/api/admin/coupons/{coupon.id}/toggle/")
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_inactive_coupon_ineligible_for_booking(self):
        """Inactive coupon is immediately ineligible in is_eligible_for."""
        coupon = Coupon.objects.create(
            code="INACTIVE_CP",
            discount_title="คูปองปิดใช้งาน",
            discount_percent=20,
            is_active=False,
        )
        ok, msg = coupon.is_eligible_for(self.room_meeting, Decimal("1000.00"))
        self.assertFalse(ok)
        self.assertIn("ปิดใช้งานแล้ว", msg)

    def test_inactive_coupon_cannot_be_claimed(self):
        """User cannot claim an inactive coupon via claim_coupon_api."""
        coupon = Coupon.objects.create(
            code="CLAIM_INACTIVE",
            discount_title="รับไม่ได้",
            discount_percent=20,
            is_active=False,
        )
        self.client.force_authenticate(user=self.regular_user)
        res = self.client.post("/api/coupons/claim/", {"coupon_id": coupon.id}, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class CouponExpirationTimestampAdversarialTests(CouponStressAdversarialBaseTestCase):
    """Stress tests for expiration timestamps, past/future boundaries, and claiming."""

    def test_past_expiration_is_ineligible_for_booking(self):
        """Coupon with expires_at in the past is ineligible."""
        coupon = Coupon.objects.create(
            code="PAST_EXP",
            discount_title="หมดอายุแล้ว",
            discount_percent=10,
            expires_at=timezone.now() - timedelta(minutes=1),
            is_active=True,
        )
        ok, msg = coupon.is_eligible_for(self.room_meeting, Decimal("1000.00"))
        self.assertFalse(ok)
        self.assertIn("หมดอายุแล้ว", msg)

    def test_future_expiration_is_eligible_for_booking(self):
        """Coupon with expires_at in future is eligible."""
        coupon = Coupon.objects.create(
            code="FUTURE_EXP",
            discount_title="ยังไม่หมดอายุ",
            discount_percent=10,
            expires_at=timezone.now() + timedelta(days=7),
            is_active=True,
        )
        ok, _ = coupon.is_eligible_for(self.room_meeting, Decimal("1000.00"))
        self.assertTrue(ok)

    def test_none_expiration_is_eligible_indefinitely(self):
        """Coupon with expires_at=None has no expiration and is always eligible."""
        coupon = Coupon.objects.create(
            code="NO_EXP",
            discount_title="ไม่มีวันหมดอายุ",
            discount_percent=10,
            expires_at=None,
            is_active=True,
        )
        ok, _ = coupon.is_eligible_for(self.room_meeting, Decimal("1000.00"))
        self.assertTrue(ok)

    def test_admin_create_coupon_with_valid_iso_expires_at(self):
        """Admin can create coupon with ISO 8601 timestamp."""
        exp_time = timezone.now() + timedelta(days=15)
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "ISO_EXP",
            "discount_title": "มีวันหมดอายุ",
            "sub_title": "สิทธิ์พิเศษ",
            "discount_percent": 15,
            "expires_at": exp_time.isoformat(),
            "applicable_category": "all",
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(res.data["expires_at"])

    def test_admin_create_coupon_with_malformed_expires_at_rejected(self):
        """Admin creating coupon with invalid date format string is rejected."""
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "BAD_DATE",
            "discount_title": "วันที่ผิด",
            "discount_percent": 10,
            "expires_at": "invalid-date-string-not-iso",
            "applicable_category": "all",
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expires_at", res.data)


class CouponDuplicateCodeAdversarialTests(CouponStressAdversarialBaseTestCase):
    """Stress tests for duplicate codes, case insensitivity, trimming, and self-update."""

    def test_create_exact_duplicate_code_rejected(self):
        """Creating a coupon with an existing code is rejected with 400 Bad Request."""
        Coupon.objects.create(code="DUPLICATE1", discount_title="คูปองเดิม", is_active=True)
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "DUPLICATE1",
            "discount_title": "คูปองซ้ำ",
            "discount_percent": 20,
            "applicable_category": "all",
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", res.data)

    def test_create_case_insensitive_duplicate_code_rejected(self):
        """Creating 'duplicate1' when 'DUPLICATE1' exists is strictly rejected."""
        Coupon.objects.create(code="CASECODE", discount_title="คูปองตัวใหญ่", is_active=True)
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "casecode",
            "discount_title": "คูปองตัวเล็ก",
            "discount_percent": 15,
            "applicable_category": "all",
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", res.data)

    def test_create_duplicate_code_with_whitespace_rejected(self):
        """Creating '  SPACECODE  ' when 'SPACECODE' exists is rejected."""
        Coupon.objects.create(code="SPACECODE", discount_title="คูปองเดิม", is_active=True)
        self.client.force_authenticate(user=self.admin)
        payload = {
            "code": "  spacecode  ",
            "discount_title": "คูปองมีช่องว่าง",
            "discount_percent": 10,
            "applicable_category": "all",
        }
        res = self.client.post("/api/admin/coupons/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", res.data)

    def test_patch_coupon_with_its_own_code_allowed(self):
        """Updating a coupon while preserving its own code is permitted."""
        coupon = Coupon.objects.create(code="SELFUPDATE", discount_title="ก่อนแก้", discount_percent=10, is_active=True)
        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(
            f"/api/admin/coupons/{coupon.id}/",
            {"code": "SELFUPDATE", "discount_title": "หลังแก้"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["discount_title"], "หลังแก้")

    def test_patch_coupon_with_different_existing_code_rejected(self):
        """Updating coupon A to use coupon B's code is strictly rejected."""
        c1 = Coupon.objects.create(code="COUPONA", discount_title="คูปอง A", is_active=True)
        c2 = Coupon.objects.create(code="COUPONB", discount_title="คูปอง B", is_active=True)
        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(
            f"/api/admin/coupons/{c2.id}/",
            {"code": "coupona"},  # Try taking c1's code (in lowercase)
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", res.data)

    def test_create_coupon_empty_or_whitespace_code_rejected(self):
        """Creating a coupon with empty or whitespace-only code is rejected."""
        self.client.force_authenticate(user=self.admin)
        for bad_code in ["", "   ", "\t\n"]:
            res = self.client.post(
                "/api/admin/coupons/",
                {"code": bad_code, "discount_title": "โค้ดว่าง", "discount_percent": 10, "applicable_category": "all"},
                format="json",
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("code", res.data)


class CouponClaimAnalyticsAdversarialTests(CouponStressAdversarialBaseTestCase):
    """Stress tests for real-time coupon claim analytics, redemption tracking, and isolation."""

    def test_claims_view_structure_and_metrics(self):
        """Claim analytics endpoint returns total claims, used count, and claimant details."""
        coupon = Coupon.objects.create(
            code="ANALYTICS1",
            discount_title="คูปองวิเคราะห์",
            discount_percent=25,
            is_active=True,
        )
        # Create 3 claimants: 2 used, 1 unused
        u1 = CustomUser.objects.create_user(username="claim_u1", email="u1@test.local", password="P1!")
        u2 = CustomUser.objects.create_user(username="claim_u2", email="u2@test.local", password="P2!")
        u3 = CustomUser.objects.create_user(username="claim_u3", email="u3@test.local", password="P3!")

        UserCoupon.objects.create(user=u1, coupon=coupon, is_used=True, used_at=timezone.now())
        UserCoupon.objects.create(user=u2, coupon=coupon, is_used=True, used_at=timezone.now())
        UserCoupon.objects.create(user=u3, coupon=coupon, is_used=False)

        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f"/api/admin/coupons/{coupon.id}/claims/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["coupon_id"], coupon.id)
        self.assertEqual(res.data["coupon_code"], "ANALYTICS1")
        self.assertEqual(res.data["claims_count"], 3)
        self.assertEqual(res.data["used_count"], 2)
        claims = res.data["claims"]
        self.assertEqual(len(claims), 3)

        # Verify claim record properties
        u1_rec = next(c for c in claims if c["username"] == "claim_u1")
        self.assertTrue(u1_rec["is_used"])
        self.assertIsNotNone(u1_rec["used_at"])
        self.assertIn("used_at_display", u1_rec)

        u3_rec = next(c for c in claims if c["username"] == "claim_u3")
        self.assertFalse(u3_rec["is_used"])
        self.assertIsNone(u3_rec["used_at"])

    def test_claims_view_with_zero_claims(self):
        """Claim analytics returns empty list and 0 counts when no users have claimed."""
        coupon = Coupon.objects.create(code="NOCLAIMS", discount_title="ยังไม่มีคนกดรับ", is_active=True)
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f"/api/admin/coupons/{coupon.id}/claims/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["claims_count"], 0)
        self.assertEqual(res.data["used_count"], 0)
        self.assertEqual(res.data["claims"], [])

    def test_claims_view_filters_strictly_to_target_coupon(self):
        """Claim analytics for Coupon A never includes claimants of Coupon B."""
        cA = Coupon.objects.create(code="TARGET_A", discount_title="คูปอง A", is_active=True)
        cB = Coupon.objects.create(code="TARGET_B", discount_title="คูปอง B", is_active=True)

        uA = CustomUser.objects.create_user(username="user_only_a", email="ua@test.local", password="P!")
        uB = CustomUser.objects.create_user(username="user_only_b", email="ub@test.local", password="P!")

        UserCoupon.objects.create(user=uA, coupon=cA)
        UserCoupon.objects.create(user=uB, coupon=cB)

        self.client.force_authenticate(user=self.admin)
        resA = self.client.get(f"/api/admin/coupons/{cA.id}/claims/")
        self.assertEqual(resA.status_code, status.HTTP_200_OK)
        self.assertEqual(resA.data["claims_count"], 1)
        self.assertEqual(resA.data["claims"][0]["username"], "user_only_a")

    def test_claims_view_404_for_nonexistent_coupon(self):
        """Claim analytics returns 404 for non-existent coupon ID."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/admin/coupons/888888/claims/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_claims_view_forbidden_for_regular_user(self):
        """Regular user cannot access coupon claim analytics (403 Forbidden)."""
        coupon = Coupon.objects.create(code="RBAC_CLAIMS", discount_title="ทดสอบ", is_active=True)
        self.client.force_authenticate(user=self.regular_user)
        res = self.client.get(f"/api/admin/coupons/{coupon.id}/claims/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class CouponListFilteringAndSecurityAdversarialTests(CouponStressAdversarialBaseTestCase):
    """Stress tests for list search query injection safety, ordering whitelist, and filters."""

    def test_search_query_injection_safety(self):
        """Search query with SQL injection characters executes safely without 500 error."""
        Coupon.objects.create(code="SQLSAFE", discount_title="ค้นหาปลอดภัย", is_active=True)
        self.client.force_authenticate(user=self.admin)
        malicious_inputs = [
            "' OR '1'='1",
            "'; DROP TABLE reservations_coupon; --",
            "\" OR \"\"=\"",
            "%admin%",
            "\\x00",
        ]
        for payload in malicious_inputs:
            res = self.client.get(f"/api/admin/coupons/?search={payload}")
            self.assertEqual(
                res.status_code,
                status.HTTP_200_OK,
                f"Search query '{payload}' triggered unexpected status {res.status_code}",
            )

    def test_ordering_parameter_whitelist_safety(self):
        """Ordering by unauthorized field gracefully falls back to default ordering without 500."""
        Coupon.objects.create(code="ORD1", discount_title="เรียง 1", is_active=True)
        self.client.force_authenticate(user=self.admin)
        bad_orderings = ["password", "user__email", "unknown_field", "-secret", "1; DROP TABLE"]
        for bad_ord in bad_orderings:
            res = self.client.get(f"/api/admin/coupons/?ordering={bad_ord}")
            self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_by_is_active(self):
        """Filter ?is_active=true and ?is_active=false strictly isolates coupons."""
        Coupon.objects.create(code="ACT1", discount_title="Active", is_active=True)
        Coupon.objects.create(code="INACT1", discount_title="Inactive", is_active=False)

        self.client.force_authenticate(user=self.admin)
        res_act = self.client.get("/api/admin/coupons/?is_active=true")
        self.assertEqual(res_act.status_code, status.HTTP_200_OK)
        results_act = res_act.data.get("results", res_act.data)
        self.assertTrue(all(c["is_active"] is True for c in results_act))

        res_inact = self.client.get("/api/admin/coupons/?is_active=false")
        self.assertEqual(res_inact.status_code, status.HTTP_200_OK)
        results_inact = res_inact.data.get("results", res_inact.data)
        self.assertTrue(all(c["is_active"] is False for c in results_inact))

    def test_filter_by_category(self):
        """Filter ?category=villa returns only coupons applicable to villa (or all)."""
        Coupon.objects.create(code="VILLA_CP", discount_title="Villa", applicable_category="villa", is_active=True)
        Coupon.objects.create(code="THEAT_CP", discount_title="Theater", applicable_category="theater", is_active=True)

        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/admin/coupons/?category=villa")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data.get("results", res.data)
        codes = [c["code"] for c in results]
        self.assertIn("VILLA_CP", codes)
        self.assertNotIn("THEAT_CP", codes)

    def test_regular_user_cannot_access_coupon_admin_list(self):
        """Regular user without admin or staff role is denied from listing coupons (403 Forbidden)."""
        self.client.force_authenticate(user=self.regular_user)
        res = self.client.get("/api/admin/coupons/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
