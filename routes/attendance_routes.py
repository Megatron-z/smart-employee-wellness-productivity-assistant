from django.urls import path
from modules.attendance import views

urlpatterns = [
    path('mark/', views.mark_attendance_page, name='mark_attendance'),
    path('api/verify/', views.verify_attendance_api, name='verify_attendance_api'),
    path('history/', views.attendance_history, name='attendance_history'),
    path('attendance_print/',views.attendance_print,name='attendance_print'),
]
