from django.shortcuts import render, redirect
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from database.models import Employee, Payroll, Attendance, LeaveRequest 
import calendar
from datetime import date
from django.utils.dateparse import parse_date
from datetime import datetime
from datetime import date  
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from database.models import Employee


@login_required(login_url='login')
def payroll_calc(request):
    if request.user.role not in ['admin', 'hr']:
        messages.error(request, "Access denied.")
        return redirect('employee_dashboard')
    
    if request.user.role == 'hr':
        # Exclude anyone in HR department or with HR role
        employees = Employee.objects.filter(
            ~Q(department__icontains='HR') & ~Q(user__role='hr')
        )
    else:
        employees = Employee.objects.all()
   


    today = date.today()
    context = {
        'employees': employees,
        'current_year': today.year,
        'current_month': f"{today.month:02d}",
    }

    if request.method == 'POST':
        emp_id = request.POST.get('emp_id')
        month_input = request.POST.get('month')

        try:
            basic = float(request.POST.get('basic', 0))
            hra_percent = float(request.POST.get('hra', 0))
            ta_percent = float(request.POST.get('ta', 0))
            da_percent = float(request.POST.get('da', 0))
            pf_percent = float(request.POST.get('pf', 0))

            if min(basic, hra_percent, ta_percent, da_percent, pf_percent) < 0:
                raise ValueError
            if max(hra_percent, ta_percent, da_percent, pf_percent) > 100:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, "Please enter valid salary amounts and percentages.")
            return render(request, 'payroll/calc.html', context)

        try:
            selected_date = datetime.strptime(month_input, "%Y-%m").date()

            # Block previous years
            if selected_date.year != today.year:
                messages.error(request, "Only current year payroll is allowed.")
                return render(request, 'payroll/calc.html', context)

            #  Block future months
            if selected_date.month > today.month:
                messages.error(request, "Future month payroll is not allowed.")
                return render(request, 'payroll/calc.html', context)


        except (TypeError, ValueError):
            messages.error(request, "Please select a valid payroll month.")
            return render(request, 'payroll/calc.html', context)

        month_date = selected_date.replace(day=1)
                
       
        
        try:
            employee = employees.get(emp_id=emp_id)

            ####
            # total working days in month
            total_days = calendar.monthrange(month_date.year, month_date.month)[1]

            # count absent days
            month_end = month_date.replace(day=total_days)

            absent_days = Attendance.objects.filter(
                employee=employee,
                date__month=month_date.month,
                date__year=month_date.year,
                is_valid=False
            ).count()
                    
            lop_input = request.POST.get('lop')

            if lop_input and lop_input.strip() != "":
                try:
                    lop_days = int(lop_input)
                    if lop_days < 0:
                        raise ValueError
                except ValueError:
                    messages.error(request, "Please enter a valid LOP day count.")
                    return render(request, 'payroll/calc.html', context)
            else:
                approved_leaves = LeaveRequest.objects.filter(
                    employee=employee,
                    status__iexact='Approved',
                    start_date__lte=month_end,
                    end_date__gte=month_date
                )

                lop_leave_days = 0
                for leave in approved_leaves:
                    overlap_start = max(leave.start_date, month_date)
                    overlap_end = min(leave.end_date, month_end)
                    lop_leave_days += (overlap_end - overlap_start).days + 1

                lop_days = absent_days + lop_leave_days   #  AUTO ONLY IF EMPTY
            
            if lop_days > total_days:
                messages.error(request, f"LOP days cannot exceed {total_days} for the selected month.")
                return render(request, 'payroll/calc.html', context)
            ####

            hra = basic * hra_percent / 100
            ta = basic * ta_percent / 100
            da = basic * da_percent / 100
            pf = basic * pf_percent / 100

            per_day_salary = basic / total_days

            lop_amount = lop_days * per_day_salary

            total_salary = basic + hra + ta + da - pf - lop_amount


            # Update or create payroll
            Payroll.objects.update_or_create(
                employee=employee,
                month=month_date,
                defaults={
                    'basic': basic,
                    'hra': hra,
                    'ta': ta,
                    'da': da,
                    'pf': pf,
                    'lop_days': lop_days,
                    'lop_amount': lop_amount,
                    'total_salary': total_salary
                }
            )
            messages.success(request, f"Payroll updated for {employee.name}. Total: {total_salary}")
            context.update({
                'last_employee': employee.emp_id,
                'last_month': month_date.strftime("%Y-%m"),
            })
            return render(request, 'payroll/calc.html', context)
        
        except Employee.DoesNotExist:
            messages.error(request, "Employee not found.")

    return render(request, 'payroll/calc.html', context)


#####

@login_required(login_url='login')
def get_employee_payroll(request, emp_id):
    try:
        employee = Employee.objects.get(emp_id=emp_id)
        payroll = employee.payrolls.order_by('-month').first()

        role = employee.user.role   # get role

        today = date.today()

        absent_days = Attendance.objects.filter(
            employee=employee,
            date__month=today.month,
            is_valid=False
        ).count()


        ##lop_days = absent_days + lop_leave_days
        lop_input = request.POST.get('lop')

        if lop_input and lop_input.strip() != "":
            lop_days = int(lop_input)   # manual value
        else:
            
            lop_leave_days = LeaveRequest.objects.filter(
                employee=employee,
                status__iexact='Approved'
            ).count()


            lop_days = absent_days + lop_leave_days   #  auto

        #  If payroll already exists → use saved values
        if payroll:
            basic = payroll.basic or 0
            data = {
                'basic': basic,
                'hra': round((payroll.hra / basic) * 100, 2) if basic else 0,
                'ta': round((payroll.ta / basic) * 100, 2) if basic else 0,
                'da': round((payroll.da / basic) * 100, 2) if basic else 0,
                'pf': round((payroll.pf / basic) * 100, 2) if basic else 0,
                'lop': lop_days
                
            }

        else:
            #  Default salary based on role
            if role == 'hr':
                data = {
                    'basic': 60000,
                    'hra': 25,
                    'ta': 8.33,
                    'da': 8.33,
                    'pf': 5,
                    'lop': lop_days
                }
            else:
                data = {
                    'basic': 30000,
                    'hra': 16.67,
                    'ta': 6.67,
                    'da': 6.67,
                    'pf': 3.33,
                    'lop': lop_days
                }

        return JsonResponse({'success': True, 'role': role, **data})

    except Employee.DoesNotExist:
        return JsonResponse({'success': False})
###



@login_required(login_url='login')
def view_payslip(request):
    """Personal view for employees to see their personal payroll details."""
    employee = getattr(request.user, 'employee_profile', None)
    
    if not employee:
        return redirect('login')
        
    payrolls = employee.payrolls.order_by('-month')  #  list
    
    return render(request, 'payroll/payslip.html', {'payrolls': payrolls, 'employee': employee})




@login_required(login_url='login')
def payroll_history(request):

    selected_month = request.GET.get('month')

    if selected_month:
        selected_date = parse_date(selected_month + "-01")
    else:
        selected_date = date.today()

    employee_data = []
    hr_data = []

    # EMPLOYEES
    employees = Employee.objects.filter(user__role='employee')

    for emp in employees:

       
        payroll = Payroll.objects.filter(
            employee=emp,
            month__month=selected_date.month,
            month__year=selected_date.year
        ).first()

        attendance = Attendance.objects.filter(
            employee=emp,
            date__month=selected_date.month,
            date__year=selected_date.year
        )
        if attendance.exists():
            # Real data
            days_worked = attendance.filter(is_valid=True).count()
            absent_days = attendance.filter(is_valid=False).count()

        else:
            # No attendance → use payroll LOP
            if payroll:
                total_days = 30
                absent_days = payroll.lop_days
                days_worked = total_days - payroll.lop_days
            else:
                days_worked = 0
                absent_days = 0
                

        if payroll:
            employee_data.append({
                'emp': emp,
                'days_worked': days_worked,
                'absent_days': absent_days,
                'basic_pay': payroll.basic,
                'hra': payroll.hra,
                'ta': payroll.ta,
                'da': payroll.da,
                'pf': payroll.pf,
                'total_salary': payroll.total_salary
            })

    # HR (ADMIN ONLY)
    if request.user.role == 'admin':

        hrs = Employee.objects.filter(user__role='hr')

        for emp in hrs:

            payroll = Payroll.objects.filter(
            employee=emp,
            month__month=selected_date.month,
            month__year=selected_date.year
        ).first()

            attendance = Attendance.objects.filter(
                employee=emp,
                date__month=selected_date.month,
                date__year=selected_date.year
            )
            
            days_worked = attendance.filter(is_valid=True).count()
            absent_days = attendance.filter(is_valid=False).count()

            if payroll:
                hr_data.append({
                    'emp': emp,
                    'days_worked': days_worked,
                    'absent_days': absent_days,
                    'basic_pay': payroll.basic,
                    'hra': payroll.hra,
                    'ta': payroll.ta,
                    'da': payroll.da,
                    'pf': payroll.pf,
                    'total_salary': payroll.total_salary
                })

    return render(request, 'payroll/payroll_history.html', {
        'employee_data': employee_data,
        'hr_data': hr_data,
        'selected_month': selected_date
    })


@login_required(login_url='login')
def payroll_preview(request, emp_id, month):

    employee = Employee.objects.get(emp_id=emp_id)

    selected_date = datetime.strptime(month, "%Y-%m").date()

    payroll = Payroll.objects.filter(
        employee=employee,
        month__month=selected_date.month,
        month__year=selected_date.year
    ).first()

    return render(request, 'payroll/payroll_preview.html', {
        'employee': employee,
        'payroll': payroll
    })
