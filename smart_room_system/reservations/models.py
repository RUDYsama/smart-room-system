from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'ผู้ดูแลระบบ (Admin)'),
        ('staff', 'เจ้าหน้าที่อาคาร (Staff)'),
        ('user', 'ผู้ใช้ทั่วไป (User)'),
    ]
    MEMBERSHIP_TIERS = [
        ('standard', 'สมาชิกทั่วไป'),
        ('silver', 'สมาชิก Silver'),
        ('gold', 'สมาชิก Gold'),
        ('vip', 'สมาชิก Smart VIP'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    membership_tier = models.CharField(max_length=30, choices=MEMBERSHIP_TIERS, default='vip', verbose_name="ระดับสมาชิก")
    loyalty_points = models.IntegerField(default=150, verbose_name="คะแนนสะสม")
    phone_number = models.CharField(max_length=20, blank=True, default='')
    department = models.CharField(max_length=100, blank=True, default='')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="รูปโปรไฟล์")
    is_verified = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class EmailOTP(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='otps')
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} - {self.otp_code}"

TAG_TO_CATEGORY = {
    'ห้องพัก': 'room',
    'บ้านพัก': 'villa',
    'จัดกิจกรรม': 'event',
    'สถานที่จัดกิจกรรม': 'event',
    'โรงละคร': 'theater',
    'สถานที่ทำงาน': 'work',
}

class Room(models.Model):
    ROOM_TYPES = [
        ('meeting', 'ห้องประชุม'),
        ('classroom', 'ห้องเรียนบรรยาย'),
        ('auditorium', 'หอประชุมใหญ่'),
        ('lab', 'ห้องปฏิบัติการคอมพิวเตอร์'),
    ]
    name = models.CharField(max_length=100)
    room_number = models.CharField(max_length=50, unique=True)
    building = models.CharField(max_length=100)
    floor = models.IntegerField(default=1)
    capacity = models.IntegerField(default=10)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=500.00, verbose_name="ราคาต่อหน่วย (บาท)")
    PRICE_UNITS = [
        ('hour', 'ชั่วโมง'),
        ('day', 'วัน'),
    ]
    price_unit = models.CharField(max_length=10, choices=PRICE_UNITS, default='hour', verbose_name="หน่วยคิดราคา")
    image = models.ImageField(upload_to='rooms/', blank=True, null=True, verbose_name="รูปภาพสถานที่")
    room_type = models.CharField(max_length=30, choices=ROOM_TYPES, default='meeting')
    tags = models.CharField(
        max_length=200, 
        blank=True, 
        default='', 
        help_text="แท็กหมวดหมู่คั่นด้วยจุลภาค สูงสุด 3 แท็ก (เช่น สถานที่ทำงาน, จัดกิจกรรม)"
    )
    amenities = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.tags:
            tag_items = [t.strip() for t in self.tags.split(',') if t.strip()]
            if len(tag_items) > 3:
                raise ValidationError("1 สถานที่สามารถมีแท็กได้สูงสุด 3 อันเท่านั้น")

    @property
    def is_daily(self):
        return self.price_unit == 'day'

    @property
    def price_unit_display(self):
        return '/ วัน' if self.price_unit == 'day' else '/ ชม.'

    @property
    def price_unit_label(self):
        return 'วัน' if self.price_unit == 'day' else 'ชม.'

    @property
    def tag_list(self):
        """Returns a list of up to 3 individual tags for badge pills directly from database."""
        if self.tags:
            return [t.strip() for t in self.tags.split(',') if t.strip()][:3]
        return [self.get_room_type_display()]

    @property
    def category_classes(self):
        """Returns space-separated category filter codes (e.g. 'work event')."""
        cats = []
        for tag in self.tag_list:
            code = TAG_TO_CATEGORY.get(tag)
            if code and code not in cats:
                cats.append(code)
        return " ".join(cats) if cats else "all"

    @property
    def get_images_list(self):
        """Returns a list of image URLs strictly belonging to THIS room: main image followed by all RoomImage gallery images."""
        urls = []
        if self.image:
            urls.append(self.image.url)
        for gi in self.gallery_images.all().order_by('order', 'id'):
            if gi.image:
                urls.append(gi.image.url)
        if not urls:
            urls.append('/static/images/rooms/vacation_villa.png')
        return urls

    def __str__(self):
        return f"{self.room_number} - {self.name}"

class RoomImage(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='gallery_images', verbose_name="สถานที่")
    image = models.ImageField(upload_to='rooms/gallery/', verbose_name="รูปภาพประกอบ")
    caption = models.CharField(max_length=150, blank=True, default='', verbose_name="คำบรรยายภาพ")
    order = models.IntegerField(default=0, verbose_name="ลำดับ")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "รูปภาพเพิ่มเติมของสถานที่"
        verbose_name_plural = "รูปภาพเพิ่มเติมทั้งหมด"

    def __str__(self):
        return f"{self.room.room_number} - Image #{self.id}"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'รอการพิจารณา'),
        ('APPROVED', 'อนุมัติแล้ว'),
        ('REJECTED', 'ไม่อนุมัติ'),
        ('CANCELLED', 'ยกเลิกแล้ว'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('PAID', 'ชำระเงินแล้ว'),
        ('PENDING', 'รอชำระเงิน'),
        ('REFUNDED', 'คืนเงินแล้ว'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bookings')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='bookings')
    title = models.CharField(max_length=150)
    purpose = models.TextField(blank=True, default='')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    stay_days = models.IntegerField(default=1, verbose_name="จำนวนวันเข้าพัก")
    stay_nights = models.IntegerField(default=1, verbose_name="จำนวนคืนเข้าพัก")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    attendees_count = models.IntegerField(default=1)
    rejection_reason = models.TextField(blank=True, default='')
    access_pin = models.CharField(max_length=6, blank=True, default='')
    coupon_code = models.CharField(max_length=50, blank=True, default='', verbose_name="โค้ดคูปองที่ใช้")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ยอดชำระสุทธิ (บาท)")
    payment_card = models.ForeignKey('PaymentCard', on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings', verbose_name="บัตรชำระเงินที่ใช้")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PAID', verbose_name="สถานะการชำระเงิน")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("เวลาสิ้นสุดต้องอยู่หลังเวลาเริ่มต้นเสมอ")

    def __str__(self):
        return f"{self.title} [{self.room.room_number}] ({self.status})"

class BookingEquipment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='equipments')
    equipment_name = models.CharField(max_length=100)
    quantity = models.IntegerField(default=1)
    condition = models.CharField(max_length=100, blank=True, default='สมบูรณ์')

    def __str__(self):
        return f"{self.equipment_name} (x{self.quantity}) - Booking #{self.booking_id}"


class Coupon(models.Model):
    ICON_CHOICES = [
        ('star', 'ดาว / สมาชิกใหม่'),
        ('bed', 'เตียง / ห้องพัก'),
        ('villa', 'บ้านพัก'),
        ('event', 'โถงกิจกรรม'),
        ('theater', 'โรงละคร'),
        ('work', 'สถานที่ทำงาน'),
        ('cafe', 'คาเฟ่ & เลานจ์'),
        ('users', 'การประชุมกลุ่ม'),
        ('clock', 'เหมาเต็มวัน'),
        ('calendar', 'สุดสัปดาห์'),
    ]
    code = models.CharField(max_length=50, unique=True, verbose_name="รหัสคูปอง")
    discount_title = models.CharField(max_length=100, verbose_name="ข้อความส่วนลด") # e.g. "ส่วนลด 20%"
    sub_title = models.CharField(max_length=100, verbose_name="สิทธิ์หรือประเภทสถานที่") # e.g. "สิทธิ์สมาชิกใหม่"
    info_tooltip = models.CharField(max_length=255, blank=True, default='', verbose_name="คำอธิบายเงื่อนไข")
    icon_type = models.CharField(max_length=30, choices=ICON_CHOICES, default='star', verbose_name="ไอคอนตั๋ว")
    button_text = models.CharField(max_length=50, default='รับสิทธิ์', verbose_name="ข้อความบนปุ่ม")
    discount_percent = models.IntegerField(default=10, verbose_name="เปอร์เซ็นต์ส่วนลด (%)")
    min_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ยอดจองขั้นต่ำ (บาท)")
    applicable_category = models.CharField(
        max_length=100, 
        default='all', 
        verbose_name="หมวดหมู่สถานที่ที่ใช้ได้",
        help_text="รหัสหมวดหมู่ เช่น all, room, villa, event, theater, work (หรือคั่นด้วยจุลภาค)"
    )
    max_discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="ส่วนลดสูงสุด (บาท - เว้นว่างถ้าไม่จำกัด)"
    )
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="วันหมดอายุคูปอง")
    terms = models.TextField(blank=True, default='', verbose_name="ข้อกำหนดและเงื่อนไข (ข้อละบรรทัด)")
    order = models.IntegerField(default=0, verbose_name="ลำดับการแสดงผล")
    is_active = models.BooleanField(default=True, verbose_name="เปิดใช้งาน")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "คูปองและสิทธิ์พิเศษ"
        verbose_name_plural = "คูปองและสิทธิ์พิเศษทั้งหมด"
        ordering = ['order', 'id']

    @property
    def applicable_category_display(self):
        if not self.applicable_category or self.applicable_category.strip().lower() == 'all':
            return 'ทุกหมวดหมู่'
        names = {
            'room': 'ห้องพัก',
            'villa': 'บ้านพัก',
            'event': 'จัดกิจกรรม',
            'theater': 'โรงละคร',
            'work': 'สถานที่ทำงาน'
        }
        cats = [names.get(c.strip().lower(), c.strip()) for c in self.applicable_category.split(',') if c.strip()]
        return ', '.join(cats)

    def is_eligible_for(self, room, subtotal):
        """Checks if this coupon can be applied to the given room and subtotal amount."""
        from django.utils import timezone
        from decimal import Decimal
        if not self.is_active:
            return False, "คูปองนี้ปิดใช้งานแล้ว"
        if self.expires_at and timezone.now() > self.expires_at:
            return False, "คูปองนี้หมดอายุแล้ว"
        if Decimal(str(subtotal)) < Decimal(str(self.min_spend)):
            return False, f"ยอดจองต้องไม่น้อยกว่า ฿{self.min_spend:,.0f} (ปัจจุบัน ฿{subtotal:,.0f})"
        
        # Check category match
        if self.applicable_category and self.applicable_category.strip().lower() != 'all':
            allowed_cats = [c.strip().lower() for c in self.applicable_category.split(',') if c.strip()]
            room_cats = [c.strip().lower() for c in getattr(room, 'category_classes', '').split() if c.strip()]
            if not any(cat in allowed_cats for cat in room_cats):
                return False, f"คูปองนี้ใช้ได้เฉพาะหมวด {self.applicable_category_display} เท่านั้น"
        return True, ""

    def calculate_discount(self, subtotal):
        """Calculates discount amount enforcing max_discount_amount cap."""
        from decimal import Decimal
        sub = Decimal(str(subtotal))
        discount = (sub * Decimal(str(self.discount_percent))) / Decimal('100.0')
        if self.max_discount_amount is not None and self.max_discount_amount > 0:
            discount = min(discount, Decimal(str(self.max_discount_amount)))
        return min(discount, sub)

    def __str__(self):
        return f"[{self.code}] {self.discount_title} - {self.sub_title}"


class UserCoupon(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='claimed_coupons', verbose_name="ผู้ใช้")
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='user_claims', verbose_name="คูปอง")
    claimed_at = models.DateTimeField(auto_now_add=True, verbose_name="วันที่กดรับสิทธิ์")
    is_used = models.BooleanField(default=False, verbose_name="ใช้งานแล้วหรือไม่")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="วันที่ใช้งาน")

    class Meta:
        verbose_name = "คูปองของผู้ใช้"
        verbose_name_plural = "คูปองของผู้ใช้ทั้งหมด"
        unique_together = ('user', 'coupon')
        ordering = ['-claimed_at']

    def __str__(self):
        status_str = "ใช้งานแล้ว" if self.is_used else "พร้อมใช้งาน"
        return f"{self.user.username} - [{self.coupon.code}] ({status_str})"


class PaymentCard(models.Model):
    CARD_BRANDS = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('jcb', 'JCB'),
        ('amex', 'American Express'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payment_cards', verbose_name="ผู้ใช้")
    card_brand = models.CharField(max_length=20, choices=CARD_BRANDS, default='visa', verbose_name="ประเภทบัตร")
    cardholder_name = models.CharField(max_length=150, verbose_name="ชื่อบนบัตร")
    last_four = models.CharField(max_length=4, verbose_name="เลข 4 ตัวท้าย")
    exp_month = models.CharField(max_length=2, verbose_name="เดือนหมดอายุ")
    exp_year = models.CharField(max_length=2, verbose_name="ปีหมดอายุ (YY)")
    is_default = models.BooleanField(default=False, verbose_name="เป็นช่องทางหลัก")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "บัตรชำระเงิน"
        verbose_name_plural = "บัตรชำระเงินทั้งหมด"
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.get_card_brand_display()} (•••• {self.last_four})"


class PromotionBanner(models.Model):
    BANNER_TYPE_CHOICES = [
        ('main_wide', 'แบนเนอร์หลัก (กว้าง)'),
        ('side_compact', 'แบนเนอร์เสริม (กะทัดรัด)'),
    ]
    title = models.CharField(max_length=150, verbose_name="หัวข้อโปรโมชัน")
    badge_text = models.CharField(max_length=50, blank=True, default='โปรโมชันพิเศษ', verbose_name="ป้ายกำกับโปรโมชัน")
    image = models.ImageField(upload_to='promotions/', verbose_name="รูปภาพโปรโมชัน")
    banner_type = models.CharField(
        max_length=20, 
        choices=BANNER_TYPE_CHOICES, 
        default='main_wide', 
        verbose_name="ตำแหน่งแบนเนอร์"
    )
    coupon = models.ForeignKey(
        Coupon, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='banners', 
        verbose_name="คูปองหลักประจำแคมเปญ"
    )
    secondary_coupon = models.ForeignKey(
        Coupon, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='secondary_banners', 
        verbose_name="คูปองเสริม (ถ้ามี เช่น ฟรีเครื่องดื่ม)"
    )
    description = models.TextField(blank=True, default='', verbose_name="รายละเอียดโปรโมชัน / แคมเปญ")
    terms = models.TextField(blank=True, default='', verbose_name="เงื่อนไขและข้อกำหนดเฉพาะแคมเปญ (ข้อละบรรทัด)")
    target_url = models.CharField(max_length=255, blank=True, default='', verbose_name="ลิงก์ปลายทาง (ถ้ามี)")
    order = models.IntegerField(default=0, verbose_name="ลำดับการแสดงผล")
    is_active = models.BooleanField(default=True, verbose_name="เปิดใช้งาน")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "แบนเนอร์โปรโมชัน"
        verbose_name_plural = "แบนเนอร์โปรโมชันทั้งหมด"
        ordering = ['order', 'id']

    def __str__(self):
        return f"[{self.get_banner_type_display()}] {self.title}"

