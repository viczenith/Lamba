"""
Reassign all existing data to Company A (Lamba Real Estate - estate@gmail.com)
This will restore all the lost data to the correct company.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import (
    Company, CustomUser, Estate, PlotSize, PlotNumber, PlotSizeUnits, 
    PlotAllocation, EstatePlot, EstateLayout, EstateMap, 
    EstateFloorPlan, EstatePrototype, ProgressStatus, 
    PropertyRequest, Transaction, Message
)
from django.db import transaction

def reassign_all_to_company_a():
    print("\n🔄 REASSIGNING ALL DATA TO COMPANY A")
    print("=" * 80)
    
    # Find Company A admin (estate@gmail.com)
    try:
        company_a_admin = CustomUser.objects.get(email='estate@gmail.com')
        company_a = company_a_admin.company_profile
        
        if not company_a:
            print("❌ Company A admin found but has no company_profile!")
            return
            
        print(f"✅ Found Company A: {company_a.company_name}")
        print(f"   Admin: {company_a_admin.full_name} ({company_a_admin.email})")
        print()
        
    except CustomUser.DoesNotExist:
        print("❌ Company A admin (estate@gmail.com) not found!")
        return
    
    with transaction.atomic():
        # Reassign all models to Company A
        models_to_reassign = [
            ('Estate', Estate),
            ('PlotSize', PlotSize),
            ('PlotNumber', PlotNumber),
            ('PlotSizeUnits', PlotSizeUnits),
            ('PlotAllocation', PlotAllocation),
            ('EstatePlot', EstatePlot),
            ('EstateLayout', EstateLayout),
            ('EstateMap', EstateMap),
            ('EstateFloorPlan', EstateFloorPlan),
            ('EstatePrototype', EstatePrototype),
            ('ProgressStatus', ProgressStatus),
            ('PropertyRequest', PropertyRequest),
            ('Transaction', Transaction),
            ('Message', Message),
        ]
        
        for model_name, model_class in models_to_reassign:
            # Update all records to Company A
            updated = model_class.objects.all().update(company=company_a)
            print(f"✅ {model_name:20} → {updated:4} records assigned to Company A")
        
        # Also reassign all users (except the other company's admin if exists)
        # Keep Lamba Properties admin separate
        lamba_properties_admin = CustomUser.objects.filter(email='akorvikkyy@gmail.com').first()
        
        if lamba_properties_admin and lamba_properties_admin.company_profile:
            # Reassign all users EXCEPT Lamba Properties users
            lamba_properties_company = lamba_properties_admin.company_profile
            
            users_to_reassign = CustomUser.objects.exclude(company_profile=lamba_properties_company)
            user_count = users_to_reassign.count()
            users_to_reassign.update(company_profile=company_a)
            print(f"✅ {'CustomUser':20} → {user_count:4} users assigned to Company A")
            
            print(f"\n📋 Company A ({company_a.company_name}) now has:")
            print(f"   Admins:    {CustomUser.objects.filter(role='admin', company_profile=company_a).count()}")
            print(f"   Clients:   {CustomUser.objects.filter(role='client', company_profile=company_a).count()}")
            print(f"   Marketers: {CustomUser.objects.filter(role='marketer', company_profile=company_a).count()}")
            print(f"   Support:   {CustomUser.objects.filter(role='support', company_profile=company_a).count()}")
        else:
            # No Lamba Properties admin, reassign all users
            user_count = CustomUser.objects.all().update(company_profile=company_a)
            print(f"✅ {'CustomUser':20} → {user_count:4} users assigned to Company A")
    
    print("\n" + "=" * 80)
    print("✅ ALL DATA SUCCESSFULLY REASSIGNED TO COMPANY A!")
    print("=" * 80)

if __name__ == '__main__':
    reassign_all_to_company_a()
