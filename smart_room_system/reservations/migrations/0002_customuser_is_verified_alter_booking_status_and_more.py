
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='is_verified',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='booking',
            name='status',
            field=models.CharField(choices=[('PENDING', 'รอการพิจารณา'), ('APPROVED', 'อนุมัติแล้ว'), ('REJECTED', 'ไม่อนุมัติ'), ('CANCELLED', 'ยกเลิกแล้ว')], default='PENDING', max_length=20),
        ),
        migrations.AlterField(
            model_name='bookingequipment',
            name='condition',
            field=models.CharField(blank=True, default='สมบูรณ์', max_length=100),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(choices=[('admin', 'ผู้ดูแลระบบ (Admin)'), ('staff', 'เจ้าหน้าที่อาคาร (Staff)'), ('user', 'ผู้ใช้ทั่วไป (User)')], default='user', max_length=20),
        ),
        migrations.AlterField(
            model_name='room',
            name='room_type',
            field=models.CharField(choices=[('meeting', 'ห้องประชุม'), ('classroom', 'ห้องเรียนบรรยาย'), ('auditorium', 'หอประชุมใหญ่'), ('lab', 'ห้องปฏิบัติการคอมพิวเตอร์')], default='meeting', max_length=30),
        ),
        migrations.CreateModel(
            name='EmailOTP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('otp_code', models.CharField(max_length=6)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('is_used', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='otps', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
