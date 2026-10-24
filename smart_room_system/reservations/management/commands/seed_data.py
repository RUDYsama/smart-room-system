from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from reservations.models import CustomUser, Room, Booking, BookingEquipment

class Command(BaseCommand):
    help = "Seeds database with realistic initial data"

    def handle(self, *args, **options):
        admin_user, _ = CustomUser.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@itds-organization.local",
                "role": "admin",
                "department": "IT Operations & Infrastructure",
                "phone_number": "02-123-4567",
                "is_staff": True,
                "is_superuser": True
            }
        )
        admin_user.set_password("admin1234")
        admin_user.save()

        staff_user, _ = CustomUser.objects.get_or_create(
            username="staff_member",
            defaults={
                "email": "facility@itds-organization.local",
                "role": "staff",
                "department": "Facility & Building Operations",
                "phone_number": "02-123-4568",
                "is_staff": True
            }
        )
        staff_user.set_password("staff1234")
        staff_user.save()

        john, _ = CustomUser.objects.get_or_create(
            username="john_doe",
            defaults={
                "email": "john.doe@enterprise.local",
                "role": "user",
                "department": "Software Engineering Department",
                "phone_number": "081-987-6543"
            }
        )
        john.set_password("user1234")
        john.save()

        jane, _ = CustomUser.objects.get_or_create(
            username="jane_smith",
            defaults={
                "email": "jane.smith@enterprise.local",
                "role": "user",
                "department": "Data Analytics & AI",
                "phone_number": "089-112-2334"
            }
        )
        jane.set_password("user1234")
        jane.save()

        rooms_data = [
            {
                "room_number": "A-301",
                "name": "Grand Auditorium",
                "building": "Tower A",
                "floor": 3,
                "capacity": 150,
                "room_type": "auditorium",
                "amenities": "4K Laser Projector, Surround Sound System, Dual Wireless Mics, Interactive Stage Podium",
                "is_active": True
            },
            {
                "room_number": "B-402",
                "name": "Executive Boardroom",
                "building": "Tower B",
                "floor": 4,
                "capacity": 22,
                "room_type": "meeting",
                "amenities": "85-inch 4K Display, Polycom Video Conferencing, High-speed Wi-Fi, Conference Phone, Ergonomic Chairs",
                "is_active": True
            },
            {
                "room_number": "A-205",
                "name": "Advanced Computing Laboratory",
                "building": "Tower A",
                "floor": 2,
                "capacity": 45,
                "room_type": "lab",
                "amenities": "45 RTX Workstations, Gigabit Ethernet, Instructor Overhead Monitor, Network Rack Access",
                "is_active": True
            },
            {
                "room_number": "C-501",
                "name": "Lecture Classroom Alpha",
                "building": "Tower C",
                "floor": 5,
                "capacity": 60,
                "room_type": "classroom",
                "amenities": "Dual Whiteboards, Full HD Ceiling Projector, Centralized Air Conditioning, Sound Amplification",
                "is_active": True
            },
            {
                "room_number": "B-108",
                "name": "Agile Sprint Room",
                "building": "Tower B",
                "floor": 1,
                "capacity": 12,
                "room_type": "meeting",
                "amenities": "Glass Whiteboard Walls, 65-inch Mobile Smart Monitor, Standing Desks, Power Pods",
                "is_active": True
            }
        ]

        created_rooms = []
        for r_info in rooms_data:
            room, _ = Room.objects.update_or_create(
                room_number=r_info["room_number"],
                defaults=r_info
            )
            created_rooms.append(room)

        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        tomorrow_10am = now + timedelta(days=1, hours=(10 - now.hour if now.hour != 10 else 0))
        tomorrow_12pm = tomorrow_10am + timedelta(hours=2)
        tomorrow_2pm = tomorrow_10am + timedelta(hours=4)
        tomorrow_4pm = tomorrow_2pm + timedelta(hours=2)

        b1, _ = Booking.objects.get_or_create(
            title="Q4 System Architecture Review",
            room=created_rooms[1],
            defaults={
                "user": john,
                "purpose": "Quarterly system design review and microservice migration sync",
                "start_time": tomorrow_10am,
                "end_time": tomorrow_12pm,
                "status": "APPROVED",
                "attendees_count": 14
            }
        )
        BookingEquipment.objects.get_or_create(
            booking=b1,
            equipment_name="Wireless Presentation Clicker",
            defaults={"quantity": 1, "condition": "New"}
        )
        BookingEquipment.objects.get_or_create(
            booking=b1,
            equipment_name="Video Conference Extension Mic",
            defaults={"quantity": 2, "condition": "Good"}
        )

        b2, _ = Booking.objects.get_or_create(
            title="Machine Learning Workshop Lecture",
            room=created_rooms[2],
            defaults={
                "user": jane,
                "purpose": "Hands-on PyTorch training for senior computer science cohort",
                "start_time": tomorrow_2pm,
                "end_time": tomorrow_4pm,
                "status": "PENDING",
                "attendees_count": 38
            }
        )
        BookingEquipment.objects.get_or_create(
            booking=b2,
            equipment_name="HDMI 4K Splitter Cable",
            defaults={"quantity": 1, "condition": "Good"}
        )

        b3, _ = Booking.objects.get_or_create(
            title="Ad-hoc Gaming Tournament",
            room=created_rooms[0],
            defaults={
                "user": john,
                "purpose": "Informal department social gaming session",
                "start_time": tomorrow_10am - timedelta(days=1),
                "end_time": tomorrow_12pm - timedelta(days=1),
                "status": "REJECTED",
                "rejection_reason": "Auditorium is reserved strictly for academic and official department symposiums.",
                "attendees_count": 50
            }
        )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully with users, rooms, bookings, and equipment."))
