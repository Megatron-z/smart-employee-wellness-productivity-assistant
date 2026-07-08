from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from database.models import User, Employee
import uuid
import json
import base64
import os
import re
from django.conf import settings



def home(request):
    return render(request, 'auth/home.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_approved:
                messages.warning(request, 'Your account is pending HR approval.')
                return redirect('login')
            
            # Check profile existence BEFORE showing success message
            if user.role == 'employee' and not hasattr(user, 'employee_profile'):
                messages.error(request, "Employee account does not exist.")
                return redirect('login')

            login(request, user)
            messages.success(request, f"Welcome back, {username}!")
            if user.role == 'admin':
                return redirect('employee_list')
            elif user.role == 'hr':
                return redirect('manage_leaves')
            else:
                return redirect('employee_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'auth/login.html')

def register_view(request):
    if request.method == 'POST':
        role = request.POST.get('role', 'employee')
        if role == 'admin':
            messages.error(request, 'Main Admin registration is not allowed.')
            return redirect('register')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        name = request.POST.get('name')
        dept = request.POST.get('department')
        desig = request.POST.get('designation')

    ####
    # Basic format check
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            messages.error(request, "Invalid email format")
            return render(request, 'auth/register.html')

        #  Block numeric domains like 123.com
        domain = email.split('@')[1]          # 123.com
        domain_name = domain.split('.')[0]    # 123

        if domain_name.isdigit():
            messages.error(request, "Email domain cannot be numeric (e.g. 123.com not allowed)")
            return render(request, 'auth/register.html')
        
        # Check if username exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'auth/register.html')

        # Check if email exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'auth/register.html')

        with transaction.atomic():
            # Create user (unapproved)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                is_approved=False
            )
            
            # Generate EMP ID robustly
            base_count = Employee.objects.count() + 1
            emp_id = f"EMP-{1000 + base_count}"
            while Employee.objects.filter(emp_id=emp_id).exists():
                base_count += 1
                emp_id = f"EMP-{1000 + base_count}"
            
            employee = Employee.objects.create(
                user=user,
                emp_id=emp_id,
                name=name,
                department=dept,
                designation=desig
            )
        
        # Handle Facial Data for Employee and HR
        if role in ['employee', 'hr']:
            face_data = request.POST.get('face_data') # base64 string
            if face_data:
                try:
                    import numpy as np
                    import cv2
                    from deepface import DeepFace
                    from modules.utils import ensure_ai_weights
                    
                    # 1. Self-healing for weights
                    ensure_ai_weights()
                    
                    # Convert base64 to image
                    format, imgstr = face_data.split(';base64,') 
                    ext = format.split('/')[-1]
                    img_data = base64.b64decode(imgstr)
                    
                    # Temporary save to extract embedding
                    temp_path = os.path.join(settings.BASE_DIR, 'media', f'temp_face_{user.id}.jpg')
                    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                    with open(temp_path, 'wb') as f:
                        f.write(img_data)
                        
                    # Extract embedding
                    embedding = DeepFace.represent(img_path=temp_path, model_name='VGG-Face', detector_backend="retinaface",enforce_detection=True)[0]['embedding']
                    employee.face_embedding = embedding
                    employee.profile_pic = None # Clear if was set
                    employee.save()
                    
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception as e:
                    print(f"DeepFace Registration Error: {e}")
                    messages.warning(request, f"Registration successful, but facial data extraction failed: {e}. You may need to update your identity data later.")
        
        # Handle Profile Pic for Admin only (Staff/HR use face detection now)
        if role == 'admin':
            profile_pic = request.FILES.get('profile_pic')
            if profile_pic:
                employee.profile_pic = profile_pic
                employee.save()
        
        messages.success(request, f'Registration successful! Your ID is {emp_id}. Please wait for HR approval.')
        return redirect('login')
        
    return render(request, 'auth/register.html')

def logout_view(request):
    # ... (Keep existing logout)
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')

def login_redirect(request):
    if request.user.is_authenticated:
        if request.user.role == 'admin':
            return redirect('employee_list')
        elif request.user.role == 'hr':
            return redirect('manage_leaves')
        else:
            return redirect('employee_dashboard')
    return redirect('login')
