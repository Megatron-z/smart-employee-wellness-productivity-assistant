from django.urls import path
from modules.reports import views

urlpatterns = [
    
    path('print_all/',views.print_all,name='print_all'),
    path('<str:emp_id>/', views.report_view, name='report_view'),
]
