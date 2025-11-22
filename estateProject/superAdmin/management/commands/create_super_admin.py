"""
Management command to create a super admin user
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from superAdmin.models import SuperAdminUser

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a super admin user for platform management'
    
    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Super admin email')
        parser.add_argument('--password', type=str, help='Super admin password')
        parser.add_argument('--full-name', type=str, help='Super admin full name')
        parser.add_argument('--level', type=str, default='super', 
                          choices=['super', 'billing', 'support', 'analytics'],
                          help='Admin level')
    
    def handle(self, *args, **options):
        email = options.get('email')
        password = options.get('password')
        full_name = options.get('full_name')
        level = options.get('level')
        
        if not email:
            email = input('Enter email: ')
        
        if not password:
            password = input('Enter password: ')
        
        if not full_name:
            full_name = input('Enter full name: ')
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'User with email {email} already exists'))
            return
        
        # Create user
        user = User.objects.create_user(
            email=email,
            password=password,
            full_name=full_name,
            role='admin',
            is_staff=True,
            is_superuser=True,
        )
        
        # Create super admin profile
        super_admin = SuperAdminUser.objects.create(
            user=user,
            admin_level=level,
            can_access_all_companies=True,
            can_modify_subscriptions=True,
            can_view_financials=True,
            can_manage_users=True,
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created super admin: {email} with level {level}'
            )
        )
