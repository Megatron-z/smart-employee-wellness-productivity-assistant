from database.models import User, LeaveRequest

def global_context(request):
    """
    Provides global data for templates, such as pending approval counts.
    """
    if request.user.is_authenticated:
        pending_approvals = User.objects.filter(is_approved=False, role__in=['employee', 'hr'])
        if request.user.role == 'hr':
            pending_approvals = pending_approvals.filter(role='employee')

        pending_approvals = pending_approvals.count()
        pending_leaves = LeaveRequest.objects.filter(status='pending').count()
        return {
            'pending_approvals_count': pending_approvals,
            'pending_leaves_count': pending_leaves
        }
    return {
        'pending_approvals_count': 0,
        'pending_leaves_count': 0
    }
