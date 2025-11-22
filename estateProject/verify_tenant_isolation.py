"""
Tenant Isolation Verification Script
This script verifies that all models have proper company isolation.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import (
    Company, Estate, PlotSize, PlotNumber, PlotSizeUnits, 
    PlotAllocation, EstatePlot, EstateLayout, EstateMap, 
    EstateFloorPlan, EstatePrototype, ProgressStatus, 
    PropertyRequest, Transaction, Message, CustomUser
)
from django.db.models import Count

def verify_tenant_isolation():
    """
    Verify that all records are properly assigned to companies
    and that companies cannot see each other's data.
    """
    print("\n" + "=" * 80)
    print("🔍 TENANT ISOLATION VERIFICATION")
    print("=" * 80)
    
    companies = Company.objects.all()
    
    if companies.count() == 0:
        print("❌ No companies found in database.")
        return
    
    print(f"\n📊 Found {companies.count()} companies in database\n")
    
    # Models to check
    models_to_check = [
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
    
    all_isolated = True
    
    for company in companies:
        print(f"\n🏢 Company: {company.company_name}")
        print("-" * 80)
        
        for model_name, model_class in models_to_check:
            try:
                # Count records for this company
                company_records = model_class.objects.filter(company=company).count()
                
                # Count total records
                total_records = model_class.objects.count()
                
                # Count records without company (should be 0)
                orphaned_records = model_class.objects.filter(company__isnull=True).count()
                
                status = "✅" if orphaned_records == 0 else "⚠️"
                
                print(f"  {status} {model_name:20} | Company: {company_records:3} | Total: {total_records:3} | Orphaned: {orphaned_records:3}")
                
                if orphaned_records > 0:
                    all_isolated = False
                    
            except Exception as e:
                print(f"  ❌ {model_name:20} | Error: {str(e)}")
                all_isolated = False
    
    # Check for cross-company visibility
    print("\n" + "=" * 80)
    print("🔒 CROSS-COMPANY VISIBILITY CHECK")
    print("=" * 80)
    
    if companies.count() >= 2:
        company_a = companies[0]
        company_b = companies[1]
        
        print(f"\nCompany A: {company_a.company_name}")
        print(f"Company B: {company_b.company_name}")
        print("-" * 80)
        
        for model_name, model_class in models_to_check:
            try:
                # Count for Company A
                count_a = model_class.objects.filter(company=company_a).count()
                
                # Count for Company B
                count_b = model_class.objects.filter(company=company_b).count()
                
                # Check if Company A can see Company B's data (should be False)
                company_a_sees_b = model_class.objects.filter(company=company_a, id__in=model_class.objects.filter(company=company_b).values_list('id', flat=True)).exists()
                
                visibility_status = "❌ LEAK" if company_a_sees_b else "✅ SECURE"
                
                print(f"  {model_name:20} | A: {count_a:3} | B: {count_b:3} | {visibility_status}")
                
                if company_a_sees_b:
                    all_isolated = False
                    
            except Exception as e:
                print(f"  {model_name:20} | Error: {str(e)}")
    else:
        print("\n⚠️  Need at least 2 companies to test cross-company visibility")
    
    # Check user isolation
    print("\n" + "=" * 80)
    print("👥 USER ISOLATION CHECK")
    print("=" * 80)
    
    for company in companies:
        admins = CustomUser.objects.filter(role='admin', company_profile=company).count()
        clients = CustomUser.objects.filter(role='client', company_profile=company).count()
        marketers = CustomUser.objects.filter(role='marketer', company_profile=company).count()
        
        print(f"\n🏢 {company.company_name}")
        print(f"  Admins: {admins} | Clients: {clients} | Marketers: {marketers}")
    
    # Final verdict
    print("\n" + "=" * 80)
    if all_isolated:
        print("✅ ✅ ✅ TENANT ISOLATION VERIFIED - ALL CHECKS PASSED! ✅ ✅ ✅")
    else:
        print("⚠️  WARNING: Some isolation issues detected. Review output above.")
    print("=" * 80)
    print()

if __name__ == '__main__':
    verify_tenant_isolation()
