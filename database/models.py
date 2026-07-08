from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('hr', 'HR'),
        ('employee', 'Employee'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    is_approved = models.BooleanField(default=False)

    class Meta:
        db_table = 'users'

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    emp_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    joining_date = models.DateField(null=True, blank=True)
    face_embedding = models.JSONField(null=True, blank=True)
    profile_pic = models.ImageField(upload_to='profiles/', null=True, blank=True)

    class Meta:
        db_table = 'employees'

class WellnessLog(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='wellness_logs')
    stress_score = models.FloatField()  # 1-10
    mood = models.CharField(max_length=50) # Happy, Sad, Neutral
    hours_worked = models.FloatField()
    break_time = models.FloatField() # in hours
    mental_fatigue = models.FloatField(default=0.0) # 0-10
    date = models.DateField(auto_now_add=True)

    class Meta:
        db_table = 'wellness_logs'

class Payroll(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payrolls')
    month = models.DateField()

    basic = models.FloatField()
    hra = models.FloatField()
    ta = models.FloatField()
    da = models.FloatField()
    pf = models.FloatField()

    lop_days = models.IntegerField(default=0)
    lop_amount = models.FloatField(default=0)

    total_salary = models.FloatField()

    class Meta:
        db_table = 'payroll'
        unique_together = ('employee', 'month')

class ProductivityLog(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='productivity_logs')
    tasks_completed = models.IntegerField()
    attendance_rate = models.FloatField() # percentage 0-100
    efficiency_score = models.FloatField(null=True, blank=True)
    date = models.DateField(auto_now_add=True)

    class Meta:
        db_table = 'productivity_logs'

class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(auto_now_add=True)
    login_time = models.DateTimeField(null=True, blank=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    working_hours = models.FloatField(default=0.0)
    verifications = models.JSONField(default=dict) # Store results of GPS, WiFi, Face, Liveness
    is_valid = models.BooleanField(default=False)

    class Meta:
        db_table = 'attendance'

class LeaveRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'leave_requests'

class SystemConfig(models.Model):
    office_lat = models.FloatField(default=8.5241)
    office_lon = models.FloatField(default=76.9366)
    office_radius = models.FloatField(default=100.0) # in meters
    office_wifi_ssid = models.CharField(max_length=100, default='OfficeWiFi')

    class Meta:
        db_table = 'system_config'

from django.db.models.signals import post_delete
from django.dispatch import receiver

@receiver(post_delete, sender=Employee)
def delete_related_user(sender, instance, **kwargs):
    if instance.user_id:
        User.objects.filter(id=instance.user_id).delete()
