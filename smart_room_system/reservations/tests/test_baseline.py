from datetime import datetime, time, timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from reservations.models import CustomUser, Room, Booking, BookingEquipment, EmailOTP

class ReservationSystemTestSuite(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = CustomUser.objects.create_superuser(
            username='sys_admin',
            email='admin@enterprise.local',
            password='AdminPassword123!',
            role='admin',
            department='Enterprise Architecture'
        )
        self.staff = CustomUser.objects.create_user(
            username='staff_member',
            email='staff@enterprise.local',
            password='StaffPassword123!',
            role='staff',
            department='Facilities'
        )
        self.user1 = CustomUser.objects.create_user(
            username='user_alice',
            email='alice@enterprise.local',
            password='UserPassword123!',
            role='user',
            department='Data Engineering'
        )
        self.user2 = CustomUser.objects.create_user(
            username='user_bob',
            email='bob@enterprise.local',
            password='UserPassword123!',
            role='user',
            department='Product Design'
        )

        self.room_auditorium = Room.objects.create(
            room_number='AUD-101',
            name='Silicon Auditorium',
            building='Engineering Complex',
            floor=1,
            capacity=200,
            room_type='auditorium',
            amenities='Laser Projector, Array Mics',
            is_active=True
        )
        self.room_boardroom = Room.objects.create(
            room_number='BR-502',
            name='Executive Boardroom',
            building='Executive Tower',
            floor=5,
            capacity=18,
            room_type='meeting',
            amenities='Video Bar, 85in Display',
            is_active=True
        )

    def test_user_registration_and_jwt_login(self):
        reg_payload = {
            'username': 'new_developer',
            'email': 'new.dev@enterprise.local',
            'password': 'SecurePassword999!',
            'role': 'user',
            'department': 'Cloud DevOps'
        }
        res_reg = self.client.post('/api/auth/register/', reg_payload, format='json')
        self.assertEqual(res_reg.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_reg.data['username'], 'new_developer')

        login_payload = {
            'username': 'new_developer',
            'password': 'SecurePassword999!'
        }
        res_login = self.client.post('/api/auth/login/', login_payload, format='json')
        self.assertEqual(res_login.status_code, status.HTTP_200_OK)
        self.assertIn('access', res_login.data)
        self.assertIn('refresh', res_login.data)

        access_token = res_login.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        res_prof = self.client.get('/api/auth/profile/')
        self.assertEqual(res_prof.status_code, status.HTTP_200_OK)
        self.assertEqual(res_prof.data['username'], 'new_developer')
        self.assertEqual(res_prof.data['department'], 'Cloud DevOps')

    def test_room_crud_and_permission_enforcement(self):
        res_list = self.client.get('/api/rooms/')
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(res_list.data['count'], 2)

        res_filter = self.client.get('/api/rooms/?room_type=meeting')
        self.assertEqual(res_filter.status_code, status.HTTP_200_OK)
        self.assertEqual(res_filter.data['count'], 1)
        self.assertEqual(res_filter.data['results'][0]['room_number'], 'BR-502')

        new_room_data = {
            'room_number': 'LAB-301',
            'name': 'Robotics Lab',
            'building': 'Engineering Complex',
            'floor': 3,
            'capacity': 30,
            'room_type': 'lab',
            'amenities': 'Robotic Arms, 3D Printers',
            'is_active': True
        }

        self.client.force_authenticate(user=self.user1)
        res_forbidden = self.client.post('/api/rooms/', new_room_data, format='json')
        self.assertEqual(res_forbidden.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.admin)
        res_create = self.client.post('/api/rooms/', new_room_data, format='json')
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_create.data['room_number'], 'LAB-301')

    def test_booking_creation_and_conflict_detection(self):
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        start1 = now + timedelta(days=2, hours=10)
        end1 = start1 + timedelta(hours=2)

        self.client.force_authenticate(user=self.user1)
        booking_payload1 = {
            'room': self.room_boardroom.id,
            'title': 'AI Roadmap Planning',
            'purpose': 'Strategy session for model optimization',
            'start_time': start1.isoformat(),
            'end_time': end1.isoformat(),
            'attendees_count': 10
        }
        res_book1 = self.client.post('/api/bookings/', booking_payload1, format='json')
        self.assertEqual(res_book1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_book1.data['status'], 'PENDING')
        booking1_id = res_book1.data['id']

        self.client.force_authenticate(user=self.user2)
        conflict_start = start1 + timedelta(minutes=30)
        conflict_end = conflict_start + timedelta(hours=1)
        conflict_payload = {
            'room': self.room_boardroom.id,
            'title': 'Overlapping Budget Sync',
            'purpose': 'Budget distribution',
            'start_time': conflict_start.isoformat(),
            'end_time': conflict_end.isoformat(),
            'attendees_count': 5
        }
        res_conflict = self.client.post('/api/bookings/', conflict_payload, format='json')
        self.assertEqual(res_conflict.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', res_conflict.data)
        self.assertTrue(any('conflict' in str(msg).lower() or 'ชนเวลา' in str(msg) for msg in res_conflict.data['non_field_errors']))

        non_conflict_start = end1 + timedelta(hours=1)
        non_conflict_end = non_conflict_start + timedelta(hours=2)
        valid_payload = {
            'room': self.room_boardroom.id,
            'title': 'Afternoon Design Sync',
            'purpose': 'UI review',
            'start_time': non_conflict_start.isoformat(),
            'end_time': non_conflict_end.isoformat(),
            'attendees_count': 8
        }
        res_valid = self.client.post('/api/bookings/', valid_payload, format='json')
        self.assertEqual(res_valid.status_code, status.HTTP_201_CREATED)

        invalid_time_payload = {
            'room': self.room_boardroom.id,
            'title': 'Time Inverted Meeting',
            'start_time': end1.isoformat(),
            'end_time': start1.isoformat(),
            'attendees_count': 4
        }
        res_inverted = self.client.post('/api/bookings/', invalid_time_payload, format='json')
        self.assertEqual(res_inverted.status_code, status.HTTP_400_BAD_REQUEST)

    def test_booking_approval_rejection_cancel_lifecycle(self):
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        start = now + timedelta(days=3, hours=14)
        end = start + timedelta(hours=2)

        booking = Booking.objects.create(
            user=self.user1,
            room=self.room_auditorium,
            title='Annual Dev Summit',
            purpose='Keynote presentation',
            start_time=start,
            end_time=end,
            status='PENDING',
            attendees_count=120
        )

        self.client.force_authenticate(user=self.user2)
        res_unauthorized_approve = self.client.post(f'/api/bookings/{booking.id}/approve/')
        self.assertEqual(res_unauthorized_approve.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.staff)
        res_approve = self.client.post(f'/api/bookings/{booking.id}/approve/')
        self.assertEqual(res_approve.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'APPROVED')

        booking2 = Booking.objects.create(
            user=self.user2,
            room=self.room_auditorium,
            title='Informal Party',
            start_time=start + timedelta(days=1),
            end_time=end + timedelta(days=1),
            status='PENDING'
        )
        self.client.force_authenticate(user=self.admin)
        res_reject = self.client.post(f'/api/bookings/{booking2.id}/reject/', {'reason': 'Non-academic event'}, format='json')
        self.assertEqual(res_reject.status_code, status.HTTP_200_OK)
        booking2.refresh_from_db()
        self.assertEqual(booking2.status, 'REJECTED')
        self.assertEqual(booking2.rejection_reason, 'Non-academic event')

        self.client.force_authenticate(user=self.user1)
        res_cancel = self.client.post(f'/api/bookings/{booking.id}/cancel/')
        self.assertEqual(res_cancel.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CANCELLED')

    def test_room_availability_timeline_endpoint(self):
        target_date = (timezone.now() + timedelta(days=4)).date()
        dt_start = timezone.make_aware(datetime.combine(target_date, time(9, 0)))
        dt_end = timezone.make_aware(datetime.combine(target_date, time(11, 30)))

        Booking.objects.create(
            user=self.user1,
            room=self.room_boardroom,
            title='Morning Briefing',
            start_time=dt_start,
            end_time=dt_end,
            status='APPROVED'
        )

        res = self.client.get(f'/api/rooms/{self.room_boardroom.id}/availability/?date={target_date.strftime("%Y-%m-%d")}')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['room_number'], 'BR-502')
        self.assertEqual(len(res.data['reserved_slots']), 1)
        self.assertEqual(res.data['reserved_slots'][0]['title'], 'Morning Briefing')
        self.assertEqual(res.data['reserved_slots'][0]['start'], '09:00')
        self.assertEqual(res.data['reserved_slots'][0]['end'], '11:30')

    def test_dashboard_analytics_and_web_ui(self):
        self.client.force_authenticate(user=self.admin)
        res_stats = self.client.get('/api/dashboard/stats/')
        self.assertEqual(res_stats.status_code, status.HTTP_200_OK)
        self.assertIn('total_rooms', res_stats.data)
        self.assertIn('total_bookings', res_stats.data)
        self.assertIn('room_type_distribution', res_stats.data)

        self.client.logout()
        res_ui = self.client.get('/')
        self.assertEqual(res_ui.status_code, status.HTTP_200_OK)
        self.assertContains(res_ui, 'VH - Vacation & Hotel')
        self.assertContains(res_ui, 'Silicon Auditorium')

        res_swagger = self.client.get('/swagger/')
        self.assertEqual(res_swagger.status_code, status.HTTP_200_OK)

        res_redoc = self.client.get('/redoc/')
        self.assertEqual(res_redoc.status_code, status.HTTP_200_OK)

    def test_otp_pin_verification_and_resend_flow(self):
        reg_payload = {
            'username': 'candidate_user',
            'email': 'candidate@enterprise.local',
            'password': 'CandidatePassword123!',
            'role': 'user',
            'department': 'Cybersecurity'
        }
        res_reg = self.client.post('/api/auth/register/', reg_payload, format='json')
        self.assertEqual(res_reg.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res_reg.data.get('requires_otp'))

        candidate = CustomUser.objects.get(username='candidate_user')
        self.assertFalse(candidate.is_verified)

        otp_record = EmailOTP.objects.filter(email='candidate@enterprise.local').latest('created_at')
        real_pin = otp_record.otp_code

        res_bad_pin = self.client.post('/api/auth/verify-otp/', {
            'email': 'candidate@enterprise.local',
            'otp_code': '000000'
        }, format='json')
        self.assertEqual(res_bad_pin.status_code, status.HTTP_400_BAD_REQUEST)

        res_verify = self.client.post('/api/auth/verify-otp/', {
            'email': 'candidate@enterprise.local',
            'otp_code': real_pin
        }, format='json')
        self.assertEqual(res_verify.status_code, status.HTTP_200_OK)
        self.assertIn('access', res_verify.data)
        self.assertIn('refresh', res_verify.data)

        candidate.refresh_from_db()
        self.assertTrue(candidate.is_verified)

        res_resend = self.client.post('/api/auth/resend-otp/', {
            'email': 'candidate@enterprise.local'
        }, format='json')
        self.assertEqual(res_resend.status_code, status.HTTP_200_OK)
        new_otp = EmailOTP.objects.filter(email='candidate@enterprise.local').latest('created_at')
        self.assertIsNotNone(new_otp.otp_code)
