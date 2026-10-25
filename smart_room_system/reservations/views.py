import os
import random
from decimal import Decimal
from datetime import datetime, time, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.core.mail import send_mail
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import CustomUser, EmailOTP, Room, Booking, BookingEquipment, Coupon, UserCoupon, PaymentCard, PromotionBanner, RoomImage
from .serializers import (
    RegisterSerializer,
    VerifyOTPSerializer,
    ResendOTPSerializer,
    ProfileSerializer,
    ChangePasswordSerializer,
    UserSerializer,
    RoomSerializer,
    RoomImageSerializer,
    BookingSerializer,
    BookingEquipmentSerializer,
    BookingStatusActionSerializer,
    AdminCouponSerializer,
    AdminCouponClaimSerializer,
    AdminBannerSerializer,
    AdminBannerLinkedCouponSerializer,
)
import threading
from .permissions import IsAdminRole, IsStaffOrAdminRole, IsOwnerOrAdminOrReadOnly

def _send_email_async(subject, message, recipient_list, html_message):
    import urllib.request, json, ssl
    # 1. Try sending via Vercel HTTPS SMTP Relay (uses Google App Password from Vercel where port 587 is unblocked)
    for recipient in recipient_list:
        delivered = False
        try:
            relay_url = "https://smart-room-system.vercel.app/api/send-otp"
            payload = json.dumps({
                "to": recipient,
                "subject": subject,
                "html": html_message,
                "text": message
            }).encode('utf-8')
            ctx = ssl.create_default_context()
            req = urllib.request.Request(
                relay_url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Relay-Secret": "smart-room-otp-relay-secret-2026",
                    "User-Agent": "SmartRoomBackend/1.0"
                }
            )
            with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
                if resp.status in (200, 201):
                    logger.info(f"Email delivered via Vercel SMTP relay to {recipient}")
                    delivered = True
        except Exception as e:
            logger.warning(f"Vercel relay delivery skipped or pending deploy: {e}")

        if not delivered:
            # 2. Fallback to direct Django SMTP (uses Google App Password directly)
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    html_message=html_message,
                    fail_silently=False
                )
                logger.info(f"Email delivered via direct Django SMTP to {recipient}")
            except Exception as e:
                logger.error(f"Direct Django SMTP delivery failed for {recipient}: {e}")

def send_pin_email(email, pin, username):
    subject = f"[VH - Vacations & Hotel] รหัสยืนยันการลงทะเบียน (OTP PIN): {pin}"
    message = f"สวัสดีคุณ {username}\n\nรหัสยืนยัน PIN 6 หลักของคุณคือ: {pin}\nรหัสนี้มีอายุการใช้งาน 10 นาที\n\nระบบบริหารจัดการและจองสถานที่และห้องพัก (VH - Vacations & Hotel)"
    html_message = f"""
    <div style="font-family: 'Sarabun', Arial, sans-serif; padding: 24px; border: 1px solid #cbd5e1; border-radius: 12px; max-width: 520px; margin: auto; background-color: #ffffff;">
        <h2 style="color: #1e3a8a; margin-top: 0; font-size: 22px;">ระบบบริหารจัดการและจองสถานที่และห้องพัก</h2>
        <p style="color: #64748b; font-size: 14px; margin-top: -6px;">VH - Vacations & Hotel Reservation System</p>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 16px 0;">
        <p style="font-size: 15px; color: #334155;">เรียน คุณ <strong>{username}</strong>,</p>
        <p style="font-size: 15px; color: #334155;">คุณได้ทำการลงทะเบียนเข้าใช้งานระบบบริหารจัดการและจองสถานที่และห้องพัก รหัสยืนยัน PIN 6 หลักสำหรับการยืนยันตัวตนและเปิดใช้งานบัญชีของคุณคือ:</p>
        <div style="background-color: #f8fafc; border: 2px dashed #3b82f6; border-radius: 8px; padding: 18px; text-align: center; margin: 20px 0;">
            <span style="font-size: 38px; font-weight: bold; letter-spacing: 8px; color: #1e3a8a;">{pin}</span>
        </div>
        <p style="color: #ef4444; font-size: 13px; margin-bottom: 0;">* รหัส PIN นี้มีอายุการใช้งาน 10 นาที และถือเป็นข้อมูลความปลอดภัยส่วนบุคคล ห้ามเปิดเผยแก่บุคคลอื่น</p>
    </div>
    """
    # Send email in a background daemon thread so HTTP requests respond in milliseconds without timing out
    t = threading.Thread(
        target=_send_email_async,
        args=(subject, message, [email], html_message),
        daemon=True
    )
    t.start()
    return True

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(operation_description="Register a new user and generate a 6-digit OTP PIN")
    def post(self, request, *args, **kwargs):
        username = request.data.get('username', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')

        # If user exists but has not completed OTP verification yet, allow re-triggering signup seamlessly
        unverified_user = None
        if username:
            unverified_user = CustomUser.objects.filter(username=username, is_verified=False).first()
        if not unverified_user and email:
            unverified_user = CustomUser.objects.filter(email=email, is_verified=False).first()

        if unverified_user:
            if password:
                unverified_user.set_password(password)
            if email:
                unverified_user.email = email
            phone = request.data.get('phone_number', '')
            if phone:
                unverified_user.phone_number = phone
            dept = request.data.get('department', '')
            if dept:
                unverified_user.department = dept
            unverified_user.save()
            user = unverified_user
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

        pin = f"{random.randint(100000, 999999)}"
        expires_at = timezone.now() + timedelta(minutes=10)
        EmailOTP.objects.create(
            user=user,
            email=user.email,
            otp_code=pin,
            expires_at=expires_at
        )

        email_sent = send_pin_email(user.email, pin, user.username)

        return Response({
            "message": "ลงทะเบียนสำเร็จ กรุณากรอกรหัส PIN 6 หลักที่ส่งไปยังอีเมลของคุณเพื่อเปิดใช้งานบัญชี",
            "email": user.email,
            "username": user.username,
            "requires_otp": True,
            "email_dispatched": email_sent
        }, status=status.HTTP_201_CREATED)

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Verify 6-digit OTP PIN and activate user account",
        request_body=VerifyOTPSerializer
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']

        otp_record = EmailOTP.objects.filter(
            email=email,
            otp_code=otp_code,
            is_used=False,
            expires_at__gte=timezone.now()
        ).order_by('-created_at').first()

        if not otp_record:
            return Response({
                "error": "รหัส PIN ไม่ถูกต้อง หรือหมดอายุการใช้งานแล้ว กรุณาตรวจสอบหรือขอรหัสใหม่"
            }, status=status.HTTP_400_BAD_REQUEST)

        otp_record.is_used = True
        otp_record.save()

        user = otp_record.user
        user.is_verified = True
        user.is_active = True
        user.save()

        # Start Django session & set 7-day expiry
        login(request, user)
        request.session.set_expiry(60 * 60 * 24 * 7)

        # Issue JWT tokens
        refresh = RefreshToken.for_user(user)

        is_admin = getattr(user, 'role', '') == 'admin' or user.is_superuser or user.is_staff
        redirect_url = '/admin-panel/' if is_admin else '/user/'

        return Response({
            "message": "ยืนยันรหัส PIN สำเร็จ บัญชีของคุณได้รับการเปิดใช้งานเรียบร้อยแล้ว",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "role_display": user.get_role_display(),
                "department": getattr(user, 'department', '')
            },
            "redirect_url": redirect_url
        }, status=status.HTTP_200_OK)

class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Resend a fresh 6-digit OTP PIN",
        request_body=ResendOTPSerializer
    )
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = CustomUser.objects.filter(email=email).first()
        if not user:
            return Response({"error": "ไม่พบบัญชีผู้ใช้ที่ผูกกับอีเมลนี้"}, status=status.HTTP_404_NOT_FOUND)

        pin = f"{random.randint(100000, 999999)}"
        expires_at = timezone.now() + timedelta(minutes=10)
        EmailOTP.objects.create(
            user=user,
            email=user.email,
            otp_code=pin,
            expires_at=expires_at
        )

        email_sent = send_pin_email(user.email, pin, user.username)

        return Response({
            "message": "สร้างรหัส PIN 6 หลักใหม่เรียบร้อยแล้ว",
            "email": email,
            "email_dispatched": email_sent
        }, status=status.HTTP_200_OK)

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_description="Retrieve current user profile")
    def get(self, request):
        return Response(ProfileSerializer(request.user).data)

    @swagger_auto_schema(
        operation_description="Update current user profile",
        request_body=ProfileSerializer
    )
    def put(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Change user password",
        request_body=ChangePasswordSerializer
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({"error": "รหัสผ่านปัจจุบันไม่ถูกต้อง"}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"message": "เปลี่ยนรหัสผ่านสำเร็จ"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserListView(generics.ListCreateAPIView):
    queryset = CustomUser.objects.all().order_by('-id')
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
    lookup_field = 'id'

class RoomListCreateView(generics.ListCreateAPIView):
    queryset = Room.objects.all().order_by('id')
    serializer_class = RoomSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsStaffOrAdminRole()]

    def get_queryset(self):
        qs = Room.objects.all().order_by('id')
        room_type = self.request.query_params.get('room_type')
        min_capacity = self.request.query_params.get('min_capacity')
        building = self.request.query_params.get('building')
        is_active = self.request.query_params.get('is_active')

        if room_type:
            qs = qs.filter(room_type=room_type)
        if min_capacity:
            try:
                qs = qs.filter(capacity__gte=int(min_capacity))
            except ValueError:
                pass
        if building:
            qs = qs.filter(building__icontains=building)
        if is_active is not None:
            active_val = is_active.lower() in ['true', '1']
            qs = qs.filter(is_active=active_val)
        return qs

class RoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'pk'

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsStaffOrAdminRole()]

class RoomAvailabilityView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        room = get_object_or_404(Room, pk=pk)
        date_str = request.query_params.get('date')
        if not date_str:
            target_date = timezone.localdate()
        else:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "รูปแบบวันที่ไม่ถูกต้อง กรุณาใช้ YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        day_start = timezone.make_aware(datetime.combine(target_date, time(8, 0)))
        day_end = timezone.make_aware(datetime.combine(target_date, time(22, 0)))

        bookings = Booking.objects.filter(
            room=room,
            status__in=['PENDING', 'APPROVED'],
            start_time__lt=day_end,
            end_time__gt=day_start
        ).order_by('start_time')

        slots = []
        for b in bookings:
            start_local = timezone.localtime(b.start_time)
            end_local = timezone.localtime(b.end_time)
            slots.append({
                "booking_id": b.id,
                "title": b.title,
                "status": b.status,
                "status_display": "อนุมัติแล้ว" if b.status == 'APPROVED' else "รอการอนุมัติ",
                "start": start_local.strftime('%H:%M'),
                "end": end_local.strftime('%H:%M'),
            })

        # Precompute hourly blocks from 08:00 to 22:00
        hourly_slots = []
        for hour in range(8, 22):
            s_time = time(hour, 0)
            e_time = time(hour + 1, 0)
            slot_s = timezone.make_aware(datetime.combine(target_date, s_time))
            slot_e = timezone.make_aware(datetime.combine(target_date, e_time))

            overlapping = [
                b for b in bookings 
                if b.start_time < slot_e and b.end_time > slot_s
            ]

            if overlapping:
                b = overlapping[0]
                hourly_slots.append({
                    "time": f"{hour:02d}:00 - {hour+1:02d}:00",
                    "start": f"{hour:02d}:00",
                    "end": f"{hour+1:02d}:00",
                    "is_available": False,
                    "status": b.status,
                    "status_display": "อนุมัติแล้ว" if b.status == 'APPROVED' else "รอการอนุมัติ",
                    "title": b.title
                })
            else:
                hourly_slots.append({
                    "time": f"{hour:02d}:00 - {hour+1:02d}:00",
                    "start": f"{hour:02d}:00",
                    "end": f"{hour+1:02d}:00",
                    "is_available": True,
                    "status_display": "ว่าง",
                    "title": "ว่าง (พร้อมให้เช่า)"
                })

        is_daily = getattr(room, 'price_unit', '') == 'day' or getattr(room, 'is_daily', False)
        daily_stay = None
        if is_daily:
            stay_start = timezone.make_aware(datetime.combine(target_date, time(14, 0)))
            stay_end = timezone.make_aware(datetime.combine(target_date + timedelta(days=1), time(12, 0)))
            overlapping_stays = Booking.objects.filter(
                room=room,
                status__in=['PENDING', 'APPROVED'],
                start_time__lt=stay_end,
                end_time__gt=stay_start
            )
            is_stay_available = not overlapping_stays.exists()
            stay_b = overlapping_stays.first() if not is_stay_available else None
            daily_stay = {
                "date": target_date.strftime('%Y-%m-%d'),
                "check_in": "14:00 น.",
                "check_out": "12:00 น. (วันถัดไป)",
                "is_available": is_stay_available,
                "status_display": "ว่าง (เปิดจองรายวัน)" if is_stay_available else ("จองแล้ว" if stay_b.status == 'APPROVED' else "รอการอนุมัติ"),
                "title": "ว่าง (พร้อมให้เช็คอินเข้าพัก)" if is_stay_available else (stay_b.title if stay_b else "มีผู้จองแล้ว")
            }

        return Response({
            "room_id": room.id,
            "room_number": room.room_number,
            "room_name": room.name,
            "building": room.building,
            "floor": room.floor,
            "capacity": room.capacity,
            "price_per_hour": float(room.price_per_hour),
            "price_unit": room.price_unit,
            "price_unit_display": room.price_unit_display,
            "is_daily": is_daily,
            "daily_stay": daily_stay,
            "room_type": room.room_type,
            "room_type_display": room.get_room_type_display(),
            "tags": room.tag_list,
            "amenities": room.amenities,
            "image_url": room.image.url if room.image else "/static/images/rooms/private_cafe.png",
            "is_active": room.is_active,
            "date": target_date.strftime('%Y-%m-%d'),
            "business_hours": {"open": "08:00", "close": "22:00"},
            "reserved_slots": slots,
            "hourly_slots": hourly_slots,
            "available_count": sum(1 for s in hourly_slots if s["is_available"]),
            "total_slots": len(hourly_slots),
        })

class BookingListCreateView(generics.ListCreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Booking.objects.select_related('user', 'room').prefetch_related('equipments').all().order_by('-start_time')
        if not (getattr(user, 'role', '') in ['admin', 'staff'] or user.is_staff or user.is_superuser):
            qs = qs.filter(user=user)

        room_id = self.request.query_params.get('room')
        status_param = self.request.query_params.get('status')
        date_param = self.request.query_params.get('date')

        if room_id:
            qs = qs.filter(room_id=room_id)
        if status_param:
            qs = qs.filter(status=status_param.upper())
        if date_param:
            try:
                parsed_date = datetime.strptime(date_param, '%Y-%m-%d').date()
                qs = qs.filter(start_time__date=parsed_date)
            except ValueError:
                pass
        return qs

    def perform_create(self, serializer):
        validated = serializer.validated_data
        start_time = validated.get('start_time')
        end_time = validated.get('end_time')
        room = validated.get('room')
        
        base_price = getattr(room, 'price_per_hour', Decimal('500.00')) if room else Decimal('500.00')
        stay_days = validated.get('stay_days')
        stay_nights = validated.get('stay_nights')

        if getattr(room, 'price_unit', '') == 'day' or getattr(room, 'is_daily', False):
            # Daily booking calculation (1 day 0 nights = 0.5; D days D-1 nights = (D-1)+0.5; D days D nights = D units)
            if stay_nights is None or stay_days is None:
                diff_seconds = (end_time - start_time).total_seconds() if (start_time and end_time) else 86400.0
                calc_days = max(1, round(diff_seconds / 86400.0))
                stay_days = stay_days or calc_days
                stay_nights = stay_nights or calc_days

            if stay_nights == 0:
                chargeable_units = Decimal(str(max(1, stay_days))) * Decimal('0.5')
            elif stay_nights < stay_days:
                chargeable_units = Decimal(str(stay_nights)) + Decimal('0.5')
            else:
                chargeable_units = Decimal(str(max(1, stay_nights)))

            subtotal = chargeable_units * Decimal(str(base_price))
        else:
            # Hourly booking calculation
            hours = 1.0
            if start_time and end_time:
                diff = (end_time - start_time).total_seconds() / 3600.0
                hours = max(1.0, round(diff, 2))
            subtotal = Decimal(str(hours)) * Decimal(str(base_price))
            stay_days = 0
            stay_nights = 0
        
        total_price = subtotal

        coupon_code = validated.get('coupon_code', '')
        if coupon_code:
            code = coupon_code.strip()
            uc = UserCoupon.objects.filter(user=self.request.user, coupon__code__iexact=code, is_used=False).first()
            if uc:
                is_eligible, err_msg = uc.coupon.is_eligible_for(room, subtotal)
                if not is_eligible:
                    raise serializers.ValidationError({"coupon_code": f"ไม่สามารถใช้คูปอง '{code}' ได้: {err_msg}"})
                discount_amount = uc.coupon.calculate_discount(subtotal)
                total_price = max(Decimal('0.00'), subtotal - discount_amount)
                uc.is_used = True
                uc.used_at = timezone.now()
                uc.save()

        # If user has payment cards and didn't specify one, assign default
        payment_card = validated.get('payment_card')
        if not payment_card:
            default_card = PaymentCard.objects.filter(user=self.request.user, is_default=True).first()
            if not default_card:
                default_card = PaymentCard.objects.filter(user=self.request.user).first()
            payment_card = default_card

        # Generate a real 6-digit access PIN
        pin = f"{random.randint(100000, 999999)}"

        booking = serializer.save(
            user=self.request.user,
            total_price=total_price,
            payment_card=payment_card,
            payment_status='PAID',
            access_pin=pin
        )

class BookingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Booking.objects.select_related('user', 'room').prefetch_related('equipments').all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdminOrReadOnly]
    lookup_field = 'pk'

class BookingApproveView(APIView):
    permission_classes = [IsStaffOrAdminRole]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if booking.status == 'CANCELLED':
            return Response({"error": "ไม่สามารถอนุมัติคำขอที่ถูกยกเลิกไปแล้วได้"}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = 'APPROVED'
        booking.rejection_reason = ''
        if not booking.access_pin:
            booking.access_pin = f"{random.randint(100000, 999999)}"
        booking.save()
        return Response({
            "message": f"อนุมัติคำขอจองห้อง #{booking.id} เรียบร้อยแล้ว",
            "status": booking.status,
            "access_pin": booking.access_pin
        })

class BookingRejectView(APIView):
    permission_classes = [IsStaffOrAdminRole]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        serializer = BookingStatusActionSerializer(data=request.data)
        serializer.is_valid()
        reason = serializer.validated_data.get('reason', '')
        booking.status = 'REJECTED'
        booking.rejection_reason = reason
        booking.save()
        return Response({"message": f"ปฏิเสธคำขอจองห้อง #{booking.id} เรียบร้อยแล้ว", "status": booking.status, "reason": reason})

class BookingCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        user = request.user
        is_privileged = getattr(user, 'role', '') in ['admin', 'staff'] or user.is_staff or user.is_superuser
        if not is_privileged and booking.user != user:
            return Response({"error": "คุณไม่มีสิทธิ์ในการยกเลิกคำขอนี้"}, status=status.HTTP_403_FORBIDDEN)
        if booking.status == 'CANCELLED':
            return Response({"message": "คำขอนี้ถูกยกเลิกไปแล้ว"}, status=status.HTTP_200_OK)
        booking.status = 'CANCELLED'
        booking.save()
        return Response({"message": f"ยกเลิกคำขอจองห้อง #{booking.id} เรียบร้อยแล้ว", "status": booking.status})

class BookingEquipmentListCreateView(generics.ListCreateAPIView):
    queryset = BookingEquipment.objects.all().order_by('-id')
    serializer_class = BookingEquipmentSerializer
    permission_classes = [IsAuthenticated]

class BookingEquipmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BookingEquipment.objects.all()
    serializer_class = BookingEquipmentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_rooms = Room.objects.count()
        active_rooms = Room.objects.filter(is_active=True).count()
        total_bookings = Booking.objects.count()
        pending_bookings = Booking.objects.filter(status='PENDING').count()
        approved_bookings = Booking.objects.filter(status='APPROVED').count()
        rejected_bookings = Booking.objects.filter(status='REJECTED').count()
        cancelled_bookings = Booking.objects.filter(status='CANCELLED').count()

        utilization = 0.0
        if total_bookings > 0:
            utilization = round((approved_bookings / total_bookings) * 100, 1)

        type_counts = dict(Room.objects.values('room_type').annotate(count=Count('id')).values_list('room_type', 'count'))

        return Response({
            "total_rooms": total_rooms,
            "active_rooms": active_rooms,
            "total_bookings": total_bookings,
            "pending_bookings": pending_bookings,
            "approved_bookings": approved_bookings,
            "rejected_bookings": rejected_bookings,
            "cancelled_bookings": cancelled_bookings,
            "approval_rate_percentage": utilization,
            "room_type_distribution": type_counts,
        })

def dashboard_ui_view(request):
    rooms = Room.objects.all().order_by('id')
    recent_bookings = Booking.objects.select_related('user', 'room').order_by('-created_at')[:25]
    total_rooms = rooms.count()
    total_bookings = Booking.objects.count()
    pending_count = Booking.objects.filter(status='PENDING').count()
    approved_count = Booking.objects.filter(status='APPROVED').count()

    context = {
        'rooms': rooms,
        'recent_bookings': recent_bookings,
        'stats': {
            'total_rooms': total_rooms,
            'total_bookings': total_bookings,
            'pending_count': pending_count,
            'approved_count': approved_count,
        }
    }
    return render(request, 'dashboard.html', context)

class CustomLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Authenticate user, start 7-day Django session, and return JWT tokens",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'password'],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
            }
        )
    )
    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')

        if not username or not password:
            return Response({'detail': 'กรุณากรอกชื่อผู้ใช้และรหัสผ่าน'}, status=status.HTTP_400_BAD_REQUEST)

        # Allow logging in with either username or email address
        auth_username = username
        if '@' in username or not CustomUser.objects.filter(username=username).exists():
            matched_user = CustomUser.objects.filter(email__iexact=username).first()
            if matched_user:
                auth_username = matched_user.username

        user = authenticate(request, username=auth_username, password=password)
        if user is None:
            return Response({'detail': 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({'detail': 'บัญชีนี้ยังไม่ได้รับการยืนยันหรือถูกระงับการใช้งาน'}, status=status.HTTP_403_FORBIDDEN)

        # Start Django session & set 7-day expiry
        login(request, user)
        request.session.set_expiry(60 * 60 * 24 * 7)

        # Issue JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        is_admin = getattr(user, 'role', '') == 'admin' or user.is_superuser or user.is_staff
        redirect_url = '/admin-panel/' if is_admin else '/user/'

        return Response({
            'access': access_token,
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'role_display': user.get_role_display(),
                'department': getattr(user, 'department', ''),
                'phone_number': getattr(user, 'phone_number', ''),
            },
            'redirect_url': redirect_url
        })

def logout_view(request):
    logout(request)
    response = redirect('/auth/?mode=login')
    response.delete_cookie('sessionid')
    return response

def root_redirect_view(request):
    if request.user.is_authenticated:
        if getattr(request.user, 'role', '') == 'admin' or request.user.is_superuser or request.user.is_staff:
            return redirect('/admin-panel/')
        return redirect('/user/')
    return dashboard_ui_view(request)

def auth_ui_view(request):
    if request.user.is_authenticated:
        if getattr(request.user, 'role', '') == 'admin' or request.user.is_superuser or request.user.is_staff:
            return redirect('/admin-panel/')
        return redirect('/user/')
    return render(request, 'auth.html')

def project_report_view(request):
    return render(request, 'PROJECT_REPORT.html')

def download_docx_view(request):
    file_path = os.path.join(settings.BASE_DIR, 'PROJECT_REPORT.docx')
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename='PROJECT_REPORT_Smart_Room_System.docx')
    raise Http404("Report document not found")

def profile_page_view(request):
    if not request.user.is_authenticated:
        return redirect('/auth/?next=/profile/')
    
    payment_cards = request.user.payment_cards.all()
    user_bookings = Booking.objects.filter(user=request.user).select_related('room').order_by('-created_at')[:5]

    return render(request, 'profile.html', {
        'current_user': request.user,
        'payment_cards': payment_cards,
        'user_bookings': user_bookings,
    })

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def add_payment_card_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "กรุณาเข้าสู่ระบบก่อนดำเนินการ"}, status=401)
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)

    card_number = request.POST.get('card_number', '').replace(' ', '').replace('-', '')
    cardholder_name = request.POST.get('cardholder_name', '').strip()
    exp_month = request.POST.get('exp_month', '').strip().zfill(2)
    exp_year = request.POST.get('exp_year', '').strip()[-2:]
    is_default = request.POST.get('is_default') == 'true'

    if not card_number or len(card_number) < 15 or len(card_number) > 16 or not card_number.isdigit():
        return JsonResponse({"error": "หมายเลขบัตรไม่ถูกต้อง (ต้องเป็นตัวเลข 15-16 หลัก)"}, status=400)
    if not cardholder_name:
        return JsonResponse({"error": "กรุณากรอกชื่อผู้ถือบัตร"}, status=400)
    if not exp_month.isdigit() or int(exp_month) < 1 or int(exp_month) > 12:
        return JsonResponse({"error": "เดือนหมดอายุไม่ถูกต้อง"}, status=400)
    if not exp_year.isdigit() or len(exp_year) != 2:
        return JsonResponse({"error": "ปีหมดอายุไม่ถูกต้อง"}, status=400)

    # Detect brand
    if card_number.startswith('4'):
        card_brand = 'visa'
    elif card_number.startswith(('51', '52', '53', '54', '55', '22', '23', '24', '25', '26', '27')):
        card_brand = 'mastercard'
    elif card_number.startswith(('3528', '3529', '353', '354', '355', '356', '357', '358')):
        card_brand = 'jcb'
    elif card_number.startswith(('34', '37')):
        card_brand = 'amex'
    else:
        card_brand = 'visa'

    last_four = card_number[-4:]

    # Check if duplicate
    existing = PaymentCard.objects.filter(user=request.user, last_four=last_four, card_brand=card_brand).first()
    if existing:
        return JsonResponse({"error": f"บัตร {card_brand.upper()} ลงท้ายด้วย {last_four} มีอยู่ในระบบแล้ว"}, status=400)

    # If first card, always make it default
    has_cards = PaymentCard.objects.filter(user=request.user).exists()
    if not has_cards or is_default:
        PaymentCard.objects.filter(user=request.user).update(is_default=False)
        is_default = True

    card = PaymentCard.objects.create(
        user=request.user,
        card_brand=card_brand,
        cardholder_name=cardholder_name,
        last_four=last_four,
        exp_month=exp_month,
        exp_year=exp_year,
        is_default=is_default,
    )

    return JsonResponse({
        "success": True,
        "message": f"เพิ่มบัตร {card.get_card_brand_display()} (•••• {last_four}) สำเร็จ",
        "card": {
            "id": card.id,
            "brand": card.card_brand,
            "brand_display": card.get_card_brand_display(),
            "last_four": card.last_four,
            "exp": f"{card.exp_month}/{card.exp_year}",
            "is_default": card.is_default,
            "cardholder": card.cardholder_name,
        }
    })

@csrf_exempt
def delete_payment_card_api(request, card_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "กรุณาเข้าสู่ระบบก่อนดำเนินการ"}, status=401)
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)

    card = get_object_or_404(PaymentCard, id=card_id, user=request.user)
    was_default = card.is_default
    card.delete()

    # If deleted default card, set next one as default
    if was_default:
        first_card = PaymentCard.objects.filter(user=request.user).first()
        if first_card:
            first_card.is_default = True
            first_card.save()

    return JsonResponse({
        "success": True,
        "message": "ลบบัตรเรียบร้อยแล้ว"
    })

@csrf_exempt
def set_default_payment_card_api(request, card_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "กรุณาเข้าสู่ระบบก่อนดำเนินการ"}, status=401)
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)

    card = get_object_or_404(PaymentCard, id=card_id, user=request.user)
    PaymentCard.objects.filter(user=request.user).update(is_default=False)
    card.is_default = True
    card.save()

    return JsonResponse({
        "success": True,
        "message": f"ตั้งบัตร •••• {card.last_four} เป็นช่องทางหลักเรียบร้อยแล้ว"
    })

@csrf_exempt
def update_profile_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "กรุณาเข้าสู่ระบบก่อนดำเนินการ"}, status=401)
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)

    user = request.user
    updated_fields = []

    # 1. Display name
    display_name = request.POST.get('display_name')
    if display_name is not None and display_name.strip():
        user.first_name = display_name.strip()
        updated_fields.append('first_name')

    # 2. Phone number
    phone_number = request.POST.get('phone_number')
    if phone_number is not None:
        user.phone_number = phone_number.strip()
        updated_fields.append('phone_number')

    # 3. Avatar upload
    if 'avatar' in request.FILES:
        user.avatar = request.FILES['avatar']
        updated_fields.append('avatar')

    if updated_fields:
        user.save()

    avatar_url = user.avatar.url if user.avatar else ''
    display_name_val = user.first_name if user.first_name else user.username

    return JsonResponse({
        "success": True,
        "message": "อัปเดตข้อมูลโปรไฟล์เรียบร้อยแล้ว",
        "display_name": display_name_val,
        "avatar_url": avatar_url,
        "phone_number": user.phone_number
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def claim_coupon_api(request):
    data = request.data if hasattr(request, 'data') and request.data else request.POST

    coupon_id = data.get('coupon_id')
    coupon_code = data.get('coupon_code') or data.get('code')

    coupon = None
    if coupon_id:
        coupon = Coupon.objects.filter(id=coupon_id, is_active=True).first()
    elif coupon_code:
        coupon = Coupon.objects.filter(code__iexact=str(coupon_code).strip(), is_active=True).first()

    if not coupon:
        return Response({"error": "ไม่พบคูปองที่ระบุ หรือคูปองหมดอายุแล้ว"}, status=status.HTTP_404_NOT_FOUND)

    user_coupon, created = UserCoupon.objects.get_or_create(
        user=request.user,
        coupon=coupon
    )

    my_coupons_count = UserCoupon.objects.filter(user=request.user, is_used=False).count()
    unclaimed_count = Coupon.objects.filter(is_active=True).exclude(user_claims__user=request.user).count()

    return Response({
        "status": "success",
        "message": f"รับสิทธิ์คูปอง '{coupon.discount_title}' สำเร็จแล้ว!",
        "coupon_id": coupon.id,
        "coupon_code": coupon.code,
        "discount_title": coupon.discount_title,
        "discount_percent": coupon.discount_percent,
        "icon_type": coupon.icon_type,
        "sub_title": coupon.sub_title,
        "info_tooltip": coupon.info_tooltip,
        "expires_at": coupon.expires_at.strftime("%d %b %Y") if coupon.expires_at else "ไม่มีวันหมดอายุ",
        "already_claimed": not created,
        "my_coupons_count": my_coupons_count,
        "unclaimed_count": unclaimed_count,
    })

def user_portal_view(request):
    if not request.user.is_authenticated:
        return redirect('/auth/?next=/user/')

    # Real rooms from Database
    rooms = Room.objects.all().order_by('room_number')
    
    # Real bookings for THIS logged-in user
    my_bookings = Booking.objects.filter(user=request.user).select_related('room').order_by('-created_at')
    
    # Active approved booking for top alert card
    active_booking = my_bookings.filter(status='APPROVED').first()
    
    my_total = my_bookings.count()
    approved_count = my_bookings.filter(status='APPROVED').count()
    pending_count = my_bookings.filter(status='PENDING').count()
    rejected_count = my_bookings.filter(status='REJECTED').count()

    # Real coupons from Database with claimed status
    all_coupons = list(Coupon.objects.filter(is_active=True).order_by('order', 'id'))
    user_claims_qs = UserCoupon.objects.filter(user=request.user).select_related('coupon')
    claimed_coupon_ids = set(user_claims_qs.values_list('coupon_id', flat=True))

    unclaimed_coupons = []
    claimed_coupons = []

    for c in all_coupons:
        if c.id in claimed_coupon_ids:
            c.is_claimed = True
            claimed_coupons.append(c)
        else:
            c.is_claimed = False
            unclaimed_coupons.append(c)

    # In carousel: Unclaimed first, Claimed coupons sent to the back
    carousel_coupons = unclaimed_coupons + claimed_coupons
    my_coupons = user_claims_qs.order_by('is_used', '-claimed_at')
    my_coupons_count = user_claims_qs.filter(is_used=False).count()
    unclaimed_count = len(unclaimed_coupons)

    # Real promotional banners from Database
    import json
    thai_months = ['', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
    all_active_banners = list(PromotionBanner.objects.filter(is_active=True).select_related('coupon', 'secondary_coupon').order_by('order', 'id'))
    wide_banners = [b for b in all_active_banners if b.banner_type == 'main_wide']
    compact_banners = [b for b in all_active_banners if b.banner_type == 'side_compact']

    def format_coupon_dict(cp):
        if not cp:
            return None
        exp_str = 'ไม่มีวันหมดอายุ'
        if cp.expires_at:
            exp_str = f"{cp.expires_at.day} {thai_months[cp.expires_at.month]} {cp.expires_at.year} เวลา {cp.expires_at.strftime('%H:%M')} น."
        return {
            'id': cp.id,
            'code': cp.code,
            'discount_title': cp.discount_title,
            'sub_title': cp.sub_title,
            'discount_percent': cp.discount_percent,
            'min_spend': float(cp.min_spend),
            'max_discount_amount': float(cp.max_discount_amount) if cp.max_discount_amount else None,
            'applicable_category': cp.applicable_category,
            'applicable_category_display': cp.applicable_category_display,
            'expires_at_display': exp_str,
            'is_claimed': cp.id in claimed_coupon_ids,
            'terms': [t.strip() for t in (cp.terms or '').split('\n') if t.strip()],
        }

    campaigns_data = {}
    for b in all_active_banners:
        banner_terms = [t.strip() for t in (b.terms or '').split('\n') if t.strip()]
        campaigns_data[str(b.id)] = {
            'id': b.id,
            'title': b.title,
            'badge_text': b.badge_text or 'โปรโมชันพิเศษ',
            'image_url': b.image.url if b.image else '',
            'description': b.description,
            'terms': banner_terms,
            'target_url': b.target_url,
            'coupon': format_coupon_dict(b.coupon),
            'secondary_coupon': format_coupon_dict(b.secondary_coupon),
        }

    context = {
        'rooms': rooms,
        'coupons': carousel_coupons,
        'my_coupons': my_coupons,
        'my_coupons_count': my_coupons_count,
        'unclaimed_count': unclaimed_count,
        'wide_banners': wide_banners,
        'compact_banners': compact_banners,
        'campaigns_json': json.dumps(campaigns_data, ensure_ascii=False),
        'my_bookings': my_bookings,
        'active_booking': active_booking,
        'payment_cards': request.user.payment_cards.all(),
        'stats': {
            'total_rooms': rooms.count(),
            'my_total': my_total,
            'approved_count': approved_count,
            'pending_count': pending_count,
            'rejected_count': rejected_count,
        },
        'current_user': request.user,
    }
    return render(request, 'user_portal.html', context)

def admin_portal_view(request):
    if not request.user.is_authenticated:
        return redirect('/auth/?next=/admin-panel/')
    
    # Role gate: only admin, superuser, or staff
    if getattr(request.user, 'role', '') != 'admin' and not request.user.is_superuser and not request.user.is_staff:
        return redirect('/user/')

    # 1. Rooms, bookings, and users
    rooms = Room.objects.all().order_by('id')
    all_bookings = Booking.objects.select_related('user', 'room').order_by('-created_at')
    pending_bookings = Booking.objects.filter(status='PENDING').select_related('user', 'room').order_by('-created_at')
    users = CustomUser.objects.all().order_by('-date_joined')
    
    total_rooms = rooms.count()
    available_rooms = rooms.filter(is_active=True).count()
    total_bookings = all_bookings.count()
    pending_count = pending_bookings.count()
    approved_count = Booking.objects.filter(status='APPROVED').count()
    total_users = users.count()

    # 2. Enhanced R1: Coupons with claim annotations and active coupons list
    coupons = Coupon.objects.annotate(
        claims_count=Count('user_claims', distinct=True),
        used_count=Count('user_claims', filter=Q(user_claims__is_used=True), distinct=True)
    ).order_by('order', 'id')
    all_active_coupons = Coupon.objects.filter(is_active=True).order_by('order', 'code')

    # 3. Enhanced R2: Promotional Banners & Live Shopee Modal JSON serialization
    import json
    thai_months = ['', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']

    all_banners = list(PromotionBanner.objects.select_related('coupon', 'secondary_coupon').order_by('order', 'id'))
    wide_banners = [b for b in all_banners if b.banner_type == 'main_wide']
    compact_banners = [b for b in all_banners if b.banner_type == 'side_compact']

    def format_coupon_for_modal(cp):
        if not cp:
            return None
        exp_str = 'ไม่มีวันหมดอายุ'
        if cp.expires_at:
            exp_local = timezone.localtime(cp.expires_at)
            exp_str = f"{exp_local.day} {thai_months[exp_local.month]} {exp_local.year} เวลา {exp_local.strftime('%H:%M')} น."
        return {
            'id': cp.id,
            'code': cp.code,
            'discount_title': cp.discount_title,
            'sub_title': cp.sub_title,
            'discount_percent': cp.discount_percent,
            'min_spend': float(cp.min_spend),
            'max_discount_amount': float(cp.max_discount_amount) if cp.max_discount_amount else None,
            'applicable_category': cp.applicable_category,
            'applicable_category_display': cp.applicable_category_display,
            'expires_at_display': exp_str,
            'is_claimed': False,
            'terms': [t.strip() for t in (cp.terms or '').split('\n') if t.strip()],
        }

    campaigns_data = {}
    for b in all_banners:
        banner_terms = [t.strip() for t in (b.terms or '').split('\n') if t.strip()]
        campaigns_data[str(b.id)] = {
            'id': b.id,
            'title': b.title,
            'badge_text': b.badge_text or 'โปรโมชันพิเศษ',
            'image_url': b.image.url if b.image else '',
            'banner_type': b.banner_type,
            'description': b.description,
            'terms': banner_terms,
            'target_url': b.target_url,
            'order': b.order,
            'is_active': b.is_active,
            'coupon': format_coupon_for_modal(b.coupon),
            'secondary_coupon': format_coupon_for_modal(b.secondary_coupon),
        }
    campaigns_json = json.dumps(campaigns_data, ensure_ascii=False)

    stats = {
        'total_rooms': total_rooms,
        'available_rooms': available_rooms,
        'total_bookings': total_bookings,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'total_users': total_users,
        'total_coupons': coupons.count(),
        'active_coupons': coupons.filter(is_active=True).count(),
        'total_claims': UserCoupon.objects.count(),
        'used_claims': UserCoupon.objects.filter(is_used=True).count(),
        'total_banners': len(all_banners),
        'active_banners': sum(1 for b in all_banners if b.is_active),
        'wide_banners_count': len(wide_banners),
        'compact_banners_count': len(compact_banners),
    }

    context = {
        'rooms': rooms,
        'all_bookings': all_bookings,
        'pending_bookings': pending_bookings,
        'users': users,
        'coupons': coupons,
        'all_active_coupons': all_active_coupons,
        'all_banners': all_banners,
        'wide_banners': wide_banners,
        'compact_banners': compact_banners,
        'campaigns_json': campaigns_json,
        'stats': stats,
        'current_user': request.user,
    }
    return render(request, 'admin_portal.html', context)


# ============================================================================
# MILESTONE 1: ADMIN COUPON & CAMPAIGN BANNER VIEWS (R1 & R2)
# ============================================================================

class AdminCouponListCreateView(generics.ListCreateAPIView):
    """
    GET: List all coupons with search, category filtering, active filter, and ordering.
    POST: Create a new promotional coupon.
    Protected by IsStaffOrAdminRole.
    """
    serializer_class = AdminCouponSerializer
    permission_classes = [IsStaffOrAdminRole]

    def get_queryset(self):
        qs = Coupon.objects.annotate(
            claims_count=Count('user_claims', distinct=True),
            used_count=Count('user_claims', filter=Q(user_claims__is_used=True), distinct=True)
        )

        q = self.request.query_params.get('q') or self.request.query_params.get('search')
        if q:
            q_clean = q.strip()
            qs = qs.filter(
                Q(code__icontains=q_clean) |
                Q(discount_title__icontains=q_clean) |
                Q(sub_title__icontains=q_clean) |
                Q(info_tooltip__icontains=q_clean) |
                Q(terms__icontains=q_clean)
            )

        category = self.request.query_params.get('category')
        if category and category.lower() != 'all':
            qs = qs.filter(
                Q(applicable_category__icontains=category) |
                Q(applicable_category='all')
            )

        is_active = self.request.query_params.get('is_active')
        if is_active is not None and is_active != '':
            active_bool = is_active.lower() in ['true', '1', 'yes']
            qs = qs.filter(is_active=active_bool)

        ordering = self.request.query_params.get('ordering')
        allowed_orderings = {
            'order': 'order',
            '-order': '-order',
            'created_at': 'created_at',
            '-created_at': '-created_at',
            'discount_percent': 'discount_percent',
            '-discount_percent': '-discount_percent',
            'claims_count': 'claims_count',
            '-claims_count': '-claims_count',
            'code': 'code',
            '-code': '-code',
        }
        if ordering in allowed_orderings:
            qs = qs.order_by(allowed_orderings[ordering], 'id')
        else:
            qs = qs.order_by('order', 'id')

        return qs


class AdminCouponDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve coupon details with claim statistics.
    PUT/PATCH: Update coupon properties.
    DELETE: Remove coupon from database.
    Protected by IsStaffOrAdminRole.
    """
    serializer_class = AdminCouponSerializer
    permission_classes = [IsStaffOrAdminRole]
    lookup_field = 'pk'

    def get_queryset(self):
        return Coupon.objects.annotate(
            claims_count=Count('user_claims', distinct=True),
            used_count=Count('user_claims', filter=Q(user_claims__is_used=True), distinct=True)
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        code = instance.code
        self.perform_destroy(instance)
        return Response({
            "status": "success",
            "message": f"ลบคูปอง '{code}' เรียบร้อยแล้ว"
        }, status=status.HTTP_200_OK)


class AdminCouponToggleActiveView(APIView):
    """
    POST: Instant toggle for coupon is_active status.
    Protected by IsStaffOrAdminRole.
    """
    permission_classes = [IsStaffOrAdminRole]

    def post(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)
        coupon.is_active = not coupon.is_active
        coupon.save(update_fields=['is_active'])
        return Response({
            "status": "success",
            "id": coupon.id,
            "code": coupon.code,
            "is_active": coupon.is_active,
            "message": f"{'เปิดใช้งาน' if coupon.is_active else 'ปิดใช้งาน'}คูปอง '{coupon.code}' เรียบร้อยแล้ว"
        }, status=status.HTTP_200_OK)


class AdminCouponClaimsView(APIView):
    """
    GET: Inspection modal data displaying all users who claimed this coupon.
    Protected by IsStaffOrAdminRole.
    """
    permission_classes = [IsStaffOrAdminRole]

    def get(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)
        claims = UserCoupon.objects.filter(coupon=coupon).select_related('user').order_by('-claimed_at')
        
        thai_months = ['', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']

        claims_list = []
        for c in claims:
            u = c.user
            claimed_at_local = timezone.localtime(c.claimed_at)
            claimed_at_display = f"{claimed_at_local.day} {thai_months[claimed_at_local.month]} {claimed_at_local.year} {claimed_at_local.strftime('%H:%M')} น."
            
            used_at_display = None
            if c.used_at:
                used_at_local = timezone.localtime(c.used_at)
                used_at_display = f"{used_at_local.day} {thai_months[used_at_local.month]} {used_at_local.year} {used_at_local.strftime('%H:%M')} น."
            else:
                used_at_display = "ยังไม่ได้ใช้งาน" if not c.is_used else "ใช้งานแล้ว"

            claims_list.append({
                "id": c.id,
                "user_id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": f"{u.first_name} {u.last_name}".strip() or u.username,
                "phone_number": getattr(u, 'phone_number', '') or '-',
                "department": getattr(u, 'department', '') or '-',
                "membership_tier": getattr(u, 'membership_tier', 'standard'),
                "tier_display": u.get_membership_tier_display() if hasattr(u, 'get_membership_tier_display') else 'สมาชิกทั่วไป',
                "claimed_at": c.claimed_at.isoformat(),
                "claimed_at_display": claimed_at_display,
                "is_used": c.is_used,
                "used_at": c.used_at.isoformat() if c.used_at else None,
                "used_at_display": used_at_display,
            })

        return Response({
            "status": "success",
            "coupon_id": coupon.id,
            "coupon_code": coupon.code,
            "discount_title": coupon.discount_title,
            "discount_percent": coupon.discount_percent,
            "claims_count": len(claims_list),
            "used_count": sum(1 for item in claims_list if item["is_used"]),
            "claims": claims_list
        }, status=status.HTTP_200_OK)


class AdminUserClaimsView(APIView):
    """
    GET: Inspection modal data displaying all coupons claimed by a specific user.
    Protected by IsStaffOrAdminRole.
    """
    permission_classes = [IsStaffOrAdminRole]

    def get(self, request, user_id):
        target_user = get_object_or_404(CustomUser, id=user_id)
        claims = UserCoupon.objects.filter(user=target_user).select_related('coupon').order_by('-claimed_at')

        thai_months = ['', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']

        claims_list = []
        for c in claims:
            claimed_at_local = timezone.localtime(c.claimed_at)
            claimed_at_display = f"{claimed_at_local.day} {thai_months[claimed_at_local.month]} {claimed_at_local.year} {claimed_at_local.strftime('%H:%M')} น."

            used_at_display = None
            if c.used_at:
                used_at_local = timezone.localtime(c.used_at)
                used_at_display = f"{used_at_local.day} {thai_months[used_at_local.month]} {used_at_local.year} {used_at_local.strftime('%H:%M')} น."
            else:
                used_at_display = "ยังไม่ได้ใช้งาน" if not c.is_used else "ใช้งานแล้ว"

            cp = c.coupon
            claims_list.append({
                "id": c.id,
                "coupon_id": cp.id,
                "code": cp.code,
                "discount_title": cp.discount_title,
                "discount_percent": cp.discount_percent,
                "min_spend": float(cp.min_spend),
                "max_discount_amount": float(cp.max_discount_amount) if cp.max_discount_amount else None,
                "claimed_at": c.claimed_at.isoformat(),
                "claimed_at_display": claimed_at_display,
                "is_used": c.is_used,
                "used_at": c.used_at.isoformat() if c.used_at else None,
                "used_at_display": used_at_display,
            })

        return Response({
            "status": "success",
            "user_id": target_user.id,
            "username": target_user.username,
            "email": target_user.email,
            "full_name": f"{target_user.first_name} {target_user.last_name}".strip() or target_user.username,
            "total_claims": len(claims_list),
            "used_count": sum(1 for item in claims_list if item["is_used"]),
            "claims": claims_list
        }, status=status.HTTP_200_OK)


class AdminBannerListCreateView(generics.ListCreateAPIView):
    """
    GET: List banners filtered by banner_type, active status, or search query.
    POST: Upload multipart image and link primary/secondary coupons.
    Protected by IsStaffOrAdminRole.
    """
    serializer_class = AdminBannerSerializer
    permission_classes = [IsStaffOrAdminRole]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = PromotionBanner.objects.select_related('coupon', 'secondary_coupon').all()

        banner_type = self.request.query_params.get('banner_type')
        if banner_type:
            qs = qs.filter(banner_type=banner_type)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None and is_active != '':
            active_bool = is_active.lower() in ['true', '1', 'yes']
            qs = qs.filter(is_active=active_bool)

        q = self.request.query_params.get('q') or self.request.query_params.get('search')
        if q:
            q_clean = q.strip()
            qs = qs.filter(
                Q(title__icontains=q_clean) |
                Q(badge_text__icontains=q_clean) |
                Q(description__icontains=q_clean)
            )

        return qs.order_by('order', 'id')


class AdminBannerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve single banner details with expanded coupon information.
    PUT/PATCH: Update banner metadata and/or image.
    DELETE: Remove banner.
    Protected by IsStaffOrAdminRole.
    """
    serializer_class = AdminBannerSerializer
    permission_classes = [IsStaffOrAdminRole]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'pk'
    queryset = PromotionBanner.objects.select_related('coupon', 'secondary_coupon').all()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        title = instance.title
        self.perform_destroy(instance)
        return Response({
            "status": "success",
            "message": f"ลบแบนเนอร์ '{title}' เรียบร้อยแล้ว"
        }, status=status.HTTP_200_OK)


class AdminBannerToggleActiveView(APIView):
    """
    POST: Instant toggle for banner is_active status.
    Protected by IsStaffOrAdminRole.
    """
    permission_classes = [IsStaffOrAdminRole]

    def post(self, request, pk):
        banner = get_object_or_404(PromotionBanner, pk=pk)
        banner.is_active = not banner.is_active
        banner.save(update_fields=['is_active'])
        return Response({
            "status": "success",
            "id": banner.id,
            "title": banner.title,
            "is_active": banner.is_active,
            "message": f"{'เปิดใช้งาน' if banner.is_active else 'ปิดใช้งาน'}แบนเนอร์ '{banner.title}' เรียบร้อยแล้ว"
        }, status=status.HTTP_200_OK)


class AdminBannerReorderView(APIView):
    """
    POST: Reorder banners atomically.
    Accepts:
    - {"banner_ids": [id1, id2, id3, ...]}
    - {"order_ids": [id1, id2, id3, ...]}
    - {"items": [{"id": id1, "order": 0}, {"id": id2, "order": 1}, ...]}
    Protected by IsStaffOrAdminRole.
    """
    permission_classes = [IsStaffOrAdminRole]

    def post(self, request):
        banner_ids = request.data.get('banner_ids') or request.data.get('order_ids')
        items = request.data.get('items')

        if not banner_ids and not items:
            return Response(
                {"error": "กรุณาระบุ 'banner_ids' (array ของ ID) หรือ 'items' (array ของ {id, order})"},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            updated_count = 0
            if banner_ids and isinstance(banner_ids, list):
                for new_order, b_id in enumerate(banner_ids):
                    rows = PromotionBanner.objects.filter(id=b_id).update(order=new_order)
                    updated_count += rows
            elif items and isinstance(items, list):
                for item in items:
                    b_id = item.get('id')
                    order_val = item.get('order', 0)
                    if b_id is not None:
                        rows = PromotionBanner.objects.filter(id=b_id).update(order=order_val)
                        updated_count += rows

        return Response({
            "status": "success",
            "message": "บันทึกลำดับแบนเนอร์เรียบร้อยแล้ว",
            "updated_count": updated_count
        }, status=status.HTTP_200_OK)


# ==================== ADMIN VENUES & ROOM GALLERY (R3) ====================

class AdminRoomGalleryCreateView(APIView):
    """
    POST: Upload panorama gallery photo for a specific room (RoomImage).
    GET: List all gallery photos for the room.
    Protected by IsStaffOrAdminRole.
    """
    permission_classes = [IsStaffOrAdminRole]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, room_id):
        room = get_object_or_404(Room, pk=room_id)
        images = room.gallery_images.all().order_by('order', 'id')
        serializer = RoomImageSerializer(images, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, room_id):
        room = get_object_or_404(Room, pk=room_id)
        serializer = RoomImageSerializer(data=request.data)
        if serializer.is_valid():
            img = serializer.save(room=room)
            return Response(RoomImageSerializer(img).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminRoomGalleryDeleteView(APIView):
    """
    DELETE: Delete a specific gallery photo.
    Protected by IsStaffOrAdminRole.
    """
    permission_classes = [IsStaffOrAdminRole]

    def delete(self, request, pk):
        image = get_object_or_404(RoomImage, pk=pk)
        image.delete()
        return Response({
            "status": "success",
            "message": "ลบรูปภาพแกลเลอรีเรียบร้อยแล้ว"
        }, status=status.HTTP_200_OK)


# ==================== ADMIN BOOKINGS MANAGEMENT (R4) ====================

class AdminBookingPinView(APIView):
    """
    POST: Manual override or automatic regeneration of 6-digit access PIN.
    Accepts:
    - {"pin": "654321"} (strictly 6 numeric digits)
    - {"regenerate": true}
    Protected by IsStaffOrAdminRole.
    """
    permission_classes = [IsStaffOrAdminRole]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        regenerate = request.data.get('regenerate', False)
        if str(regenerate).lower() in ['true', '1']:
            import secrets
            new_pin = f"{secrets.randbelow(900000) + 100000:06d}"
            if new_pin == booking.access_pin:
                new_pin = f"{(int(new_pin) + 1) % 900000 + 100000:06d}"
            booking.access_pin = new_pin
            booking.save(update_fields=['access_pin'])
            return Response({
                "status": "success",
                "message": "สร้างรหัส PIN 6 หลักใหม่สำเร็จ",
                "access_pin": booking.access_pin
            }, status=status.HTTP_200_OK)

        pin = request.data.get('pin')
        if not pin or not isinstance(pin, str) or len(pin) != 6 or not pin.isdigit():
            return Response(
                {"error": "Access PIN must be strictly 6 numeric digits"},
                status=status.HTTP_400_BAD_REQUEST
            )

        booking.access_pin = pin
        booking.save(update_fields=['access_pin'])
        return Response({
            "status": "success",
            "message": "อัปเดตรหัส PIN เข้าห้องสำเร็จ",
            "access_pin": booking.access_pin
        }, status=status.HTTP_200_OK)


class AdminBookingConflictsView(APIView):
    """
    GET: Detect schedule overlaps and return conflicts list.
    Query params: room_id, start, end, exclude_id
    Protected by IsStaffOrAdminRole.
    """
    permission_classes = [IsStaffOrAdminRole]

    def get(self, request):
        room_id = request.query_params.get('room_id')
        start_str = request.query_params.get('start')
        end_str = request.query_params.get('end')
        exclude_id = request.query_params.get('exclude_id')

        if not room_id or not start_str or not end_str:
            return Response(
                {"error": "room_id, start, and end parameters are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.utils.dateparse import parse_datetime
        try:
            start_clean = start_str.strip()
            end_clean = end_str.strip()
            start_dt = parse_datetime(start_clean) or parse_datetime(start_clean.replace(' ', '+'))
            if not start_dt:
                start_dt = datetime.fromisoformat(start_clean.replace('Z', '+00:00').replace(' ', '+'))
            end_dt = parse_datetime(end_clean) or parse_datetime(end_clean.replace(' ', '+'))
            if not end_dt:
                end_dt = datetime.fromisoformat(end_clean.replace('Z', '+00:00').replace(' ', '+'))
        except Exception:
            return Response({"error": "รูปแบบวันและเวลาไม่ถูกต้อง"}, status=status.HTTP_400_BAD_REQUEST)

        if timezone.is_naive(start_dt):
            start_dt = timezone.make_aware(start_dt)
        if timezone.is_naive(end_dt):
            end_dt = timezone.make_aware(end_dt)

        conflicts = Booking.objects.filter(
            room_id=room_id,
            status__in=['PENDING', 'APPROVED'],
            start_time__lt=end_dt,
            end_time__gt=start_dt
        ).select_related('user', 'room')

        if exclude_id:
            conflicts = conflicts.exclude(pk=exclude_id)

        overlapping = []
        for b in conflicts:
            overlapping.append({
                "id": b.id,
                "title": b.title,
                "user": b.user.username if b.user else '',
                "start_time": b.start_time.isoformat() if b.start_time else '',
                "end_time": b.end_time.isoformat() if b.end_time else '',
                "status": b.status,
            })

        return Response({
            "has_conflict": len(overlapping) > 0,
            "conflicts_count": len(overlapping),
            "overlapping_bookings": overlapping,
        }, status=status.HTTP_200_OK)


class AdminBookingExportCSVView(APIView):
    """
    GET: Export all booking records to CSV.
    Protected by IsStaffOrAdminRole.
    """
    permission_classes = [IsStaffOrAdminRole]

    def get(self, request):
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="bookings_export.csv"'
        response.write('\ufeff')

        writer = csv.writer(response)
        writer.writerow(['ID', 'Booking Code', 'Room', 'Room Number', 'User', 'Title', 'Purpose', 'Start Time', 'End Time', 'Status', 'Total Price', 'Access PIN', 'Created At'])

        bookings = Booking.objects.select_related('room', 'user').all().order_by('-created_at')
        for b in bookings:
            writer.writerow([
                b.id,
                f"CONF-{b.id}",
                b.room.name if b.room else '',
                b.room.room_number if b.room else '',
                b.user.username if b.user else '',
                b.title,
                b.purpose or '',
                b.start_time.strftime('%Y-%m-%d %H:%M:%S') if b.start_time else '',
                b.end_time.strftime('%Y-%m-%d %H:%M:%S') if b.end_time else '',
                b.status,
                str(b.total_price),
                b.access_pin or '',
                b.created_at.strftime('%Y-%m-%d %H:%M:%S') if b.created_at else '',
            ])

        return response


# ==================== ADMIN USER RBAC & SECURITY (R5) ====================

class AdminUserHistoryView(APIView):
    """
    GET: User history inspection modal data (wallet coupons & reservations).
    Protected by IsStaffOrAdminRole.
    """
    permission_classes = [IsStaffOrAdminRole]

    def get(self, request, user_id):
        user = get_object_or_404(CustomUser, pk=user_id)

        claimed_coupons = []
        for uc in UserCoupon.objects.filter(user=user).select_related('coupon').order_by('-claimed_at'):
            claimed_coupons.append({
                "id": uc.id,
                "coupon_id": uc.coupon.id if uc.coupon else None,
                "code": uc.coupon.code if uc.coupon else '',
                "title": uc.coupon.discount_title if uc.coupon else '',
                "discount_percent": uc.coupon.discount_percent if uc.coupon else 0,
                "is_used": uc.is_used,
                "claimed_at": uc.claimed_at.isoformat() if uc.claimed_at else None,
                "used_at": uc.used_at.isoformat() if uc.used_at else None,
            })

        bookings = []
        for b in Booking.objects.filter(user=user).select_related('room').order_by('-created_at'):
            bookings.append({
                "id": b.id,
                "room_id": b.room.id if b.room else None,
                "room_name": b.room.name if b.room else '',
                "room_number": b.room.room_number if b.room else '',
                "title": b.title,
                "start_time": b.start_time.isoformat() if b.start_time else None,
                "end_time": b.end_time.isoformat() if b.end_time else None,
                "status": b.status,
                "total_price": str(b.total_price),
                "created_at": b.created_at.isoformat() if b.created_at else None,
            })

        return Response({
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "claimed_coupons": claimed_coupons,
            "bookings": bookings,
        }, status=status.HTTP_200_OK)


class AdminUserResetPasswordView(APIView):
    """
    POST: Administrative password reset without knowing old password.
    Accepts: {"new_password": "..."}
    Protected by IsStaffOrAdminRole.
    """
    permission_classes = [IsStaffOrAdminRole]

    def post(self, request, user_id):
        user = get_object_or_404(CustomUser, pk=user_id)
        new_password = request.data.get('new_password')
        if not new_password or not isinstance(new_password, str) or len(new_password) < 6:
            return Response(
                {"error": "รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 6 ตัวอักษร"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()
        return Response({
            "status": "success",
            "message": f"รีเซ็ตรหัสผ่านสำหรับผู้ใช้ '{user.username}' สำเร็จแล้ว"
        }, status=status.HTTP_200_OK)


# ==================== ADMIN ANALYTICS & KPI REPORTING (R6) ====================

class AdminAnalyticsView(APIView):
    """
    GET: Aggregate live system KPIs (Rooms, Bookings, Users, Coupons, Paid Revenue).
    Protected by IsStaffOrAdminRole.
    """
    permission_classes = [IsStaffOrAdminRole]

    def get(self, request):
        total_rooms = Room.objects.count()
        available_rooms = Room.objects.filter(is_active=True).count()
        maintenance_rooms = Room.objects.filter(is_active=False).count()

        total_bookings = Booking.objects.count()
        approved_bookings = Booking.objects.filter(status='APPROVED').count()
        pending_backlog = Booking.objects.filter(status='PENDING').count()
        rejected_bookings = Booking.objects.filter(status='REJECTED').count()
        cancelled_bookings = Booking.objects.filter(status='CANCELLED').count()

        total_users = CustomUser.objects.count()

        total_coupons = Coupon.objects.count()
        total_claims = UserCoupon.objects.count()
        used_claims = UserCoupon.objects.filter(is_used=True).count()
        redemption_rate = round((used_claims / total_claims * 100), 2) if total_claims > 0 else 0.0

        paid_revenue = Booking.objects.filter(status='APPROVED', payment_status='PAID').aggregate(
            Sum('total_price')
        )['total_price__sum'] or Decimal('0.00')

        return Response({
            "total_rooms": total_rooms,
            "available_rooms": available_rooms,
            "maintenance_rooms": maintenance_rooms,
            "total_bookings": total_bookings,
            "approved_bookings": approved_bookings,
            "pending_backlog": pending_backlog,
            "rejected_bookings": rejected_bookings,
            "cancelled_bookings": cancelled_bookings,
            "total_users": total_users,
            "total_coupons": total_coupons,
            "total_claims": total_claims,
            "used_claims": used_claims,
            "redemption_rate": redemption_rate,
            "total_revenue": str(paid_revenue),
        }, status=status.HTTP_200_OK)


class EmailDiagnoseView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        import socket, ssl, smtplib
        results = {}

        results['gmail_user_env'] = os.environ.get('GMAIL_USER', 'NOT_SET')
        pwd_env = os.environ.get('GMAIL_APP_PASSWORD')
        results['gmail_pwd_env_set'] = bool(pwd_env)
        results['gmail_pwd_len'] = len(pwd_env) if pwd_env else 0
        results['settings_user'] = settings.EMAIL_HOST_USER
        results['settings_pwd_len'] = len(settings.EMAIL_HOST_PASSWORD)

        for port in [587, 465, 2525, 25]:
            try:
                s = socket.create_connection(('smtp.gmail.com', port), timeout=4)
                s.close()
                results[f'socket_{port}'] = 'OPEN'
            except Exception as e:
                results[f'socket_{port}'] = f'FAILED: {type(e).__name__}: {e}'

        # Try sending via 587 if open
        if results.get('socket_587') == 'OPEN':
            try:
                srv = smtplib.SMTP('smtp.gmail.com', 587, timeout=6)
                srv.starttls()
                srv.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                srv.sendmail(settings.EMAIL_HOST_USER, [settings.EMAIL_HOST_USER], 'Subject: Diagnostic 587\n\nTest 587')
                srv.quit()
                results['send_587'] = 'SUCCESS'
            except Exception as e:
                results['send_587'] = f'FAILED: {type(e).__name__}: {e}'

        # Try sending via 465 if open
        if results.get('socket_465') == 'OPEN':
            try:
                ctx = ssl.create_default_context()
                srv = smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ctx, timeout=6)
                srv.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                srv.sendmail(settings.EMAIL_HOST_USER, [settings.EMAIL_HOST_USER], 'Subject: Diagnostic 465\n\nTest 465')
                srv.quit()
                results['send_465'] = 'SUCCESS'
            except Exception as e:
                results['send_465'] = f'FAILED: {type(e).__name__}: {e}'

        return Response(results)

