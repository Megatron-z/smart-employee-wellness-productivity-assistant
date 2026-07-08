from django.urls import path
from modules.leave import views

urlpatterns = [
    path('apply/', views.apply_leave, name='apply_leave'),
    path('manage/', views.manage_leaves, name='manage_leaves'),
    path('approve/<int:leave_id>/<str:status>/', views.approve_leave, name='approve_leave'),
    path('tracker/', views.leave_tracker, name='leave_tracker'),
    path('all_leave_history/', views.all_leave_history, name='all_leave_history'),
]
