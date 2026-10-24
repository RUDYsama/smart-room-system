from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, EmailOTP, Room, RoomImage, Booking, BookingEquipment, Coupon, UserCoupon, PaymentCard, PromotionBanner

class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 2

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('ข้อมูลเพิ่มเติม', {'fields': ('role', 'phone_number', 'department', 'is_verified')}),
    )
    list_display = ('username', 'email', 'role', 'department', 'is_verified', 'is_staff', 'is_active')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_active')

class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'name', 'tags', 'room_type', 'building', 'floor', 'capacity', 'is_active')
    list_filter = ('room_type', 'building', 'is_active')
    search_fields = ('room_number', 'name', 'building', 'tags')
    inlines = [RoomImageInline]

class BookingEquipmentInline(admin.TabularInline):
    model = BookingEquipment
    extra = 1

class BookingAdmin(admin.ModelAdmin):
    list_display = ('title', 'room', 'user', 'coupon_code', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'room')
    search_fields = ('title', 'coupon_code', 'user__username', 'room__room_number', 'room__name')
    inlines = [BookingEquipmentInline]

class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'otp_code', 'created_at', 'expires_at', 'is_used')
    list_filter = ('is_used', 'created_at')

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(EmailOTP, EmailOTPAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(BookingEquipment)

class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_title', 'sub_title', 'applicable_category', 'discount_percent', 'min_spend', 'expires_at', 'order', 'is_active')
    list_filter = ('applicable_category', 'icon_type', 'is_active')
    search_fields = ('code', 'discount_title', 'sub_title', 'info_tooltip')
    list_editable = ('order', 'is_active')

admin.site.register(Coupon, CouponAdmin)

class UserCouponAdmin(admin.ModelAdmin):
    list_display = ('user', 'coupon', 'is_used', 'claimed_at', 'used_at')
    list_filter = ('is_used', 'claimed_at')
    search_fields = ('user__username', 'user__email', 'coupon__code', 'coupon__discount_title')

admin.site.register(UserCoupon, UserCouponAdmin)

class PaymentCardAdmin(admin.ModelAdmin):
    list_display = ('user', 'card_brand', 'cardholder_name', 'last_four', 'exp_month', 'exp_year', 'is_default')
    list_filter = ('card_brand', 'is_default')
    search_fields = ('user__username', 'cardholder_name', 'last_four')

admin.site.register(PaymentCard, PaymentCardAdmin)

class PromotionBannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'banner_type', 'coupon', 'secondary_coupon', 'badge_text', 'is_active', 'order', 'created_at')
    list_filter = ('banner_type', 'is_active')
    search_fields = ('title', 'badge_text', 'description', 'terms', 'target_url')
    autocomplete_fields = ('coupon', 'secondary_coupon')
    list_editable = ('is_active', 'order')

admin.site.register(PromotionBanner, PromotionBannerAdmin)
