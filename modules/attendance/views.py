import json
import base64
import os
import math
import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from database.models import Employee, Attendance, SystemConfig, WellnessLog
from modules.utils import calculate_wellness_score
from datetime import date          
from database.models import LeaveRequest   

logger = logging.getLogger(__name__)

def get_distance(lat1, lon1, lat2, lon2):
    """Haversine formula to calculate distance between two points in meters."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@login_required(login_url='login')
def mark_attendance_page(request):
    """Render the multi-step attendance marking page."""
    config = SystemConfig.objects.first()
    return render(request, 'attendance/mark.html', {'config': config})

@csrf_exempt
@login_required(login_url='login')
def verify_attendance_api(request):
    """
    API to verify GPS, WiFi, and Face.
    Expected POST data: {
        'lat': float,
        'lon': float,
        'wifi_ssid': str,
        'face_image': base64_str,
        'liveness_step': str, # e.g. 'blink', 'look_left'
        'action': 'check_in' or 'check_out'
    }
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        employee = getattr(request.user, 'employee_profile', None)




        ###

        today = timezone.localtime(timezone.now()).date()

        # 🔥 STRICT LEAVE CHECK
        on_leave = LeaveRequest.objects.filter(
            employee=employee,
            start_date__lte=today,
            end_date__gte=today,
            status__iexact='Approved'   # case-insensitive
        ).exists()

        if on_leave:
            return JsonResponse({
                'success': False,
                'error': 'You are on leave today. Attendance blocked.'
            })


        ####

        if not employee:
            return JsonResponse({'success': False, 'error': 'Employee profile not found'}, status=404)

        config = SystemConfig.objects.first()
        if not config:
            return JsonResponse({'success': False, 'error': 'System configuration missing'}, status=500)

        results = {
            'gps': False,
            'wifi': False,
            'face': False,
            'liveness': True # Simplified for now
        }

        # 1. GPS Check
        user_lat = float(data.get('lat', 0))
        user_lon = float(data.get('lon', 0))
        dist = get_distance(user_lat, user_lon, config.office_lat, config.office_lon)
        if dist <= config.office_radius:
            results['gps'] = True
        else:
            logger.warning(f"GPS Failed: Distance {dist}m > {config.office_radius}m")

        # 2. WiFi Check
        user_wifi = data.get('wifi_ssid', '')
        if user_wifi == config.office_wifi_ssid:
            results['wifi'] = True

        # 3. Face Verification
        face_b64 = data.get('face_image')
        
        # Check if user has facial data
        if face_b64 and not employee.face_embedding:
            logger.warning(f"Face verification skipped: User {employee.emp_id} has no facial data stored.")
            results['face'] = False
        elif face_b64 and employee.face_embedding:
            try:
                import numpy as np
                import cv2
                from deepface import DeepFace
                from modules.utils import ensure_ai_weights
                
                # 1. Self-healing for weights
                ensure_ai_weights()
                
                # Decode image
                if ',' in face_b64:
                    face_b64 = face_b64.split(',')[1]
                img_data = base64.b64decode(face_b64)
                
                temp_path = os.path.join(settings.BASE_DIR, 'media', f'attendance_verify_{employee.emp_id}.jpg')
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                with open(temp_path, 'wb') as f:
                    f.write(img_data)

                # Extract the new embedding and compare cosine distance using VGG-Face
                new_repr = DeepFace.represent(img_path=temp_path, model_name='VGG-Face',detector_backend="retinaface",enforce_detection=True)[0]['embedding']
                
                # Cosine similarity
                stored_emb = np.array(employee.face_embedding)
                current_emb = np.array(new_repr)
                
                dot_product = np.dot(stored_emb, current_emb)
                norm_a = np.linalg.norm(stored_emb)
                norm_b = np.linalg.norm(current_emb)
                similarity = dot_product / (norm_a * norm_b)
                
                if similarity > 0.6: # Threshold for VGG-Face cosine similarity
                    results['face'] = True
                else:
                    logger.warning(f"Face Match Failed: Similarity {similarity:.2f} < 0.6")
                
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as e:
                logger.error(f"Face verification error: {e}")
                results['face'] = False # Ensure it's false on error
        else:
            # No image provided
            results['face'] = False

        # Final Decision
        is_valid = results['gps'] and results['wifi'] and results['face']
        
        if is_valid:
            today = timezone.localtime(timezone.now()).date()
            attendance, created = Attendance.objects.get_or_create(employee=employee, date=today)
            
            action = data.get('action', 'check_in')
            if action == 'check_in' and not attendance.login_time:
                attendance.login_time = timezone.now()
            elif action == 'check_out' and attendance.login_time:
                attendance.logout_time = timezone.now()
                # Calculate working hours
                diff = attendance.logout_time - attendance.login_time
                attendance.working_hours = round(diff.total_seconds() / 3600, 2)
            
            attendance.verifications = results
            attendance.is_valid = True
            attendance.save()

            # 4. Handle Wellness Log if provided
            wellness_data = data.get('wellness')
            if wellness_data and action == 'check_in':
                try:
                    WellnessLog.objects.update_or_create(
                        employee=employee,
                        date=today,
                        defaults={
                            'stress_score': float(wellness_data.get('stress_score', 5)),
                            'mood': wellness_data.get('mood', 'Neutral'),
                            'hours_worked': 0.0,
                            'break_time': 0.0,
                            'mental_fatigue': float(wellness_data.get('stress_score', 5))
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to log wellness during attendance: {e}")
            
            return JsonResponse({'success': True, 'message': f'Attendance marked: {action}', 'results': results})
        else:
            errors = []
            if not results['gps']: errors.append("Location (GPS) verification failed. Ensure you are at the office.")
            if not results['wifi']: errors.append("WiFi network verification failed. Connect to office WiFi.")
            if not results['face']: errors.append("Facial recognition verification failed.")
            
            return JsonResponse({
                'success': False, 
                'error': " | ".join(errors), 
                'results': results
            })

    except Exception as e:
        logger.error(f"Attendance API error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    

    
@login_required(login_url='login')
def attendance_history(request):
    """Personal view for employees to see their attendance logs."""
    employee = getattr(request.user, 'employee_profile', None)

    if not employee:
        return redirect('login')
        
    history = Attendance.objects.filter(employee=employee).order_by('-date')
    return render(request, 'attendance/history.html', {'history': history, 'employee': employee})




from datetime import time
from database.models import Employee, Attendance

def get_attendance_status(log, total_hour, check_in, start, have_leave):

    if not log or not log.is_valid:
        return "Absent"

    if total_hour == 0:
        if have_leave:
            return "Leave"
        return "Absent"

    elif total_hour < 6:
        return "Half Day"

    elif check_in and check_in > start and total_hour >= 8:
        return "Late"

    elif total_hour >= 8:
        return "Present"

    return "Half Day"





from django.utils.dateparse import parse_date

@login_required(login_url='login')
def attendance_print(request):

    selected_date = request.GET.get('date')
    if selected_date:
        selected_date = parse_date(selected_date)
    if not selected_date:
        selected_date = date.today()

    employee_data = []
    hr_data = []

    start_time = time(9, 0)

    #  EMPLOYEES
    employees = Employee.objects.filter(user__role='employee')

    for emp in employees:

        log = Attendance.objects.filter(
            employee=emp,
            date=selected_date
        ).first()

        #  CHECK LEAVE FIRST
        on_leave = LeaveRequest.objects.filter(
            employee=emp,
            start_date__lte=selected_date,
            end_date__gte=selected_date,
            status__iexact='Approved'
        ).exists()

        if log:
            total_hour = log.working_hours or 0
            check_in = log.login_time.time() if log.login_time else None
        else:
            total_hour = 0
            check_in = None

        #  FIXED STATUS LOGIC
        if on_leave:
            status = "Leave"

        elif not log or not log.is_valid:
            status = "Absent"

        elif total_hour < 6:
            status = "Half Day"

        elif check_in and total_hour >= 8 and check_in > start_time:
            status = "Late"

        else:
            status = "Present"

        # Wellness
        if log and total_hour > 0:
            score, wellness_status = calculate_wellness_score(70, 5, total_hour, 50, 0.1)
        else:
            score = 0
            wellness_status = "No Data"

        employee_data.append({
            'emp': emp,
            'log': log,
            'status': status,
            'score': score,
            'wellness_status': wellness_status
        })

    #  HR (ONLY ADMIN CAN SEE)
    if request.user.role == 'admin':

        hrs = Employee.objects.filter(user__role='hr')

        for emp in hrs:

            log = Attendance.objects.filter(
                employee=emp,
                date=selected_date
            ).first()


            #  CHECK LEAVE FIRST
            on_leave = LeaveRequest.objects.filter(
                employee=emp,
                start_date__lte=selected_date,
                end_date__gte=selected_date,
                status__iexact='Approved'
            ).exists()


            if log:
                total_hour = log.working_hours or 0
                check_in = log.login_time.time() if log.login_time else None
            else:
                total_hour = 0
                check_in = None

            # Status
            if on_leave:
                status = "Leave"
            elif not log or not log.is_valid:
                status = "Absent"
            elif total_hour < 6:
                status = "Half Day"
            elif check_in and total_hour >= 8 and check_in > start_time:
                status = "Late"
            else:
                status = "Present"

            # Wellness
            if log and total_hour > 0:
                score, wellness_status = calculate_wellness_score(70, 5, total_hour, 50, 0.1)
            else:
                score = 0
                wellness_status = "No Data"

            hr_data.append({
                'emp': emp,
                'log': log,
                'status': status,
                'score': score,
                'wellness_status': wellness_status
            })

    return render(request, 'attendance/attendance_print.html', {
        'employee_data': employee_data,
        'hr_data': hr_data,
        'selected_date': selected_date
    })
