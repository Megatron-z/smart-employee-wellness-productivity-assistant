from django.urls import path
from modules.payroll import views

urlpatterns = [
    path('calc/', views.payroll_calc, name='payroll_calc'),
    path('get-payroll/<str:emp_id>/', views.get_employee_payroll, name='get_payroll'),
    path('payslip/', views.view_payslip, name='view_payslip'),
    path('payroll_history/', views.payroll_history, name='payroll_history'),
    path('preview/<str:emp_id>/<str:month>/', views.payroll_preview, name='payroll_preview'),

]
