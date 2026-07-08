from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from database.models import Employee, LeaveRequest
from datetime import datetime, date, timedelta



@login_required(login_url='login')
def apply_leave(request):
    employee = getattr(request.user, 'employee_profile', None)

    if not employee:
        messages.error(request, "Employee profile not found.")
        return redirect('login')

    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        reason = request.POST.get('reason')

        try:
            #  1. Convert to date objects
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

            today = date.today()
            max_date = today + timedelta(days=365)  # 1 year limit

            #  Too far future (e.g., 2030)
            if start_date > max_date or end_date > max_date:
                messages.error(request, "Leave cannot be applied too far in future.")
                return redirect('apply_leave')

            #  Past date
            if start_date < today:
                messages.error(request, "Start date cannot be in the past.")
                return redirect('apply_leave')

            #  End before start
            if end_date < start_date:
                messages.error(request, "End date must be after start date.")
                return redirect('apply_leave')

            #  Too long leave (optional: 30 days)
            if (end_date - start_date).days > 30:
                messages.error(request, "Leave duration too long.")
                return redirect('apply_leave')

            #  Overlapping leave check
            overlap = LeaveRequest.objects.filter(
                employee=employee,
                start_date__lte=end_date,
                end_date__gte=start_date
            ).exists()

            if overlap:
                messages.error(request, "You already have leave in this period.")
                return redirect('apply_leave')

            #  2. Save leave
            LeaveRequest.objects.create(
                employee=employee,
                start_date=start_date,
                end_date=end_date,
                reason=reason
            )

            messages.success(request, "Leave request submitted successfully!")
            return redirect('employee_dashboard')

        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('apply_leave')

        except Exception as e:
            messages.error(request, f"Error submitting leave: {e}")
            return redirect('apply_leave')

    return render(request, 'leave/apply.html', {'employee': employee})


@login_required(login_url='login')
def manage_leaves(request):
    """HR/Admin view to approve/reject leaves."""
    if request.user.role not in ['admin', 'hr']:
        messages.error(request, "Access denied.")
        return redirect('employee_dashboard')
        
    if request.user.role == 'admin':
        # Admin can see all pending leaves
        pending_leaves = LeaveRequest.objects.filter(status='pending').select_related('employee__user')
    else:
        # HR can only see pending leaves for regular employees
        pending_leaves = LeaveRequest.objects.filter(
            status='pending', 
            employee__user__role='employee'
        ).select_related('employee__user')
        
    return render(request, 'leave/manage.html', {'pending_leaves': pending_leaves})

@login_required(login_url='login')
def approve_leave(request, leave_id, status):
    """API or View to update leave status."""
    if request.user.role not in ['admin', 'hr']:
        return redirect('login')
        
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    
    # 1. Prevent self-approval
    if leave.employee.user == request.user:
        messages.error(request, "You cannot approve or reject your own leave request.")
        return redirect('manage_leaves')
    
    # 2. Policy Check: HR can only approve regular employee leaves
    # HR leaves and Admin leaves must be approved by an Admin (preferably a superuser or another admin)
    if request.user.role == 'hr' and leave.employee.user.role != 'employee':
        messages.error(request, "Access denied. Only Admin can approve management leaves.")
        return redirect('manage_leaves')
        
    if status in ['approved', 'rejected']:
        leave.status = status
        leave.save()
        messages.success(request, f"Leave {status} for {leave.employee.name}.")
        
    return redirect('manage_leaves')

@login_required(login_url='login')
def leave_tracker(request):
    """Employee view to see their own leave requests."""
    employee = getattr(request.user, 'employee_profile', None)
    if not employee:
        return redirect('login')
        
    leaves = LeaveRequest.objects.filter(employee=employee).order_by('-created_at')
    return render(request, 'leave/tracker.html', {'leaves': leaves, 'employee': employee})




@login_required(login_url='login')
def all_leave_history(request):

    if request.user.role not in ['admin', 'hr']:
        messages.error(request, "Access denied.")
        return redirect('employee_dashboard')

    leaves = LeaveRequest.objects.select_related('employee__user')

    selected_date = request.GET.get('date')

    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()

            leaves = leaves.filter(
                start_date__lte=selected_date,
                end_date__gte=selected_date
            )
        except ValueError:
            messages.error(request, "Invalid date format")

    #  ROLE BASED FILTERING
    if request.user.role == 'admin':
        employee_leaves = leaves.filter(employee__user__role='employee')
        hr_leaves = leaves.filter(employee__user__role='hr')
    else:
        employee_leaves = leaves.filter(employee__user__role='employee')
        hr_leaves = None

    return render(request, 'leave/all_leave_history.html', {
        'employee_leaves': employee_leaves,
        'hr_leaves': hr_leaves,
        'selected_date': selected_date
    })

