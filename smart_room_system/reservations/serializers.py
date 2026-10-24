from rest_framework import serializers
from django.utils import timezone
from .models import (
    CustomUser,
    EmailOTP,
    Room,
    Booking,
    BookingEquipment,
    Coupon,
    UserCoupon,
    PromotionBanner,
    RoomImage,
)

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name', 'role', 'phone_number', 'department']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(password=password, is_verified=False, **validated_data)
        return user

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(required=True, min_length=6, max_length=6)

class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class ProfileSerializer(serializers.ModelSerializer):
    tier_display = serializers.CharField(source='get_membership_tier_display', read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'membership_tier', 'tier_display', 'loyalty_points', 'phone_number', 'department', 'avatar', 'is_verified', 'is_staff']
        read_only_fields = ['id', 'username', 'role', 'membership_tier', 'loyalty_points', 'is_staff', 'is_verified']

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name', 'role', 'membership_tier', 'loyalty_points', 'phone_number', 'department', 'avatar', 'is_active', 'is_verified', 'is_staff']

    def create(self, validated_data):
        password = validated_data.pop('password', 'DefaultUserPass123!')
        return CustomUser.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        if 'role' in validated_data:
            role = validated_data['role']
            if role in ['admin', 'staff']:
                instance.is_staff = True
            elif role == 'user' and not instance.is_superuser:
                instance.is_staff = False
        return super().update(instance, validated_data)

class RoomSerializer(serializers.ModelSerializer):
    images = serializers.ReadOnlyField(source='get_images_list')
    tag_list = serializers.ReadOnlyField()
    price_unit_display = serializers.ReadOnlyField()
    is_daily = serializers.ReadOnlyField()

    class Meta:
        model = Room
        fields = '__all__'

class RoomImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomImage
        fields = ['id', 'room', 'image', 'caption', 'order', 'created_at']
        read_only_fields = ['id', 'room', 'created_at']

class BookingEquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingEquipment
        fields = '__all__'

class BookingSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.username')
    user_email = serializers.ReadOnlyField(source='user.email')
    room_number = serializers.ReadOnlyField(source='room.room_number')
    room_name = serializers.ReadOnlyField(source='room.name')
    equipments = BookingEquipmentSerializer(many=True, read_only=True)
    payment_card_details = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'user', 'user_name', 'user_email', 'room', 'room_number', 'room_name',
            'title', 'purpose', 'start_time', 'end_time', 'stay_days', 'stay_nights', 'status', 'coupon_code',
            'total_price', 'payment_card', 'payment_card_details', 'payment_status',
            'attendees_count', 'rejection_reason', 'access_pin', 'equipments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'user_name', 'user_email', 'room_number', 'room_name', 'status', 'rejection_reason', 'access_pin', 'created_at', 'updated_at']

    def get_payment_card_details(self, obj):
        if obj.payment_card:
            return {
                'id': obj.payment_card.id,
                'brand': obj.payment_card.card_brand,
                'last_four': obj.payment_card.last_four,
                'cardholder_name': obj.payment_card.cardholder_name,
            }
        return None

    def validate(self, attrs):
        start_time = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end_time = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        room = attrs.get('room', getattr(self.instance, 'room', None))
        stay_days = attrs.get('stay_days', getattr(self.instance, 'stay_days', None))
        stay_nights = attrs.get('stay_nights', getattr(self.instance, 'stay_nights', None))
        attendees_count = attrs.get('attendees_count', getattr(self.instance, 'attendees_count', None))
        coupon_code = attrs.get('coupon_code', '')

        # Strictly enforce room active/maintenance mode
        if room and not room.is_active:
            raise serializers.ValidationError({
                "room": f"สถานที่ '{room.room_number}' อยู่ในสถานะปิดปรับปรุง (Maintenance) ไม่สามารถทำการจองได้"
            })

        # Strictly enforce room capacity limit
        if room and attendees_count is not None:
            if attendees_count > room.capacity:
                raise serializers.ValidationError({
                    "attendees_count": f"จำนวนผู้เข้าใช้งาน ({attendees_count} ท่าน) เกินความจุสูงสุดที่สถานที่รองรับได้ ({room.capacity} ท่าน)"
                })

        # Validate coupon claim ownership if coupon is supplied
        if coupon_code:
            code = coupon_code.strip()
            request = self.context.get('request')
            if request and request.user and request.user.is_authenticated:
                from .models import UserCoupon
                uc = UserCoupon.objects.filter(user=request.user, coupon__code__iexact=code, is_used=False).first()
                if not uc:
                    raise serializers.ValidationError({"coupon_code": f"คุณยังไม่ได้กดรับสิทธิ์คูปอง '{code}' หรือคูปองถูกใช้งานไปแล้ว"})

        if stay_days is not None:
            if stay_days < 1:
                raise serializers.ValidationError({"stay_days": "จำนวนวันเข้าพักต้องอย่างน้อย 1 วัน"})
            if stay_nights is not None:
                if stay_days == 1 and stay_nights not in [0, 1]:
                    raise serializers.ValidationError({"stay_nights": "สำหรับระยะเวลา 1 วัน สามารถเลือกได้ 0 หรือ 1 คืน เท่านั้น"})
                elif stay_days >= 2 and stay_nights not in [stay_days - 1, stay_days]:
                    raise serializers.ValidationError({"stay_nights": f"สำหรับระยะเวลา {stay_days} วัน สามารถเลือกพักได้ {stay_days - 1} คืน หรือ {stay_days} คืน เท่านั้น"})

        if start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError({"end_time": "เวลาสิ้นสุดต้องอยู่หลังเวลาเริ่มต้นเสมอ"})

            if room:
                conflicts = Booking.objects.filter(
                    room=room,
                    status__in=['PENDING', 'APPROVED'],
                    start_time__lt=end_time,
                    end_time__gt=start_time
                )
                if self.instance:
                    conflicts = conflicts.exclude(pk=self.instance.pk)

                if conflicts.exists():
                    conflict_list = [f"คำขอ #{b.id} ({b.title}): {b.start_time.strftime('%H:%M')} - {b.end_time.strftime('%H:%M')} น." for b in conflicts[:3]]
                    raise serializers.ValidationError({
                        "non_field_errors": [
                            f"Room conflict: ตรวจพบการชนเวลา: ห้อง '{room.room_number}' มีคำขอใช้งานในช่วงเวลาดังกล่าวแล้ว ({'; '.join(conflict_list)})"
                        ]
                    })
        return attrs

class BookingStatusActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class ApplicableCategoryField(serializers.Field):
    """
    Accepts string ('room,villa'), list (['villa', 'theater']), or empty values ('', []),
    and normalizes them into comma-separated lower-case category string.
    """
    def to_internal_value(self, data):
        if data is None or data == '' or data == []:
            return 'all'
        if isinstance(data, (list, tuple)):
            cats = [str(c).strip().lower() for c in data if str(c).strip()]
        elif isinstance(data, str):
            cats = [c.strip().lower() for c in data.split(',') if c.strip()]
        else:
            cats = [str(data).strip().lower()]

        if not cats:
            return 'all'

        valid_cats = {'all', 'room', 'villa', 'event', 'theater', 'work'}
        invalid = [c for c in cats if c not in valid_cats]
        if invalid:
            raise serializers.ValidationError(
                f"หมวดหมู่ไม่ถูกต้อง: {', '.join(invalid)}. หมวดหมู่ที่รองรับคือ: all, room, villa, event, theater, work"
            )

        if 'all' in cats and len(cats) > 1:
            cats = [c for c in cats if c != 'all']

        return ','.join(cats)

    def to_representation(self, value):
        return str(value) if value is not None else 'all'


class AdminCouponSerializer(serializers.ModelSerializer):
    """
    Serializer for full administrative management of Coupons (R1).
    Supports comprehensive validation, case-insensitive code uniqueness,
    multi-category parsing, and computed claim statistics.
    """
    applicable_category = ApplicableCategoryField(required=False, default='all')
    claims_count = serializers.SerializerMethodField()
    used_count = serializers.SerializerMethodField()
    applicable_category_display = serializers.ReadOnlyField()
    terms_list = serializers.SerializerMethodField()
    applicable_categories = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            'id',
            'code',
            'discount_title',
            'sub_title',
            'info_tooltip',
            'icon_type',
            'button_text',
            'discount_percent',
            'min_spend',
            'applicable_category',
            'applicable_category_display',
            'applicable_categories',
            'max_discount_amount',
            'expires_at',
            'terms',
            'terms_list',
            'order',
            'is_active',
            'created_at',
            'claims_count',
            'used_count',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'claims_count',
            'used_count',
            'applicable_category_display',
            'terms_list',
            'applicable_categories',
        ]

    def get_claims_count(self, obj):
        if hasattr(obj, 'claims_count'):
            return obj.claims_count
        return obj.user_claims.count()

    def get_used_count(self, obj):
        if hasattr(obj, 'used_count'):
            return obj.used_count
        return obj.user_claims.filter(is_used=True).count()

    def get_terms_list(self, obj):
        if not obj.terms:
            return []
        return [t.strip() for t in obj.terms.split('\n') if t.strip()]

    def get_applicable_categories(self, obj):
        if not obj.applicable_category or obj.applicable_category.strip().lower() == 'all':
            return ['all']
        return [c.strip().lower() for c in obj.applicable_category.split(',') if c.strip()]

    def validate_code(self, value):
        val = str(value).strip().upper()
        if not val:
            raise serializers.ValidationError("รหัสคูปองต้องไม่เป็นค่าว่าง")
        qs = Coupon.objects.filter(code__iexact=val)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("รหัสคูปองนี้มีอยู่ในระบบแล้ว กรุณาใช้รหัสอื่น")
        return val

    def validate_discount_percent(self, value):
        if value < 1 or value > 100:
            raise serializers.ValidationError("เปอร์เซ็นต์ส่วนลดต้องอยู่ระหว่าง 1 ถึง 100%")
        return value

    def validate_min_spend(self, value):
        if value < 0:
            raise serializers.ValidationError("ยอดจองขั้นต่ำต้องไม่ติดลบ")
        return value

    def validate_max_discount_amount(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("ส่วนลดสูงสุดต้องไม่ติดลบ")
        return value


class AdminCouponClaimSerializer(serializers.ModelSerializer):
    """
    Serializes UserCoupon instances for the Coupon Claim Analytics inspector (R1).
    Displays user details, claim timestamps, and redemption status.
    """
    user_id = serializers.ReadOnlyField(source='user.id')
    username = serializers.ReadOnlyField(source='user.username')
    email = serializers.ReadOnlyField(source='user.email')
    full_name = serializers.SerializerMethodField()
    phone_number = serializers.ReadOnlyField(source='user.phone_number')
    department = serializers.ReadOnlyField(source='user.department')

    class Meta:
        model = UserCoupon
        fields = [
            'id',
            'user_id',
            'username',
            'email',
            'full_name',
            'phone_number',
            'department',
            'claimed_at',
            'is_used',
            'used_at',
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        full = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return full if full else obj.user.username


class AdminBannerLinkedCouponSerializer(serializers.ModelSerializer):
    """
    Compact coupon serializer used exclusively for nesting inside AdminBannerSerializer
    to power real-time Shopee-style preview modals (R2).
    """
    applicable_category_display = serializers.ReadOnlyField()
    terms_list = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            'id',
            'code',
            'discount_title',
            'sub_title',
            'discount_percent',
            'min_spend',
            'max_discount_amount',
            'applicable_category',
            'applicable_category_display',
            'icon_type',
            'button_text',
            'expires_at',
            'terms',
            'terms_list',
        ]

    def get_terms_list(self, obj):
        if not obj.terms:
            return []
        return [t.strip() for t in obj.terms.split('\n') if t.strip()]


class AdminBannerSerializer(serializers.ModelSerializer):
    """
    Serializer for Promotional Campaign Banners Console (R2).
    Features:
    - Supports primary key writes (coupon, secondary_coupon, coupon_id, secondary_coupon_id).
    - Enriches read representations with full nested coupon preview objects.
    - Handles multipart/form-data image upload on creation and preserves existing images on update.
    """
    image = serializers.ImageField(required=False, allow_null=True)
    coupon = serializers.PrimaryKeyRelatedField(
        queryset=Coupon.objects.all(),
        required=False,
        allow_null=True
    )
    secondary_coupon = serializers.PrimaryKeyRelatedField(
        queryset=Coupon.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = PromotionBanner
        fields = [
            'id',
            'title',
            'badge_text',
            'image',
            'banner_type',
            'coupon',
            'secondary_coupon',
            'description',
            'terms',
            'target_url',
            'order',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_internal_value(self, data):
        # Allow mutation on QueryDict or immutable mapping
        if hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)

        # Support coupon_id and secondary_coupon_id aliases from frontend forms
        if 'coupon_id' in data and 'coupon' not in data:
            data['coupon'] = data['coupon_id']
        if 'secondary_coupon_id' in data and 'secondary_coupon' not in data:
            data['secondary_coupon'] = data['secondary_coupon_id']

        # Sanitize HTML select empty string values
        for field in ['coupon', 'secondary_coupon']:
            if field in data and (data[field] == '' or data[field] == 'null' or data[field] is None):
                data[field] = None

        # Handle image field on update: if instance exists and image passed is a string URL or empty string,
        # pop it so DRF does not raise an invalid file type ValidationError.
        if self.instance is not None:
            if 'image' in data:
                img_val = data['image']
                if isinstance(img_val, str) or img_val is None:
                    data.pop('image')

        return super().to_internal_value(data)

    def validate(self, attrs):
        # When creating a new banner, image is strictly mandatory
        if self.instance is None and 'image' not in attrs:
            raise serializers.ValidationError({'image': 'กรุณาอัปโหลดรูปภาพโปรโมชัน'})
        return attrs

    def update(self, instance, validated_data):
        # Preserve existing image if no new file was submitted
        if 'image' not in validated_data:
            validated_data['image'] = instance.image
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Raw foreign key IDs for HTML <select> dropdown binding
        data['coupon_id'] = instance.coupon_id
        data['secondary_coupon_id'] = instance.secondary_coupon_id

        # Rich nested representations for live Shopee-style preview modal
        data['coupon'] = (
            AdminBannerLinkedCouponSerializer(instance.coupon).data 
            if instance.coupon else None
        )
        data['secondary_coupon'] = (
            AdminBannerLinkedCouponSerializer(instance.secondary_coupon).data 
            if instance.secondary_coupon else None
        )

        # Additional presentation helper fields
        data['image_url'] = instance.image.url if instance.image else ''
        data['banner_type_display'] = instance.get_banner_type_display()
        data['terms_list'] = [
            t.strip() for t in (instance.terms or '').split('\n') if t.strip()
        ]

        return data

