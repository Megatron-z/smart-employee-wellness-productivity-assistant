from django.urls import path
from modules.employee import views

urlpatterns = [
    path('', views.employee_list, name='employee_list'),
    path('dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('add/', views.employee_add, name='employee_add'),
    path('pending-approvals/', views.pending_approvals, name='pending_approvals'),
    path('approve-user/<int:user_id>/', views.approve_user, name='approve_user'),
    path('reject-user/<int:user_id>/', views.reject_user, name='reject_user_registration'),
    path('system-config/', views.system_config, name='system_config'),
    path('edit/<str:emp_id>/', views.employee_edit, name='employee_edit'),
    path('delete/<str:emp_id>/', views.employee_delete, name='employee_delete'),
    path('management/dashboard/', views.management_dashboard, name='management_dashboard'),
    path('complete-onboarding/', views.complete_onboarding, name='complete_onboarding'),
]
