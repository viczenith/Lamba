"""
Fix orphaned users - assign them to a company
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company, CustomUser

def fix_orphaned_users():
    print("\n🔧 Fixing orphaned users...")
    print("=" * 80)
    
    # Get orphaned users
    orphaned_users = CustomUser.objects.filter(company_profile__isnull=True)
    
    if not orphaned_users.exists():
        print("✅ No orphaned users found. All users have company assignments.")
        return
    
    # Get first company as default
    default_company = Company.objects.first()
    
    if not default_company:
        print("❌ No companies found in database. Cannot assign users.")
        return
    
    print(f"📍 Default company: {default_company.company_name}")
    print(f"👥 Found {orphaned_users.count()} orphaned users\n")
    
    for user in orphaned_users:
        print(f"  Fixing: {user.full_name} ({user.email}) - Role: {user.role}")
        user.company_profile = default_company
        user.save(update_fields=['company_profile'])
    
    print(f"\n✅ Successfully assigned {orphaned_users.count()} users to {default_company.company_name}")
    print("=" * 80)

if __name__ == '__main__':
    fix_orphaned_users()
