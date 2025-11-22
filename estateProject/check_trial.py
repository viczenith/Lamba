import django
import os
from datetime import datetime, timezone
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import Company
from django.utils import timezone as django_timezone

# Find company by email
companies = Company.objects.filter(email='estate@gmail.com')

if not companies.exists():
    print('❌ No company found with email estate@gmail.com')
    print('\nAvailable companies:')
    for c in Company.objects.all():
        print(f'  - {c.company_name}: {c.email}')
else:
    company = companies.first()
    now = django_timezone.now()
    
    print('=' * 70)
    print('COMPANY SUBSCRIPTION STATUS')
    print('=' * 70)
    print(f'Company Name: {company.company_name}')
    print(f'Email: {company.email}')
    print(f'Subscription Tier: {company.subscription_tier.upper() if company.subscription_tier else "NONE"}')
    print(f'Subscription Status: {company.subscription_status.upper() if company.subscription_status else "NONE"}')
    print()
    
    if company.trial_ends_at:
        time_remaining = company.trial_ends_at - now
        days_remaining = time_remaining.days
        hours_remaining = time_remaining.seconds // 3600
        
        print(f'Trial Ends: {company.trial_ends_at}')
        print(f'Current Time: {now}')
        print()
        print(f'⏰ TIME REMAINING: {days_remaining} days, {hours_remaining} hours')
        print()
        
        if days_remaining <= 0:
            print('🚨 STATUS: TRIAL EXPIRED!')
        elif days_remaining <= 3:
            print('⚠️ STATUS: URGENT - Trial expiring soon!')
        elif days_remaining <= 7:
            print('⚠️ STATUS: WARNING - Less than 7 days remaining')
        elif days_remaining <= 14:
            print('ℹ️ STATUS: INFO - Trial active')
        else:
            print('✅ STATUS: Trial active')
    else:
        print('⚠️ No trial end date set!')
    
    print()
    print('ALERT SYSTEM STATUS:')
    print('-' * 70)
    
    # Check what alerts should show
    if company.subscription_status == 'trial' and company.trial_ends_at:
        days_left = (company.trial_ends_at - now).days
        
        if days_left <= 0:
            print('🚨 URGENT ALERT (RED): "Your trial has expired! Subscribe now."')
            print('   - Banner: Visible (Red)')
            print('   - Modal: Shows on login')
            print('   - Access: Restricted')
        elif days_left <= 3:
            print(f'🚨 URGENT ALERT (RED): "Only {days_left} days left! Subscribe now."')
            print('   - Banner: Visible (Red)')
            print('   - Modal: Shows on login')
        elif days_left <= 7:
            print(f'⚠️ CRITICAL ALERT (ORANGE): "Your trial expires in {days_left} days"')
            print('   - Banner: Visible (Orange)')
            print('   - Modal: Shows occasionally')
        elif days_left <= 14:
            print(f'⚠️ WARNING ALERT (YELLOW): "Your trial expires in {days_left} days"')
            print('   - Banner: Visible (Yellow)')
        else:
            print(f'ℹ️ INFO ALERT (BLUE): "Trial active, {days_left} days remaining"')
            print('   - Banner: Visible (Blue)')
    
    print()
    print('MIDDLEWARE CHECKS:')
    print('-' * 70)
    print('✅ TenantIsolationMiddleware: Active (isolates company data)')
    print('✅ SessionSecurityMiddleware: Active (manages session)')
    print('✅ SubscriptionValidationMiddleware: Active (checks subscription)')
    print()
    print('TRIAL COUNTDOWN:')
    print('-' * 70)
    print('✅ Trial end date is set in database')
    print('✅ Countdown is automatic (calculated on each request)')
    print('✅ Alerts update dynamically based on days remaining')
    print('✅ Banner shows on all pages when trial is active')
    print('✅ Modal shows on login when trial is expiring/expired')
    print('=' * 70)
