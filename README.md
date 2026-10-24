# Smart Room & Vacation Hotel Reservation System (Void Hunter)

ระบบบริหารจัดการและจองห้องเรียน ห้องประชุม สถานที่จัดกิจกรรม และโรงแรมที่พักอัจฉริยะแบบครบวงจร (Full-stack Django + TailwindCSS + RESTful API + OpenAPI/Swagger)

---

## โครงสร้างโปรเจกต์ (Project Structure)

```
Django/
│
├── smart_room_system/      # โปรเจกต์หลัก Django Application
│   ├── reservations/       # Core App (Models, Views, Serializers, URLs)
│   ├── smart_room_system/  # Project Settings & Root Configurations
│   ├── templates/          # HTML Templates (admin_portal, user_portal, auth, etc.)
│   ├── static/             # Static Assets (Images, Icons, CSS, JS)
│   ├── media/              # User Uploads (Banner images, Room photos, Avatars)
│   ├── db.sqlite3          # SQLite Database
│   └── manage.py           # Django Management Command CLI
│
├── ITDS_Site/              # Python Virtual Environment (venv)
│
├── docs/                   # เอกสารประกอบโครงงาน และแผนงานการพัฒนา
│   ├── tickets/            # สรุป Task และ Specification Tickets (01 - 08)
│   ├── PROJECT.md          # รายละเอียดโครงงานและข้อกำหนด
│   ├── ORIGINAL_REQUEST.md # ข้อกำหนดดั้งเดิมของระบบ
│   ├── TEST_INFRA.md       # โครงสร้างพื้นฐานการทดสอบ
│   └── TEST_READY.md       # สถานะการเตรียมความพร้อมระบบ
│
├── assets/                 # ทรัพยากรไฟล์มีเดียและรูปภาพต้นฉบับ
│   ├── raw_media/          # ภาพแบนเนอร์และภาพประกอบหมวดหมู่
│   └── rooms_reference/    # รูปภาพสถานที่และห้องพักอ้างอิง
│
├── backups/                # ไฟล์สำรองข้อมูลระบบทั้งหมด (Full Zip Archives)
│
├── tools/                  # เครื่องมือและยูทิลิตี้เสริม
│   └── ModelA.py           # Generator CLI tool
│
└── README.md               # เอกสารแนะนำและคู่มือการใช้งานระบบ
```

---

## การเริ่มใช้งานระบบ (Quickstart)

### 1. เข้าสู่ระบบ (Authentication)
- **URL:** [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)
- **บัญชีผู้ดูแลระบบ (Admin):**
  - **Username:** `admin`
  - **Password:** `admin1234`
- **บัญชีเจ้าหน้าที่ (Staff):**
  - **Username:** `staff`
  - **Password:** `staff1234`
- **บัญชีผู้ใช้ทั่วไป (User):**
  - **Username:** `john` / `jane`
  - **Password:** `user1234`

### 2. แผงควบคุมระบบแอดมิน (Admin Console)
- **URL:** [http://127.0.0.1:8000/admin-panel/](http://127.0.0.1:8000/admin-panel/)
- รองรับการควบคุมคูปอง, แบนเนอร์, ห้องและสถานที่, การอนุมัติจอง, และการกำหนดสิทธิ์ผู้ใช้

### 3. เอกสาร API เชิงโต้ตอบ (Swagger & ReDoc)
- **Swagger UI:** [http://127.0.0.1:8000/swagger/](http://127.0.0.1:8000/swagger/)
- **ReDoc UI:** [http://127.0.0.1:8000/redoc/](http://127.0.0.1:8000/redoc/)
- **OpenAPI Schema:** [http://127.0.0.1:8000/swagger.json](http://127.0.0.1:8000/swagger.json)
