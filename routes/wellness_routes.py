from django.urls import path
from modules.wellness import views

urlpatterns = [
    path('log/', views.wellness_log, name='wellness_log'),
]
