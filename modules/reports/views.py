from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from database.models import Employee, WellnessLog, ProductivityLog, Payroll 
from modules.utils import calculate_wellness_score
  


@login_required(login_url='login')
def report_view(request, emp_id):
    employee = get_object_or_404(Employee, emp_id=emp_id)
    
    logs = employee.wellness_logs.all().order_by('-date')[:5]
    p_logs = ProductivityLog.objects.filter(employee=employee).order_by('-date')[:2]
    
    prod_trend = "Stable"
    if len(p_logs) >= 2:
        if p_logs[0].efficiency_score > p_logs[1].efficiency_score:
            prod_trend = "Improving"
        elif p_logs[0].efficiency_score < p_logs[1].efficiency_score:
            prod_trend = "Declining"
            
    context = {
        'employee': employee,
        'wellness_logs': logs,
        'payroll': getattr(employee, 'payroll', None),
        'prod_trend': prod_trend,
        'latest_productivity': p_logs[0].efficiency_score if p_logs else 75
    }
    
    return render(request, 'reports/view.html', context)



@login_required(login_url='login')
def print_all(request):
    context = {}

    def calculate_for_emp(emp):
        w_log = WellnessLog.objects.filter(employee=emp).order_by('-date').first()
        p_log = ProductivityLog.objects.filter(employee=emp).order_by('-date').first()
      

        payroll = Payroll.objects.filter(employee=emp).order_by('-id').first()

        stress = w_log.stress_score if w_log else 5
        hours = w_log.hours_worked if w_log else 8
        break_freq = (w_log.break_time / max(hours, 1)) if w_log else 0.125
        prod = p_log.efficiency_score if p_log and p_log.efficiency_score else 70

        salary = round(float(payroll.total_salary), 2) if payroll and payroll.total_salary is not None else 0.0

        score, status = calculate_wellness_score(prod, stress, hours, salary, break_freq)

        return score, status, salary

  
    if request.user.role in ['admin', 'hr']:
        employees = Employee.objects.filter(user__role='employee')

        employee_data = []
        for emp in employees:
            score, status, salary = calculate_for_emp(emp)

            employee_data.append({
                'emp': emp,
                'score': score,
                'status': status,
                'salary': salary
            })

        context['employee_data'] = employee_data

    
    if request.user.role == 'admin':
        hrs = Employee.objects.filter(user__role='hr')

        hr_data = []
        for hr in hrs:
            score, status, salary = calculate_for_emp(hr)

            hr_data.append({
                'emp': hr,
                'score': score,
                'status': status,
                'salary': salary
            })

        context['hr_data'] = hr_data

    return render(request, 'reports/print_all.html', context)



