from django.contrib import admin
from django.urls import path, include
from routes import auth_routes
from modules.auth.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('auth/', include(auth_routes)),
    path('employee/', include('routes.employee_routes')),
    path('wellness/', include('routes.wellness_routes')),
    path('payroll/', include('routes.payroll_routes')),
    path('api/', include('routes.prediction_routes')),
    path('reports/', include('routes.report_routes')),
    path('attendance/', include('routes.attendance_routes')),
    path('leave/', include('routes.leave_routes')),
]
