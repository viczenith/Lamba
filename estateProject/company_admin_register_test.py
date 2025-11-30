"""
Company-scoped admin registration endpoint
Allows company admins to register new admins/support users
ONLY for their company - no sharing between companies
"""
import os
import sys
import json
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from estateApp.models import Company, CustomUser
import string
import random


def generate_password(name):
    """Generate a secure password based on user name"""
    nameParts = name.strip().split()
    basePassword = '_'.join(nameParts).lower()
    randomNum = random.randint(100, 999)
    return f"{basePassword}{randomNum}"


@login_required
@require_http_methods(["POST"])
def company_admin_register(request, company_id):
    """
    Company-scoped admin registration endpoint
    
    SECURITY:
    - User must be authenticated and belong to the company
    - Only admins can create other admins/support users  
    - Admin and support users are COMPANY-SCOPED ONLY
    - Cannot be shared between companies
    - Returns JSON for AJAX submission (NO redirect)
    """
    try:
        # Get company
        company = Company.objects.get(id=company_id)
        
        # SECURITY: Verify user belongs to this company
        if request.user.company_profile != company:
            return JsonResponse({
                'success': False,
                'error': 'Access denied. You can only manage your own company.'
            }, status=403)
        
        # SECURITY: Verify user is admin
        if request.user.role != 'admin':
            return JsonResponse({
                'success': False,
                'error': 'Only admins can register new users.'
            }, status=403)
        
        # Extract form data
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        date_of_birth = request.POST.get('date_of_birth', '').strip()
        address = request.POST.get('address', '').strip()
        country = request.POST.get('country', '').strip()
        role = request.POST.get('role', '').strip()
        password = request.POST.get('password', '').strip()
        
        # Validation
        if not all([name, email, role]):
            return JsonResponse({
                'success': False,
                'error': 'Name, email, and role are required.'
            })
        
        # SECURITY: Only allow admin and support roles for company-scoped users
        if role not in ['admin', 'support']:
            return JsonResponse({
                'success': False,
                'error': f'Invalid role. Only admin and support are allowed for company users.'
            })
        
        # Check if email already exists
        if CustomUser.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'error': f'Email {email} is already registered.'
            })
        
        # Generate password if not provided
        if not password:
            password = generate_password(name)
        
        # Create user within transaction
        with transaction.atomic():
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                full_name=name,
                role=role,
                phone=phone or None,
                date_of_birth=date_of_birth or None,
                address=address or None,
                country=country or None,
                company_profile=company,  # COMPANY-SCOPED
                is_active=True
            )
            
            # Verify user was created
            if not user:
                raise Exception("Failed to create user")
        
        return JsonResponse({
            'success': True,
            'message': f'✅ {role.capitalize()} {name} registered successfully for {company.company_name}!',
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'company': company.company_name
            }
        })
    
    except Company.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Company not found.'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error: {str(e)}'
        })
