"""
Empirical Adversarial Stress Test Suite for Promotional Campaign Banners (R2)
and Shopee Live Preview Modal.
Author: Challenger 2 (Milestone 1)
"""

import json
import tempfile
import shutil
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from reservations.models import CustomUser, Coupon, PromotionBanner


TEMP_MEDIA_ROOT = tempfile.mkdtemp()


def make_dummy_gif(filename="test_promo.gif"):
    content = (
        b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff"
        b"\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
        b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
    )
    return SimpleUploadedFile(name=filename, content=content, content_type="image/gif")


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class BannerEmpiricalStressTests(TestCase):
    """Adversarial stress testing of R2 Promotional Banners and Shopee Modal Preview."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()

        # Actors
        self.admin = CustomUser.objects.create_superuser(
            username="admin_challenger",
            email="admin_chal@vh.local",
            password="AdminPass123!",
            role="admin",
            is_staff=True,
            is_verified=True,
        )
        self.staff = CustomUser.objects.create_user(
            username="staff_challenger",
            email="staff_chal@vh.local",
            password="StaffPass123!",
            role="staff",
            is_staff=True,
            is_verified=True,
        )
        self.user = CustomUser.objects.create_user(
            username="user_challenger",
            email="user_chal@vh.local",
            password="UserPass123!",
            role="user",
            is_staff=False,
            is_verified=True,
        )

        # Baseline active and inactive coupons
        self.coupon_primary = Coupon.objects.create(
            code="STRESS20",
            discount_title="ส่วนลดแคมเปญ 20%",
            sub_title="สิทธิ์พิเศษสำหรับแบนเนอร์",
            discount_percent=20,
            min_spend=Decimal("1500.00"),
            max_discount_amount=Decimal("500.00"),
            applicable_category="room,villa",
            expires_at=timezone.now() + timedelta(days=15),
            terms="1. ใช้ได้เฉพาะห้องพัก\n2. จองล่วงหน้า 1 วัน",
            is_active=True,
        )
        self.coupon_secondary = Coupon.objects.create(
            code="FREEBEV",
            discount_title="ฟรีเครื่องดื่มเวลคัมดริ๊งก์",
            sub_title="รับสิทธิ์ฟรีที่เลานจ์",
            discount_percent=100,
            min_spend=Decimal("0.00"),
            max_discount_amount=Decimal("200.00"),
            applicable_category="all",
            expires_at=timezone.now() + timedelta(days=30),
            terms="แสดงคูปองต่อพนักงานต้อนรับ",
            is_active=True,
        )
        self.coupon_inactive = Coupon.objects.create(
            code="INACTIVE50",
            discount_title="คูปองปิดใช้งาน 50%",
            sub_title="ไม่พร้อมใช้งาน",
            discount_percent=50,
            is_active=False,
        )

    # -------------------------------------------------------------------------
    # 1. RBAC & SECURITY ACCESS
    # -------------------------------------------------------------------------
    def test_sec_01_anonymous_access_blocked(self):
        """Anonymous callers must receive 401 Unauthorized across all banner management endpoints."""
        endpoints = [
            ("GET", "/api/admin/banners/"),
            ("POST", "/api/admin/banners/"),
            ("POST", "/api/admin/banners/reorder/"),
        ]
        for method, url in endpoints:
            if method == "GET":
                res = self.client.get(url)
            else:
                res = self.client.post(url, {})
            self.assertEqual(
                res.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Endpoint {method} {url} should reject anonymous user with 401"
            )

    def test_sec_02_regular_user_access_forbidden(self):
        """Regular users (role='user') must receive 403 Forbidden across all banner endpoints."""
        self.client.force_authenticate(user=self.user)
        endpoints = [
            ("GET", "/api/admin/banners/"),
            ("POST", "/api/admin/banners/"),
            ("POST", "/api/admin/banners/reorder/"),
        ]
        for method, url in endpoints:
            if method == "GET":
                res = self.client.get(url)
            else:
                res = self.client.post(url, {})
            self.assertEqual(
                res.status_code,
                status.HTTP_403_FORBIDDEN,
                f"Endpoint {method} {url} should reject regular user with 403"
            )

    def test_sec_03_staff_access_permitted(self):
        """Staff users (role='staff', is_staff=True) must be granted access."""
        self.client.force_authenticate(user=self.staff)
        res = self.client.get("/api/admin/banners/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    # -------------------------------------------------------------------------
    # 2. BANNER CREATION & MULTIPART UPLOAD
    # -------------------------------------------------------------------------
    def test_create_01_missing_image_rejected(self):
        """Creating banner without image must return 400 Bad Request with descriptive error."""
        self.client.force_authenticate(user=self.admin)
        payload = {
            "title": "No Image Banner",
            "banner_type": "main_wide",
        }
        res = self.client.post("/api/admin/banners/", payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", res.data)

    def test_create_02_non_image_file_rejected(self):
        """Uploading non-image binary (text file) as image must be rejected."""
        self.client.force_authenticate(user=self.admin)
        text_file = SimpleUploadedFile("script.sh", b"#!/bin/bash\necho hack", content_type="text/plain")
        payload = {
            "title": "Text File Banner",
            "banner_type": "main_wide",
            "image": text_file,
        }
        res = self.client.post("/api/admin/banners/", payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", res.data)

    def test_create_03_wide_and_compact_creation_with_all_fields(self):
        """Create wide and compact banners with dual coupons, Thai unicode, and terms."""
        self.client.force_authenticate(user=self.admin)

        # 1. Main Wide banner
        img_wide = make_dummy_gif("wide.gif")
        payload_wide = {
            "title": "มหกรรมพักผ่อนริมหาด 2026 (Grand Beachfront)",
            "badge_text": "LIMITED EDITION",
            "banner_type": "main_wide",
            "coupon_id": self.coupon_primary.id,
            "secondary_coupon_id": self.coupon_secondary.id,
            "description": "จองวิลล่าหรูริมทะเล รับส่วนลด 20% พร้อมเวลคัมดริ๊งก์ฟรีทุกยอดจอง",
            "terms": "1. เฉพาะการจองผ่านระบบออนไลน์\n2. จำกัด 1 สิทธิ์ต่อผู้ใช้",
            "target_url": "/rooms/?category=villa",
            "order": 1,
            "is_active": True,
            "image": img_wide,
        }
        res_w = self.client.post("/api/admin/banners/", payload_wide, format="multipart")
        self.assertEqual(res_w.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_w.data["banner_type"], "main_wide")
        self.assertEqual(res_w.data["coupon_id"], self.coupon_primary.id)
        self.assertEqual(res_w.data["secondary_coupon_id"], self.coupon_secondary.id)

        # 2. Side Compact banner
        img_compact = make_dummy_gif("compact.gif")
        payload_compact = {
            "title": "โปรโมชันช่วงบ่าย คาเฟ่ & เลานจ์",
            "badge_text": "AFTERNOON SPECIAL",
            "banner_type": "side_compact",
            "coupon": self.coupon_secondary.id,  # direct field name
            "description": "ผ่อนคลายกับเครื่องดื่มฟรีตลอดสัปดาห์",
            "order": 2,
            "is_active": True,
            "image": img_compact,
        }
        res_c = self.client.post("/api/admin/banners/", payload_compact, format="multipart")
        self.assertEqual(res_c.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_c.data["banner_type"], "side_compact")
        self.assertEqual(res_c.data["coupon_id"], self.coupon_secondary.id)
        self.assertIsNone(res_c.data["secondary_coupon_id"])

    # -------------------------------------------------------------------------
    # 3. LIST FILTERING, SEARCHING & GROUPING
    # -------------------------------------------------------------------------
    def test_filter_01_by_banner_type(self):
        """Query parameters ?banner_type=main_wide and ?banner_type=side_compact return segregated sets."""
        self.client.force_authenticate(user=self.admin)
        img = make_dummy_gif()
        b_wide = PromotionBanner.objects.create(title="W1", banner_type="main_wide", image=img, order=1)
        b_compact = PromotionBanner.objects.create(title="C1", banner_type="side_compact", image=img, order=2)

        # Filter wide
        res_w = self.client.get("/api/admin/banners/?banner_type=main_wide")
        self.assertEqual(res_w.status_code, status.HTTP_200_OK)
        banners_w = res_w.data.get("results", res_w.data) if isinstance(res_w.data, dict) else res_w.data
        ids_w = [b["id"] for b in banners_w]
        self.assertIn(b_wide.id, ids_w)
        self.assertNotIn(b_compact.id, ids_w)

        # Filter compact
        res_c = self.client.get("/api/admin/banners/?banner_type=side_compact")
        self.assertEqual(res_c.status_code, status.HTTP_200_OK)
        banners_c = res_c.data.get("results", res_c.data) if isinstance(res_c.data, dict) else res_c.data
        ids_c = [b["id"] for b in banners_c]
        self.assertIn(b_compact.id, ids_c)
        self.assertNotIn(b_wide.id, ids_c)

    def test_filter_02_by_active_status_and_search(self):
        """Query params ?is_active=true/false and ?q= accurately filter results."""
        self.client.force_authenticate(user=self.admin)
        img = make_dummy_gif()
        b_active = PromotionBanner.objects.create(title="Active Promo", badge_text="SUMMER", is_active=True, image=img)
        b_inactive = PromotionBanner.objects.create(title="Old Winter Deal", badge_text="WINTER", is_active=False, image=img)

        # is_active filter
        res_act = self.client.get("/api/admin/banners/?is_active=true")
        self.assertEqual(res_act.status_code, status.HTTP_200_OK)
        banners_act = res_act.data.get("results", res_act.data) if isinstance(res_act.data, dict) else res_act.data
        act_ids = [b["id"] for b in banners_act]
        self.assertIn(b_active.id, act_ids)
        self.assertNotIn(b_inactive.id, act_ids)

        # search query
        res_q = self.client.get("/api/admin/banners/?q=Winter")
        self.assertEqual(res_q.status_code, status.HTTP_200_OK)
        banners_q = res_q.data.get("results", res_q.data) if isinstance(res_q.data, dict) else res_q.data
        q_ids = [b["id"] for b in banners_q]
        self.assertIn(b_inactive.id, q_ids)
        self.assertNotIn(b_active.id, q_ids)

    # -------------------------------------------------------------------------
    # 4. UPDATE LIFECYCLE & IMAGE PRESERVATION
    # -------------------------------------------------------------------------
    def test_update_01_patch_without_image_preserves_existing_image(self):
        """Updating title, terms, or coupons via PATCH without re-uploading image preserves the original image."""
        self.client.force_authenticate(user=self.admin)
        img = make_dummy_gif("original.gif")
        banner = PromotionBanner.objects.create(
            title="Original Banner",
            banner_type="main_wide",
            image=img,
            coupon=self.coupon_primary,
            order=5,
            is_active=True,
        )
        original_img_name = banner.image.name

        # PATCH update title and description only
        res = self.client.patch(
            f"/api/admin/banners/{banner.id}/",
            {"title": "Patched Title", "description": "New description"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        banner.refresh_from_db()
        self.assertEqual(banner.title, "Patched Title")
        self.assertEqual(banner.description, "New description")
        self.assertEqual(banner.image.name, original_img_name)

    def test_update_02_patch_with_image_url_string_does_not_fail(self):
        """Sending the existing image_url string back in form update does NOT raise an invalid file error."""
        self.client.force_authenticate(user=self.admin)
        img = make_dummy_gif("banner_url_test.gif")
        banner = PromotionBanner.objects.create(
            title="URL Preserving Banner",
            banner_type="main_wide",
            image=img,
        )
        original_img_name = banner.image.name

        # Frontend forms commonly send back the image URL string
        payload = {
            "title": "Preserved After String URL",
            "image": banner.image.url,
        }
        res = self.client.patch(f"/api/admin/banners/{banner.id}/", payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        banner.refresh_from_db()
        self.assertEqual(banner.title, "Preserved After String URL")
        self.assertEqual(banner.image.name, original_img_name)

    def test_update_03_replace_image_with_new_file(self):
        """Uploading a new image file on update successfully replaces the previous image."""
        self.client.force_authenticate(user=self.admin)
        img1 = make_dummy_gif("img1.gif")
        banner = PromotionBanner.objects.create(
            title="Banner Before Replacement",
            banner_type="main_wide",
            image=img1,
        )
        old_name = banner.image.name

        # Send new image file
        img2 = make_dummy_gif("img2_replacement.gif")
        res = self.client.patch(
            f"/api/admin/banners/{banner.id}/",
            {"image": img2, "title": "Banner After Replacement"},
            format="multipart"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        banner.refresh_from_db()
        self.assertEqual(banner.title, "Banner After Replacement")
        self.assertNotEqual(banner.image.name, old_name)

    def test_update_04_unlink_coupon_by_setting_null(self):
        """Unlinking coupon by sending null or empty string leaves coupon field None without errors."""
        self.client.force_authenticate(user=self.admin)
        img = make_dummy_gif()
        banner = PromotionBanner.objects.create(
            title="Linked Banner",
            banner_type="main_wide",
            coupon=self.coupon_primary,
            secondary_coupon=self.coupon_secondary,
            image=img,
        )
        self.assertIsNotNone(banner.coupon)
        self.assertIsNotNone(banner.secondary_coupon)

        # Unlink secondary coupon
        payload = {"secondary_coupon_id": ""}
        res = self.client.patch(f"/api/admin/banners/{banner.id}/", payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        banner.refresh_from_db()
        self.assertEqual(banner.coupon, self.coupon_primary)
        self.assertIsNone(banner.secondary_coupon)

    def test_update_05_delete_linked_coupon_does_not_cascade_delete_banner(self):
        """When a Coupon is deleted from the DB, ForeignKey on_delete=SET_NULL preserves the banner."""
        img = make_dummy_gif()
        temp_coupon = Coupon.objects.create(code="TEMPDELETE", discount_title="ชั่วคราว", is_active=True)
        banner = PromotionBanner.objects.create(
            title="Resilient Banner",
            banner_type="main_wide",
            coupon=temp_coupon,
            image=img,
        )
        temp_coupon.delete()
        banner.refresh_from_db()
        self.assertIsNone(banner.coupon)
        self.assertEqual(banner.title, "Resilient Banner")

    # -------------------------------------------------------------------------
    # 5. REORDERING ENDPOINT ATOMICITY & FORMATS
    # -------------------------------------------------------------------------
    def test_reorder_01_banner_ids_list_format(self):
        """Reorder using {"banner_ids": [id3, id1, id2]} sets order=0, 1, 2 respectively."""
        self.client.force_authenticate(user=self.admin)
        img = make_dummy_gif()
        b1 = PromotionBanner.objects.create(title="B1", order=10, image=img)
        b2 = PromotionBanner.objects.create(title="B2", order=20, image=img)
        b3 = PromotionBanner.objects.create(title="B3", order=30, image=img)

        # Desired sequence: b3, then b1, then b2
        payload = {"banner_ids": [b3.id, b1.id, b2.id]}
        res = self.client.post("/api/admin/banners/reorder/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "success")
        self.assertEqual(res.data["updated_count"], 3)

        b1.refresh_from_db()
        b2.refresh_from_db()
        b3.refresh_from_db()
        self.assertEqual(b3.order, 0)
        self.assertEqual(b1.order, 1)
        self.assertEqual(b2.order, 2)

    def test_reorder_02_items_format(self):
        """Reorder using {"items": [{"id": X, "order": 100}, ...]} sets custom order values."""
        self.client.force_authenticate(user=self.admin)
        img = make_dummy_gif()
        b1 = PromotionBanner.objects.create(title="B1", order=0, image=img)
        b2 = PromotionBanner.objects.create(title="B2", order=1, image=img)

        payload = {
            "items": [
                {"id": b1.id, "order": 99},
                {"id": b2.id, "order": 5},
            ]
        }
        res = self.client.post("/api/admin/banners/reorder/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        b1.refresh_from_db()
        b2.refresh_from_db()
        self.assertEqual(b1.order, 99)
        self.assertEqual(b2.order, 5)

    def test_reorder_03_invalid_empty_payload_returns_400(self):
        """Reorder with empty or missing payload returns 400 Bad Request."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.post("/api/admin/banners/reorder/", {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", res.data)

    def test_reorder_04_nonexistent_ids_handled_gracefully(self):
        """Non-existent banner IDs in list do not crash atomic transaction."""
        self.client.force_authenticate(user=self.admin)
        img = make_dummy_gif()
        b1 = PromotionBanner.objects.create(title="B1", order=0, image=img)

        payload = {"banner_ids": [b1.id, 999999, 888888]}
        res = self.client.post("/api/admin/banners/reorder/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["updated_count"], 1)

    # -------------------------------------------------------------------------
    # 6. SHOPEE PREVIEW MODAL DATA INTEGRITY & ADVERSARIAL CASES
    # -------------------------------------------------------------------------
    def test_shopee_01_campaigns_json_structure_and_coupon_nesting(self):
        """Admin portal view provides valid campaigns_json with all required coupon preview attributes."""
        img = make_dummy_gif()
        banner = PromotionBanner.objects.create(
            title="Shopee Grand Campaign",
            badge_text="EXCLUSIVE",
            banner_type="main_wide",
            coupon=self.coupon_primary,
            secondary_coupon=self.coupon_secondary,
            description="คำอธิบายแบบยาวสำหรับทดสอบ",
            terms="ข้อ 1\nข้อ 2\nข้อ 3",
            image=img,
            order=1,
            is_active=True,
        )

        self.client.force_login(self.admin)
        res = self.client.get("/admin-panel/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("campaigns_json", res.context)

        data = json.loads(res.context["campaigns_json"])
        self.assertIn(str(banner.id), data)
        camp = data[str(banner.id)]

        self.assertEqual(camp["id"], banner.id)
        self.assertEqual(camp["title"], "Shopee Grand Campaign")
        self.assertEqual(camp["badge_text"], "EXCLUSIVE")
        self.assertEqual(len(camp["terms"]), 3)

        # Primary coupon nesting
        self.assertIsNotNone(camp["coupon"])
        self.assertEqual(camp["coupon"]["code"], "STRESS20")
        self.assertEqual(camp["coupon"]["discount_percent"], 20)
        self.assertEqual(camp["coupon"]["min_spend"], 1500.0)
        self.assertEqual(camp["coupon"]["max_discount_amount"], 500.0)
        self.assertEqual(len(camp["coupon"]["terms"]), 2)

        # Secondary coupon nesting
        self.assertIsNotNone(camp["secondary_coupon"])
        self.assertEqual(camp["secondary_coupon"]["code"], "FREEBEV")
        self.assertEqual(camp["secondary_coupon"]["discount_percent"], 100)

    def test_shopee_02_banner_with_no_linked_coupons(self):
        """When a banner has no coupons, campaigns_json holds null for coupons without breaking."""
        img = make_dummy_gif()
        banner = PromotionBanner.objects.create(
            title="Informational Banner Only",
            banner_type="main_wide",
            image=img,
        )

        self.client.force_login(self.admin)
        res = self.client.get("/admin-panel/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = json.loads(res.context["campaigns_json"])
        camp = data[str(banner.id)]
        self.assertIsNone(camp["coupon"])
        self.assertIsNone(camp["secondary_coupon"])

    def test_shopee_03_xss_special_characters_in_banner_and_coupon(self):
        """Banner with HTML/script characters is safely encoded in campaigns_json."""
        img = make_dummy_gif()
        xss_title = '<script>alert("XSS")</script> & Special "Quotes"'
        xss_terms = "Line 1 <img src=x onerror=alert(1)>\nLine 2 <b>Bold</b>"
        banner = PromotionBanner.objects.create(
            title=xss_title,
            banner_type="side_compact",
            terms=xss_terms,
            image=img,
        )

        self.client.force_login(self.admin)
        res = self.client.get("/admin-panel/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = json.loads(res.context["campaigns_json"])
        camp = data[str(banner.id)]
        self.assertEqual(camp["title"], xss_title)
        self.assertIn("<script>alert(\"XSS\")</script>", camp["title"])

    def test_shopee_04_admin_portal_context_wide_and_compact_segregation(self):
        """Admin portal view separates wide_banners and compact_banners in context."""
        img = make_dummy_gif()
        PromotionBanner.objects.create(title="Wide 1", banner_type="main_wide", image=img, order=1)
        PromotionBanner.objects.create(title="Wide 2", banner_type="main_wide", image=img, order=2)
        PromotionBanner.objects.create(title="Compact 1", banner_type="side_compact", image=img, order=3)

        self.client.force_login(self.admin)
        res = self.client.get("/admin-panel/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        wide_list = res.context["wide_banners"]
        compact_list = res.context["compact_banners"]
        all_banners = res.context["all_banners"]

        self.assertTrue(len(wide_list) >= 2)
        self.assertTrue(len(compact_list) >= 1)
        self.assertEqual(len(all_banners), len(wide_list) + len(compact_list))
        self.assertTrue(all(b.banner_type == "main_wide" for b in wide_list))
        self.assertTrue(all(b.banner_type == "side_compact" for b in compact_list))
