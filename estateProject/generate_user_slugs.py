"""
Generate slugs for all existing users
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import CustomUser

def generate_slugs():
    """Generate slugs for all users that don't have one"""
    users = CustomUser.objects.filter(slug__isnull=True) | CustomUser.objects.filter(slug='')
    count = 0
    
    for user in users:
        user.save()  # The save method will auto-generate the slug
        print(f"✓ Generated slug for {user.full_name}: {user.slug}")
        count += 1
    
    print(f"\n✅ Successfully generated {count} slugs!")
    print("\nExamples:")
    for user in CustomUser.objects.all()[:5]:
        role_name = user.role.upper() if user.role else "NONE"
        print(f"   {user.full_name} ({role_name}): /{user.slug}/")

if __name__ == '____main__':
    generate_slugs()
