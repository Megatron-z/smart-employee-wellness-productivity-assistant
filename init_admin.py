import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_employee_ai.settings')
django.setup()

from database.models import User, SystemConfig

# 1. Create Superuser
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin', role='admin', is_approved=True)
    print("Superuser 'admin' created successfully.")
else:
    # Ensure existing admin is approved and has the correct role
    admin = User.objects.get(username='admin')
    admin.role = 'admin'
    admin.is_approved = True
    admin.save()
    print("Superuser 'admin' updated to approved status.")

# 2. Initialize System Config
if not SystemConfig.objects.exists():
    SystemConfig.objects.create()
    print("Default System Configuration created.")
else:
    print("System Configuration already exists.")
