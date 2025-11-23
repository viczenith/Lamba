import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import CustomUser

print("\n=== ALL USERS DEBUG ===\n")
users = CustomUser.objects.all()
for user in users:
    print(f"Email: {user.email}")
    print(f"  is_system_admin: {getattr(user, 'is_system_admin', 'FIELD_NOT_EXISTS')}")
    print(f"  role: {getattr(user, 'role', 'NO_ROLE')}")
    print(f"  admin_level: {getattr(user, 'admin_level', 'NO_ADMIN_LEVEL')}")
    print(f"  company_profile: {getattr(user, 'company_profile', None)}")
    print()

