"""
Script to convert existing CustomUser to MarketerUser for testing
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import CustomUser, MarketerUser, ClientUser

def fix_existing_user(email):
    """Convert existing CustomUser to MarketerUser/ClientUser"""
    try:
        # Get the existing user
        user = CustomUser.objects.get(email=email)
        print(f"\n=== Found User ===")
        print(f"Email: {user.email}")
        print(f"Type: {type(user).__name__}")
        print(f"ID: {user.pk}")
        print(f"Role: {user.role}")
        print(f"Company: {user.company_profile}")
        
        # Check if already proper type
        is_marketer = MarketerUser.objects.filter(pk=user.pk).exists()
        is_client = ClientUser.objects.filter(pk=user.pk).exists()
        
        print(f"\nIs MarketerUser: {is_marketer}")
        print(f"Is ClientUser: {is_client}")
        
        if user.role == 'marketer' and not is_marketer:
            print("\n=== Converting to MarketerUser ===")
            # Store all user data
            user_data = {
                'email': user.email,
                'full_name': user.full_name,
                'address': user.address,
                'phone': user.phone,
                'date_of_birth': user.date_of_birth,
                'country': user.country,
                'password': user.password,
                'last_login': user.last_login,
                'is_superuser': user.is_superuser,
                'is_staff': user.is_staff,
                'is_active': user.is_active,
                'date_joined': user.date_joined,
                'date_registered': user.date_registered,
                'about': user.about,
                'job': user.job,
                'profile_image': user.profile_image,
                'company_profile': user.company_profile,
            }
            
            user_id = user.pk
            user.delete()
            
            # Create MarketerUser
            marketer = MarketerUser(
                id=user_id,
                **user_data
            )
            marketer.save()
            
            print(f"✓ Successfully converted to MarketerUser (ID: {marketer.pk})")
            
            # Verify
            check = MarketerUser.objects.filter(pk=user_id).first()
            print(f"✓ Verification: MarketerUser exists: {check is not None}")
            if check:
                print(f"  - Email: {check.email}")
                print(f"  - Company: {check.company_profile}")
            
        elif user.role == 'client' and not is_client:
            print("\n=== User is client but needs conversion ===")
            print("Note: ClientUser requires assigned_marketer field")
            
        else:
            print("\n✓ User is already the correct type!")
            
    except CustomUser.DoesNotExist:
        print(f"✗ User with email {email} not found")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    email = 'viczenithgodwin@gmail.com'
    fix_existing_user(email)
