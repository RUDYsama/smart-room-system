from django.contrib import admin
from django.urls import path, re_path, include
from rest_framework import permissions
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from reservations.views import CustomLoginView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from django.conf import settings
from django.conf.urls.static import static

schema_view = get_schema_view(
    openapi.Info(
        title="Smart Room & Vacation Hotel Reservation API (Void Hunter)",
        default_version='v1',
        description=(
            "### Smart Room & Vacation Hotel Enterprise API Documentation\n\n"
            "ระบบ API สำหรับการบริหารจัดการห้องประชุม ห้องเรียน สถานที่จัดกิจกรรม และโรงแรมที่พักแบบครบวงจร\n"
            "รองรับการยืนยันตัวตนทั้ง Session Authentication และ JWT Bearer Token (อายุใช้งาน 7 วัน)\n\n"
            "#### หมวดหมู่ API ทั้งหมดในระบบ:\n"
            "1. **Authentication & Identity (`/api/auth/*`)**: ระบบล็อกอิน, สมัครสมาชิก, ตรวจสอบ OTP และข้อมูลส่วนตัว\n"
            "2. **Venues & Rooms (`/api/rooms/*`)**: ระบบสถานที่ ห้องประชุม ราคาต่อหน่วย/ชม./วัน และสถานะเปิด/ปิดซ่อม\n"
            "3. **Bookings & Approvals (`/api/bookings/*`)**: การจองห้อง อนุมัติคำขอ ออกรหัส PIN ประตู และยกเลิกคำขอ\n"
            "4. **Coupons & Vouchers (`/api/admin/coupons/*`)**: การบริหารจัดการคูปอง 14 พารามิเตอร์ และการตรวจสอบการรับสิทธิ์\n"
            "5. **Campaign Banners (`/api/admin/banners/*`)**: แบนเนอร์โปรโมชัน จัดลำดับภาพ และการแสดงป๊อปอัป Shopee-style\n"
            "6. **User Directory & RBAC (`/api/users/*` & `/api/admin/users/*`)**: การจัดการผู้ใช้งาน การเปลี่ยนสิทธิ์ (User/Staff/Admin) และกระเป๋าคูปอง\n"
            "7. **Profile & Payment Cards (`/api/profile/*`)**: การจัดการข้อมูลโปรไฟล์ บัตรชำระเงิน\n"
            "8. **Dashboard Analytics (`/api/dashboard/stats/`)**: สถิติภาพรวมระบบแบบ Real-time\n"
        ),
        contact=openapi.Contact(name="ITDS System Administration", email="admin@itds-organization.local"),
        license=openapi.License(name="Private Enterprise License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/auth/login/', CustomLoginView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include('reservations.urls')),
]

from django.views.static import serve

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
