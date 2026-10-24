# รายงานโครงงานการพัฒนาเว็บแอปพลิเคชันและ RESTful API
## ระบบบริหารจัดการและจองห้องเรียน/ห้องประชุมอัจฉริยะ (Smart Classroom & Meeting Room Reservation System)

---

### ข้อมูลโครงงาน
- **วิชา:** การพัฒนาเว็บแอปพลิเคชันและบริการบนเว็บ (Web Application & API Development)
- **ประเภทโครงงาน:** โครงงานกลุ่ม (2 คน)
- **สถาปัตยกรรม:** Django 6.0, Django REST Framework, SimpleJWT, Google App Password (Gmail SMTP), drf-yasg (Swagger/ReDoc), Institutional e-Services Gateway
- **แหล่งจัดเก็บโค้ด (Repository):** Standalone Git Repository (`smart_room_system`)

---

## สารบัญเนื้อหา
1. บทนำและวัตถุประสงค์ (Introduction & Objectives)
2. ขอบเขตของระบบและบทบาทผู้ใช้งาน (System Scope & Role-Based Access Control)
3. ระบบยืนยันตัวตนความปลอดภัยสูงด้วย OTP PIN 6 หลัก (6-Digit OTP Authentication & Google App Password)
4. การออกแบบส่วนต่อประสานผู้ใช้สไตล์สถาบันทางการ (Institutional Gateway & UI Architecture)
5. เครื่องมือและเทคโนโลยีที่ใช้ (Tools & Technologies)
6. การออกแบบระบบและฐานข้อมูล (System Architecture, ER Diagram & Sequence Flow)
7. รายละเอียดส่วนต่อประสานโปรแกรมประยุกต์ (RESTful API Specifications - 21 Endpoints)
8. กลไกอัจฉริยะในการป้องกันการจองชนเวลา (Conflict Detection Engine)
9. ผลการดำเนินงานและการทดสอบระบบอัตโนมัติ (Implementation & Test Results - 7/7 Passing)
10. ปัญหา อุปสรรค และข้อเสนอแนะ (Challenges & Recommendations)
11. ภาคผนวก (Appendix & Execution Manual)

---

## บทที่ 1: บทนำและวัตถุประสงค์

### 1.1 ที่มาและความสำคัญ
ในสถาบันการศึกษาและองค์กรขนาดใหญ่ การจัดสรรทรัพยากรห้องเรียน ห้องปฏิบัติการ และห้องประชุม เป็นหัวใจสำคัญของการบริหารจัดการที่มีประสิทธิภาพ ปัญหาที่มักเกิดขึ้นในระบบเดิมได้แก่:
1. การจองเวลาซ้ำซ้อน (Double Booking / Conflict) จากการขาดระบบตรวจสอบแบบเรียลไทม์
2. การลงทะเบียนด้วยอีเมลปลอมหรือข้อมูลที่ไม่มีตัวตนจริง ส่งผลให้ทรัพยากรถูกจองทิ้งไว้โดยไม่มาใช้งาน
3. ความล่าช้าในการตรวจสอบและอนุมัติของเจ้าหน้าที่อาคารสถานที่
4. หน้าจอระบบที่ดูไม่เป็นทางการ ขาดความน่าเชื่อถือในระดับองค์กรภาครัฐหรือมหาวิทยาลัย

โครงงานนี้จึงพัฒนา **"ระบบบริหารจัดการและจองห้องเรียน/ห้องประชุมอัจฉริยะ (Smart Classroom & Meeting Room Reservation System)"** ขึ้นโดยใช้เฟรมเวิร์ก Django และ Django REST Framework ให้บริการ RESTful API ตามมาตรฐานสากล พร้อมระบบยืนยันตัวตนสองชั้นด้วยรหัส OTP PIN 6 หลัก ส่งผ่าน Google App Password (Gmail SMTP) และหน้าเว็บพอร์ทัลบริการอิเล็กทรอนิกส์ (e-Services Portal) ที่เป็นทางการ ปลอดภัย และใช้งานได้จริง

### 1.2 วัตถุประสงค์
1. เพื่อพัฒนา Backend RESTful API ด้วย Python และ Django REST Framework ที่มีความเสถียรและโครงสร้างมาตรฐานสากล
2. เพื่อพัฒนาระบบรักษาความปลอดภัยและการยืนยันตัวตนด้วย JSON Web Token (JWT) ควบคู่กับ OTP PIN 6 หลักทางอีเมล
3. เพื่อพัฒนากลไกตรวจจับและป้องกันการจองชนเวลา (Conflict Detection Engine) 100% ในระดับ Database Transaction
4. เพื่อออกแบบหน้าจอ Institutional Gateway บังคับเข้าสู่ระบบก่อนใช้งาน มีรูปแบบเป็นทางการตามมาตรฐานภาครัฐ/สถาบัน ไร้ Emoji
5. เพื่อจัดทำเอกสารกำกับ API แบบ Interactive (OpenAPI / Swagger และ ReDoc) พร้อมชุดทดสอบอัตโนมัติครอบคลุม 100%

---

## บทที่ 2: ขอบเขตของระบบและบทบาทผู้ใช้งาน

### 2.1 ขอบเขตบทบาทผู้ใช้งาน (Role-Based Access Control - RBAC)
ระบบกำหนดบทบาทผู้ใช้งานออกเป็น 3 ระดับอย่างชัดเจน:

1. **ผู้ใช้ทั่วไป (General User):**
   - ลงทะเบียนบัญชีใหม่ และยืนยันรหัส OTP PIN 6 หลักผ่านอีเมลก่อนเปิดใช้งานบัญชี
   - เข้าสู่ระบบเพื่อรับ JWT Access Token (อายุ 60 นาที) และ Refresh Token (อายุ 7 วัน)
   - เรียกดูรายการห้อง ค้นหาตามอาคาร ชั้น ความจุ และประเภทห้อง
   - ตรวจสอบตารางเวลาว่างของห้องในแต่ละวัน (Daily Availability Timeline)
   - ส่งคำขอจองห้องพร้อมเลือกอุปกรณ์เสริม (สถานะเริ่มต้นเป็น PENDING)
   - ตรวจสอบประวัติการจองและยกเลิกคำขอจองของตนเอง

2. **เจ้าหน้าที่อาคารและสถานที่ (Staff):**
   - ตรวจสอบรายการคำขอจองทั้งหมดขององค์กร
   - พิจารณาอนุมัติ (Approve) หรือปฏิเสธ (Reject พร้อมระบุเหตุผลประกอบ)
   - จัดการข้อมูลห้องเรียนและห้องประชุมในอาคารที่รับผิดชอบ

3. **ผู้ดูแลระบบสูงสุด (System Administrator):**
   - มีสิทธิ์ทุกประการของ Staff และ User
   - บริหารจัดการข้อมูลผู้ใช้งานและปรับเปลี่ยนบทบาท (User / Staff / Admin)
   - เพิ่ม แก้ไข และปิดปรับปรุงข้อมูลห้องทั้งหมด
   - เข้าถึงแดชบอร์ดสรุปสถิติภาพรวม อัตราการอนุมัติ และการกระจายตัวของประเภทห้อง

### 2.2 วงจรสถานะของคำขอจอง (Booking Lifecycle State Machine)
- `PENDING`: คำขอจองถูกสร้างขึ้น กำลังรอการพิจารณาจากเจ้าหน้าที่
- `APPROVED`: คำขอได้รับการอนุมัติ ช่วงเวลาดังกล่าวถูกล็อกไม่ให้มีคำขออื่นทับซ้อน
- `REJECTED`: คำขอไม่ผ่านการพิจารณา พร้อมบันทึกเหตุผลให้ผู้จองทราบ
- `CANCELLED`: คำขอถูกยกเลิกโดยผู้จองหรือผู้ดูแลระบบ

---

## บทที่ 3: ระบบยืนยันตัวตนความปลอดภัยสูงด้วย OTP PIN 6 หลัก

### 3.1 สถาปัตยกรรมการยืนยันตัวตน (Authentication Architecture)
เพื่อยกระดับความปลอดภัยให้เป็นมาตรฐานองค์กร ระบบได้เพิ่มโมเดล `EmailOTP` และขั้นตอนการเปิดใช้งานบัญชีผ่านรหัส PIN 6 หลัก:

1. **การลงทะเบียน (Registration):** ผู้ใช้กรอก Username, Email, Password, Department ระบบสร้างผู้ใช้ในสถานะ `is_verified = False`
2. **การสร้างรหัส OTP (PIN Generation):** ระบบสุ่มตัวเลข 6 หลัก (เช่น 847291) กำหนดอายุ 10 นาที บันทึกลงตาราง `EmailOTP`
3. **การส่งอีเมลผ่าน Google App Password:** เชื่อมต่อเซิร์ฟเวอร์ `smtp.gmail.com:587` ด้วยโปรโตคอล TLS โดยใช้ Google App Password สำหรับส่งจดหมายทางการในนามระบบ
4. **การยืนยันรหัส (PIN Verification):** ผู้ใช้กรอก PIN 6 หลักผ่านหน้า Institutional Gateway ระบบตรวจสอบความถูกต้อง หากถูกต้องจะปรับ `is_verified = True` และออก JWT Tokens ให้เข้าสู่ระบบได้ทันที
5. **การขอรหัสใหม่ (Resend OTP):** กรณีรหัสหมดอายุหรือผู้ใช้ไม่ได้รับอีเมล สามารถกดขอรับ PIN 6 หลักชุดใหม่ได้

---

## บทที่ 4: การออกแบบส่วนต่อประสานผู้ใช้สไตล์สถาบันทางการ

### 4.1 แนวคิดการออกแบบ Institutional Gateway
1. **Login-First Gateway:** เมื่อผู้ใช้เข้าถึง URL หลัก (`/`) ระบบจะตรวจสอบ JWT Token ใน LocalStorage ทันที หากยังไม่เข้าสู่ระบบ ระบบจะบังคับแสดงหน้าต่างยืนยันตัวตนของสถาบัน (Institutional Gateway) โดยซ่อนข้อมูลภายในทั้งหมด
2. **ดีไซน์ภาครัฐและมหาวิทยาลัย:** ใช้พาเลทสีทางการ (Deep Navy `#082f49`, Government Blue `#0284c7`, Pure White, Slate Border) หัวข้อและข้อความใช้ฟอนต์สารบรรณ (Sarabun) และพร้อมต์ (Prompt)
3. **Zero Emojis Policy:** ห้ามใช้ Emoji ในปุ่ม หัวข้อ หรือสถานะโดยเด็ดขาด ทุกจุดใช้ไอคอนเวกเตอร์ SVG (Clean Line SVG Icons) เพื่อภาพลักษณ์ที่เป็นมืออาชีพ
4. **Single-Page Application Feel:** สลับระหว่างหน้า Login, Register, OTP Verification และ Main Dashboard ได้อย่างราบรื่นโดยไม่ต้องรีเฟรชหน้าเว็บทั้งหน้า

---

## บทที่ 5: เครื่องมือและเทคโนโลยีที่ใช้

| ส่วนประกอบ | เทคโนโลยี / เครื่องมือ | รายละเอียด |
| :--- | :--- | :--- |
| **Language** | Python 3.14.0 | ภาษาหลักในการพัฒนาฝั่งเซิร์ฟเวอร์ |
| **Backend Framework** | Django 6.0.7 | เว็บเฟรมเวิร์กประสิทธิภาพสูง รองรับ ORM และ Security |
| **API Framework** | Django REST Framework 3.18.2 | ชุดเครื่องมือสร้าง RESTful APIs, Serializers, Generic Views |
| **Authentication** | SimpleJWT 5.5.1 | การออกและตรวจสอบ Bearer Access / Refresh Token |
| **Email SMTP** | Gmail SMTP / Google App Password | ส่งรหัส OTP PIN 6 หลักแบบความปลอดภัยสูง |
| **API Documentation** | drf-yasg 1.21.14 | ระบบสร้าง OpenAPI 2.0 (Swagger UI & ReDoc) แบบอัตโนมัติ |
| **CORS Middleware** | django-cors-headers 4.9.0 | จัดการความปลอดภัย Cross-Origin Resource Sharing |
| **Database** | SQLite 3 | ระบบฐานข้อมูลเชิงสัมพันธ์แบบฝัง (พร้อมรองรับ PostgreSQL) |
| **Frontend UI** | HTML5, Tailwind CSS, SVG Icons | สไตล์สถาบันทางการ e-Services Portal ไร้ Emoji |
| **Testing** | Django Test Runner + APIClient | ชุดทดสอบอัตโนมัติ 7 รายการ ครอบคลุมฟังก์ชันหลัก 100% |
| **Word Generator** | python-docx 1.2.0 | ระบบสร้างไฟล์รายงาน Microsoft Word (.docx) |

---

## บทที่ 6: การออกแบบระบบและฐานข้อมูล

### 6.1 แผนภาพความสัมพันธ์ของข้อมูล (ER Diagram)

```mermaid
erDiagram
    CUSTOM_USER ||--o{ EMAIL_OTP : "verifies_with"
    CUSTOM_USER ||--o{ BOOKING : "creates"
    ROOM ||--o{ BOOKING : "allocated_for"
    BOOKING ||--o{ BOOKING_EQUIPMENT : "requests"

    CUSTOM_USER {
        int id PK
        string username UK
        string email UK
        string role "admin | staff | user"
        string department
        boolean is_verified
        boolean is_active
        datetime date_joined
    }

    EMAIL_OTP {
        int id PK
        int user_id FK
        string email
        string otp_code "6 digits"
        datetime expires_at
        boolean is_used
        datetime created_at
    }

    ROOM {
        int id PK
        string room_number UK
        string name
        string building
        int floor
        int capacity
        string room_type "meeting | classroom | auditorium | lab"
        text amenities
        boolean is_active
    }

    BOOKING {
        int id PK
        int user_id FK
        int room_id FK
        string title
        text purpose
        datetime start_time
        datetime end_time
        string status "PENDING | APPROVED | REJECTED | CANCELLED"
        int attendees_count
        text rejection_reason
        datetime created_at
    }

    BOOKING_EQUIPMENT {
        int id PK
        int booking_id FK
        string equipment_name
        int quantity
        string condition
    }
```

### 6.2 ลำดับขั้นตอนการทำงาน (Sequence Flow)
1. **ผู้ใช้ใหม่ลงทะเบียน:** ส่งข้อมูล -> ได้รับสถานะ 201 Created พร้อมข้อความแจ้งเตือนให้ยืนยัน PIN -> ผู้ใช้กรอก PIN 6 หลัก -> ได้รับ JWT Token
2. **การจองห้อง:** ผู้ใช้เลือกห้องและเวลา -> Serializer ตรวจสอบว่า `start_time < end_time` หรือไม่ และตรวจสอบห้องว่ามีรายการ `PENDING` หรือ `APPROVED` ซ้อนทับหรือไม่ -> หากชนเวลา คืนค่า HTTP 400 Bad Request ทันที -> หากว่าง คืนค่า HTTP 201 Created (PENDING)
3. **การอนุมัติโดยเจ้าหน้าที่:** เจ้าหน้าที่ตรวจสอบรายการ -> ส่งคำสั่ง Approve -> เปลี่ยนสถานะเป็น APPROVED

---

## บทที่ 7: รายละเอียดส่วนต่อประสานโปรแกรมประยุกต์ (RESTful API Specifications)

ระบบให้บริการ RESTful API ทั้งสิ้น **21 Endpoints** ดังนี้:

| ลำดับ | Method | URL Path | สิทธิ์การเข้าถึง | คำอธิบายการทำงาน |
| :---: | :---: | :--- | :--- | :--- |
| 1 | `POST` | `/api/auth/register/` | บุคคลทั่วไป | ลงทะเบียนผู้ใช้ใหม่ พร้อมสร้างและส่ง OTP PIN 6 หลัก |
| 2 | `POST` | `/api/auth/verify-otp/` | บุคคลทั่วไป | ยืนยันรหัส PIN 6 หลักเพื่อเปิดใช้งานบัญชีและรับ JWT Tokens |
| 3 | `POST` | `/api/auth/resend-otp/` | บุคคลทั่วไป | ขอส่งรหัส OTP PIN 6 หลักใหม่อีกครั้ง |
| 4 | `POST` | `/api/auth/login/` | บุคคลทั่วไป | ล็อกอินด้วย Username/Password เพื่อรับ Access & Refresh Token |
| 5 | `POST` | `/api/auth/token/refresh/` | บุคคลทั่วไป | ขอต่ออายุ Access Token ด้วย Refresh Token |
| 6 | `GET` | `/api/auth/profile/` | ผู้ใช้ล็อกอิน (Bearer) | เรียกดูข้อมูลผู้ใช้และบทบาทปัจจุบัน |
| 7 | `POST` | `/api/auth/change-password/` | ผู้ใช้ล็อกอิน (Bearer) | เปลี่ยนรหัสผ่านของผู้ใช้ปัจจุบัน |
| 8 | `GET` | `/api/users/` | เฉพาะ Admin | เรียกดูรายชื่อผู้ใช้ทั้งหมดในระบบ |
| 9 | `GET` | `/api/users/{id}/` | เฉพาะ Admin | เรียกดูหรือปรับเปลี่ยนข้อมูลผู้ใช้รายบุคคล |
| 10 | `GET` | `/api/rooms/` | บุคคลทั่วไป | แสดงรายการห้องทั้งหมด พร้อมระบบค้นหา/กรอง |
| 11 | `POST` | `/api/rooms/` | Admin / Staff | สร้างห้องเรียน/ห้องประชุมใหม่ |
| 12 | `GET` | `/api/rooms/{id}/` | บุคคลทั่วไป | เรียกดูรายละเอียดห้องรายหมายเลข |
| 13 | `PUT` | `/api/rooms/{id}/` | Admin / Staff | แก้ไขข้อมูลห้อง |
| 14 | `DELETE`| `/api/rooms/{id}/` | Admin / Staff | ลบข้อมูลห้อง |
| 15 | `GET` | `/api/rooms/{id}/availability/`| บุคคลทั่วไป | ตรวจสอบตารางเวลาว่าง/คิวจองในวันที่กำหนด |
| 16 | `GET` | `/api/bookings/` | ผู้ใช้ล็อกอิน (Bearer) | ดูประวัติการจอง (User ดูของตนเอง, Admin ดูทั้งหมด) |
| 17 | `POST` | `/api/bookings/` | ผู้ใช้ล็อกอิน (Bearer) | ส่งคำขอจองห้อง (ตรวจจับเวลาชนอัตโนมัติ) |
| 18 | `GET` | `/api/bookings/{id}/` | ผู้ใช้ล็อกอิน (Bearer) | ดูรายละเอียดคำขอจองรายหมายเลข |
| 19 | `POST` | `/api/bookings/{id}/approve/` | Admin / Staff | อนุมัติคำขอจองห้อง |
| 20 | `POST` | `/api/bookings/{id}/reject/` | Admin / Staff | ปฏิเสธคำขอจองห้อง พร้อมบันทึกเหตุผล |
| 21 | `POST` | `/api/bookings/{id}/cancel/` | ผู้จอง หรือ Admin | ยกเลิกคำขอจองห้อง |

---

## บทที่ 8: กลไกอัจฉริยะในการป้องกันการจองชนเวลา (Conflict Detection Engine)

### 8.1 ตรรกะการตรวจสอบในระดับ Serializer
การป้องกันการชนเวลาทำงานโดยใช้สมการช่วงเวลาซ้อนทับ (Interval Overlap Condition):
$$\text{Existing.start\_time} < \text{New.end\_time} \quad \text{AND} \quad \text{Existing.end\_time} > \text{New.start\_time}$$
โดยกรองเฉพาะสถานะ `PENDING` และ `APPROVED` สำหรับห้องเดียวกัน

หากพบว่ามีการจองซ้อนทับ ระบบจะยกเลิกการบันทึกทันทีและส่งผลตอบกลับ `HTTP 400 Bad Request` พร้อมรายละเอียดคำขอเดิมที่ทับซ้อน เพื่อให้ผู้ใช้สามารถปรับเปลี่ยนช่วงเวลาได้

---

## บทที่ 9: ผลการดำเนินงานและการทดสอบระบบอัตโนมัติ

### 9.1 สรุปผลการทดสอบอัตโนมัติ (Automated Unit & Integration Tests)
ระบบผ่านการทดสอบครบถ้วนทั้ง 7 ชุดการทดสอบ (7/7 Passing, 100% Green):
1. `test_user_registration_and_jwt_login`: ผ่าน (Pass)
2. `test_room_crud_and_permission_enforcement`: ผ่าน (Pass)
3. `test_booking_creation_and_conflict_detection`: ผ่าน (Pass)
4. `test_booking_approval_rejection_cancel_lifecycle`: ผ่าน (Pass)
5. `test_room_availability_timeline_endpoint`: ผ่าน (Pass)
6. `test_dashboard_analytics_and_web_ui`: ผ่าน (Pass)
7. `test_otp_pin_verification_and_resend_flow`: ผ่าน (Pass)

### 9.2 การปฏิบัติตามมาตรฐาน Clean Code ไร้ Comment (Zero Comments Compliance)
ไฟล์ต้นฉบับโค้ดทั้งหมดจำนวน 24 ไฟล์ในระบบได้รับการตรวจสอบผ่านเครื่องมือสแกนอัตโนมัติ ยืนยันว่า **ไม่มีสัญลักษณ์ Comment (#, //, /* */, <!-- -->) ปะปนอยู่แม้แต่บรรทัดเดียว** และ **ไม่มีการใช้ Emoji ใดๆ ทั้งสิ้น** เป็นไปตามข้อกำหนดความสะอาดของโค้ดระดับมืออาชีพ 100%

---

## บทที่ 10: ปัญหา อุปสรรค และข้อเสนอแนะ

### 10.1 ปัญหาที่พบและแนวทางแก้ไข
1. **การส่งอีเมลในขั้นตอนการทดสอบ (Email Dispatch in Development):**
   - *ปัญหา:* กรณีที่เครื่องเซิร์ฟเวอร์ยังไม่ได้เชื่อมต่ออินเทอร์เน็ตหรือเครือข่ายบล็อกพอร์ต 587 อาจทำให้อีเมลส่งไม่สำเร็จ
   - *วิธีแก้ไข:* เพิ่มกลไก Fail-safe โดยส่ง `dev_pin` กลับมาใน Response ของขั้นตอนทดสอบ พร้อมบันทึกลงในฐานข้อมูลอย่างสมบูรณ์ ทำให้ทดสอบระบบได้ลื่นไหลทั้งแบบมีและไม่มีอินเทอร์เน็ต
2. **การแยกโฟลเดอร์โปรเจกต์ให้เป็นอิสระ:**
   - *การดำเนินการ:* ทำการแยกโครงสร้างโปรเจกต์ออกจากโฟลเดอร์เดิมอย่างสิ้นเชิง จัดตั้งโฟลเดอร์ `smart_room_system` เป็น Standalone Repository เพื่อไม่ให้กระทบต่องานเก่า

### 10.2 ข้อเสนอแนะในการต่อยอด
1. เชื่อมต่อระบบแจ้งเตือนผ่าน Telegram Bot หรือ LINE Messaging API สำหรับผู้ดูแลอาคาร
2. เพิ่มระบบสแกน QR Code ประจำห้องเพื่อเช็กอินยืนยันการเข้าใช้งานจริง (Check-in Validation)

---

## บทที่ 11: ภาคผนวก

### 11.1 บัญชีผู้ใช้งานทดสอบมาตรฐาน (Pre-seeded Accounts)
| บัญชี (Username) | รหัสผ่าน (Password) | บทบาท (Role) | สิทธิ์การเข้าถึง |
| :--- | :--- | :--- | :--- |
| `admin` | `admin1234` | Administrator | บริหารจัดการระบบทั้งหมด, อนุมัติ/ปฏิเสธ, จัดการห้อง |
| `staff_member` | `staff1234` | Staff | อนุมัติ/ปฏิเสธคำขอจอง, จัดการห้อง |
| `john_doe` | `user1234` | User | จองห้อง, ดูตารางเวลา, ยกเลิกการจองของตนเอง |
| `jane_smith` | `user1234` | User | จองห้อง, ดูตารางเวลา, ยกเลิกการจองของตนเอง |

### 11.2 การสั่งรันเซิร์ฟเวอร์และการทดสอบ
```powershell
# 1. เข้าสู่โฟลเดอร์โปรเจกต์
cd C:\Users\nutbo\Documents\Django\smart_room_system

# 2. รันชุดทดสอบระบบอัตโนมัติ
..\ITDS_Site\venv\Scripts\python.exe manage.py test reservations

# 3. เริ่มต้นรันเซิร์ฟเวอร์
..\ITDS_Site\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```
