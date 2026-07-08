import json
import base64
import os
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from database.models import Employee, User, WellnessLog, ProductivityLog, SystemConfig, Attendance, LeaveRequest, Payroll
from modules.common import calculate_wellness_score
try:
    from deepface import DeepFace
except ImportError:
    DeepFace = None

@login_required(login_url='login')
def pending_approvals(request):
    if request.user.role not in ['admin', 'hr']:
        messages.error(request, "Access denied.")
        return redirect('employee_dashboard')

    pending_users = User.objects.filter(is_approved=False, role__in=['employee', 'hr'])
    if request.user.role == 'hr':
        pending_users = pending_users.filter(role='employee')

    pending_users = pending_users.prefetch_related('employee_profile')
    return render(request, 'employee/pending_approvals.html', {'pending_users': pending_users})

@login_required(login_url='login')
def approve_user(request, user_id):
    if request.user.role not in ['admin', 'hr']:
        messages.error(request, "Access denied.")
        return redirect('employee_dashboard')

    user = get_object_or_404(User, id=user_id)
    if request.user.role == 'hr' and user.role != 'employee':
        messages.error(request, "HR can approve employee registrations only.")
        return redirect('pending_approvals')

    if request.user.role == 'admin' and user.role not in ['employee', 'hr']:
        messages.error(request, "Only employee and HR registrations can be approved here.")
        return redirect('pending_approvals')

    user.is_approved = True
    user.save()
    messages.success(request, f"User {user.username} has been approved.")
    return redirect('pending_approvals')

@login_required(login_url='login')
def reject_user(request, user_id):
    if request.user.role not in ['admin', 'hr']:
        messages.error(request, "Access denied.")
        return redirect('employee_dashboard')
    
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if request.user.role == 'hr' and user.role != 'employee':
            messages.error(request, "HR can reject employee registrations only.")
            return redirect('pending_approvals')

        if request.user.role == 'admin' and user.role not in ['employee', 'hr']:
            messages.error(request, "Only employee and HR registrations can be rejected here.")
            return redirect('pending_approvals')

        if not user.is_approved:
            username = user.username
            user.delete() # Also deletes employee profile due to CASCADE
            messages.warning(request, f"Registration for {username} has been rejected and the account deleted.")
        else:
            messages.error(request, "Cannot reject an already approved user.")
            
    return redirect('pending_approvals')

@login_required(login_url='login')
def system_config(request):
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Only the Main Admin can access system configuration.")
        return redirect('employee_dashboard')
        
    config, created = SystemConfig.objects.get_or_create(id=1)
    
    if request.method == 'POST':
        config.office_lat = request.POST.get('lat')
        config.office_lon = request.POST.get('lon')
        config.office_radius = request.POST.get('radius')
        config.office_wifi_ssid = request.POST.get('wifi_ssid')
        config.save()
        messages.success(request, "System configuration updated.")
        return redirect('system_config')
        
    return render(request, 'employee/system_config.html', {'config': config})

@login_required(login_url='login')
def employee_dashboard(request):
    # For employees, show their own stats
    employee = getattr(request.user, 'employee_profile', None)
    if not employee:
        auth_logout(request)
        messages.error(request, "Employee account does not exist.")
        return redirect('login')
    
    # Get recent logs
    w_log = WellnessLog.objects.filter(employee=employee).order_by('-date').first()
    p_log = ProductivityLog.objects.filter(employee=employee).order_by('-date').first()
    payroll = getattr(employee, 'payroll', None)
    
    stress = w_log.stress_score if w_log else 5
    hours = (w_log.hours_worked if w_log else 8)
    break_freq = (w_log.break_time / max(hours, 1)) if w_log else 0.125
    prod = p_log.efficiency_score if p_log and p_log.efficiency_score else 70
    salary = payroll.total_salary if payroll else 50000
    
    score, status = calculate_wellness_score(prod, stress, hours, salary, break_freq)
    
    context = {
        'employee': employee,
        'wellness_score': score,
        'wellness_status': status,
        'stress_level': stress,
        'prod_score': prod
    }
    return render(request, 'employee/dashboard.html', context)

@login_required(login_url='login')
def employee_list(request):
    if request.user.role not in ['admin', 'hr']:
        return redirect('employee_dashboard')
    
    employees = list(Employee.objects.all())
    
    # Prepare ranked list with scores
    ranked_employees = []
    total_wellness = 0.0
    high_burnout_count = 0
    
    # Calculate quick wellness summary for each employee
    for emp in employees:
        w_log = WellnessLog.objects.filter(employee=emp).order_by('-date').first()
        p_log = ProductivityLog.objects.filter(employee=emp).order_by('-date').first()
        payroll = getattr(emp, 'payroll', None)
        
        # Default values if no data
        stress = w_log.stress_score if w_log else 5
        hours = w_log.hours_worked if w_log else 8
        break_freq = (w_log.break_time / max(hours, 1)) if w_log else 0.125
        prod = p_log.efficiency_score if p_log and p_log.efficiency_score else 70
        salary = payroll.total_salary if payroll else 50000
        
        score, status = calculate_wellness_score(prod, stress, hours, salary, break_freq)
        
        ranked_employees.append({
            'employee': emp,
            'score': score,
            'status': status
        })
        
        total_wellness += score
        if status in ['Burnout', 'Risk']:
            high_burnout_count += 1
            
    # Wellness Ranking: Sort by score descending
    ranked_employees.sort(key=lambda x: x['score'], reverse=True)
    
    wellness_avg = float(f"{total_wellness / len(employees):.1f}") if len(employees) > 0 else 0.0
    
    context = {
        'ranked_employees': ranked_employees,
        'avg_wellness': wellness_avg,
        'high_burnout_count': high_burnout_count
    }
        
    return render(request, 'employee/list.html', context)

@login_required(login_url='login')
def employee_add(request):
    if request.user.role not in ['admin', 'hr']:
        return redirect('employee_dashboard')
        
    if request.method == 'POST':
        name = request.POST.get('name')
        role = request.POST.get('role', 'employee')
        username = request.POST.get('username')
        password = request.POST.get('password')
        department = request.POST.get('department')
        designation = request.POST.get('designation')
        joining_date = request.POST.get('joining_date')
        profile_pic = request.FILES.get('profile_pic')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username {username} already exists.")
            return redirect('employee_add')

        # 1. Generate EMP ID automatically
        base_count = Employee.objects.count() + 1
        emp_id = f"EMP-{1000 + base_count}"
        while Employee.objects.filter(emp_id=emp_id).exists():
            base_count += 1
            emp_id = f"EMP-{1000 + base_count}"

        with transaction.atomic():
            # 2. Create User with provided credentials
            user = User.objects.create_user(
                username=username, 
                password=password,
                role=role,
                is_approved=True # Admin-added users are pre-approved
            )

            employee = Employee.objects.create(
                user=user,
                emp_id=emp_id,
                name=name,
                department=department,
                designation=designation,
                joining_date=joining_date
            )
            
            # 3. Process Facial Data if photo uploaded
            if profile_pic and DeepFace:
                try:
                    employee.profile_pic = profile_pic
                    employee.save()
                    
                    # Extract embedding from the uploaded file
                    img_path = employee.profile_pic.path
                    embedding = DeepFace.represent(img_path=img_path, model_name='VGG-Face', detector_backend="retinaface",enforce_detection=True)[0]['embedding']
                    employee.face_embedding = embedding
                    employee.save()
                except Exception as e:
                    print(f"Facial Processing Error: {e}")
        
        messages.success(request, f"Employee {name} ({emp_id}) added successfully!")
        return redirect('employee_list')
        
    return render(request, 'employee/add.html')
        
@login_required(login_url='login')
def employee_edit(request, emp_id):
    if request.user.role not in ['admin', 'hr']:
        return redirect('employee_dashboard')
        
    employee = get_object_or_404(Employee, emp_id=emp_id)
    
    if request.method == 'POST':
        employee.name = request.POST.get('name')
        employee.department = request.POST.get('department')
        employee.designation = request.POST.get('designation')
        employee.joining_date = request.POST.get('joining_date')
        employee.save()
        
        messages.success(request, f"Employee {employee.name} updated successfully!")
        return redirect('employee_list')
        
    return render(request, 'employee/edit.html', {'employee': employee})

@login_required(login_url='login')
def employee_delete(request, emp_id):
    if request.user.role not in ['admin', 'hr']:
        return redirect('employee_dashboard')
        
    employee = get_object_or_404(Employee, emp_id=emp_id)
    user = employee.user
    
    name = employee.name
    employee.delete()
    if user:
        user.delete()
        
    messages.success(request, f"Employee {name} and associated account deleted.")
    return redirect('employee_list')
@login_required(login_url='login')
def management_dashboard(request):
    if request.user.role not in ['admin', 'hr']:
        messages.error(request, "Access denied.")
        return redirect('employee_dashboard')
    
    today = timezone.localtime(timezone.now()).date()
    
    # 1. Summary Cards Data
    total_employees = Employee.objects.count()
    present_today = Attendance.objects.filter(date=today, is_valid=True).count()
    on_leave = LeaveRequest.objects.filter(
        status='approved',
        start_date__lte=today,
        end_date__gte=today
    ).count()
    pending_approvals_count = User.objects.filter(is_approved=False).count()
    
    # 2. AI Insights (Metrics summary)
    # High Stress: Stress score >= 8 in last log
    # Low Productivity: Efficiency score < 50 in last log
    # irregular attendance: < 4 valid attendances in last 7 days (simplified)
    
    high_stress_employees: list = []
    low_prod_employees: list = [] # Will store dicts: {'emp': emp, 'reason': str}
    irregular_employees: list = []
    
    employees = Employee.objects.all()
    for emp in employees:
        w_log = WellnessLog.objects.filter(employee=emp).order_by('-date').first()
        p_log = ProductivityLog.objects.filter(employee=emp).order_by('-date').first()
        
        if w_log and w_log.stress_score >= 8:
            high_stress_employees.append(emp)
            
        # 1. Check Efficiency
        if p_log and p_log.efficiency_score and p_log.efficiency_score < 50:
            low_prod_employees.append({'emp': emp, 'reason': f'Efficiency below 50% ({p_log.efficiency_score}%)'})
        
        # 2. Check Today's Working Hours
        today_attendance = Attendance.objects.filter(employee=emp, date=today).first()
        if today_attendance and today_attendance.logout_time:
            if today_attendance.working_hours and today_attendance.working_hours < 7:
                # Avoid duplicates if they already have low efficiency
                if not any(item['emp'] == emp for item in low_prod_employees):
                    low_prod_employees.append({'emp': emp, 'reason': f'Short working hours ({today_attendance.working_hours}h)'})

        recent_attendance_count = Attendance.objects.filter(
            employee=emp, 
            date__gte=today - timedelta(days=7),
            is_valid=True
        ).count()
        if recent_attendance_count < 3: # Arbitrary threshold for "irregular"
            irregular_employees.append(emp)

    # 3. Monthly Trends for Chart.js
    # Last 30 days attendance & leaves
    attendance_trends = []
    leave_trends = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        a_count = Attendance.objects.filter(date=day, is_valid=True).count()
        l_count = LeaveRequest.objects.filter(
            status='approved',
            start_date__lte=day,
            end_date__gte=day
        ).count()
        attendance_trends.append({'day': day.strftime('%d %b'), 'count': a_count})
        leave_trends.append({'day': day.strftime('%d %b'), 'count': l_count})
        
    # Department Distribution & Performance
    dept_counts = list(Employee.objects.values('department').annotate(count=Count('id')))
    
    # Granular Dept-wise Attendance (Total for the month)
    dept_attendance = []
    for stat in dept_counts:
        dept = stat['department']
        count = Attendance.objects.filter(
            employee__department=dept,
            date__gte=today - timedelta(days=30),
            is_valid=True
        ).count()
        dept_attendance.append({'dept': dept, 'count': count})
    
    # Payroll Summary (Simplified)
    total_payroll = sum([p.total_salary for p in Payroll.objects.all()])
    
    # Daily Attendance List
    daily_attendance = Attendance.objects.filter(date=today).select_related('employee').order_by('-login_time')
    
    # Pending Leaves
    pending_leaves = LeaveRequest.objects.filter(status='pending').select_related('employee').order_by('-created_at')[:5]

    # Prepare slices for template
    top_high_stress = [high_stress_employees[i] for i in range(min(3, len(high_stress_employees)))]
    top_low_prod = [low_prod_employees[i] for i in range(min(3, len(low_prod_employees)))]
    top_irregular = [irregular_employees[i] for i in range(min(3, len(irregular_employees)))]

    context = {
        'total_employees': total_employees,
        'present_today': present_today,
        'on_leave': on_leave,
        'pending_approvals_count': pending_approvals_count,
        'high_stress': top_high_stress,
        'low_prod': top_low_prod,
        'irregular': top_irregular,
        'attendance_trends': json.dumps(attendance_trends),
        'leave_trends': json.dumps(leave_trends),
        'dept_counts': json.dumps(dept_counts),
        'dept_attendance': json.dumps(dept_attendance),
        'total_payroll': total_payroll,
        'daily_attendance': daily_attendance,
        'pending_leaves': pending_leaves
    }
    
    return render(request, 'management/dashboard.html', context)

@login_required(login_url='login')
def complete_onboarding(request):
    """View for employees to setup or re-setup their facial identity."""
    employee = getattr(request.user, 'employee_profile', None)
    if not employee:
        return redirect('login')
    
    if request.method == 'POST':
        face_data = request.POST.get('face_data')
        if not face_data:
            messages.error(request, "No facial data received.")
            return redirect('complete_onboarding')
            
        try:
            import numpy as np
            import cv2
            from deepface import DeepFace
            from modules.utils import ensure_ai_weights
            
            # 1. Healing
            ensure_ai_weights()
            
            # 2. Decode
            format, imgstr = face_data.split(';base64,') 
            img_data = base64.b64decode(imgstr)
            
            temp_path = os.path.join(settings.BASE_DIR, 'media', f'setup_face_{employee.id}.jpg')
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            with open(temp_path, 'wb') as f:
                f.write(img_data)
                
            # 3. Extract embedding
            embedding = DeepFace.represent(img_path=temp_path, model_name='VGG-Face', detector_backend="retinaface",enforce_detection=True)[0]['embedding']
            employee.face_embedding = embedding
            employee.save()
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            messages.success(request, "Facial identity successfully setup! You can now mark attendance.")
            return redirect('employee_dashboard')
            
        except Exception as e:
            messages.error(request, f"Failed to process facial data: {e}")
            return redirect('complete_onboarding')
            
    return render(request, 'employee/onboarding.html', {'employee': employee})
