from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from database.models import Employee, WellnessLog

@login_required(login_url='login')
def wellness_log(request):
    employee = getattr(request.user, 'employee_profile', None)
    if not employee:
        messages.error(request, "Employee profile not found.")
        return redirect('login')

    if request.method == 'POST':
        stress_score = request.POST.get('stress_score')
        mood = request.POST.get('mood')
        hours_worked = request.POST.get('hours_worked')
        break_time = request.POST.get('break_time')
        mental_fatigue = request.POST.get('mental_fatigue', 0)
        
        from django.utils import timezone
        today = timezone.now().date()
        
        try:
            WellnessLog.objects.update_or_create(
                employee=employee,
                date=today,
                defaults={
                    'stress_score': stress_score,
                    'mood': mood,
                    'hours_worked': hours_worked,
                    'break_time': break_time,
                    'mental_fatigue': mental_fatigue
                }
            )
            messages.success(request, "Wellness data updated successfully!")
            return redirect('employee_dashboard')
        except Exception as e:
            messages.error(request, f"Error logging wellness: {e}")
            
    return render(request, 'wellness/log.html', {'employee': employee})
