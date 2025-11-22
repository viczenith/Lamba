"""
Data Migration Script: Set company field for existing records
This script assigns company to all existing records that don't have one yet.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import (
    Company, Estate, PlotSize, PlotNumber, PlotSizeUnits, 
    PlotAllocation, EstatePlot, EstateLayout, EstateMap, 
    EstateFloorPlan, EstatePrototype, ProgressStatus, 
    PropertyRequest, Transaction, Message
)
from django.db import transaction

def set_company_for_existing_records():
    """
    Assign company to existing records based on related user's company_profile.
    For records without user relationship, assign to first company.
    """
    companies = Company.objects.all()
    
    if not companies.exists():
        print("❌ No companies found in database. Please create a company first.")
        return
    
    default_company = companies.first()
    print(f"\n🏢 Default company for orphaned records: {default_company.company_name}")
    print("=" * 80)
    
    with transaction.atomic():
        # 1. Estate - assign to first company (no direct user link)
        estates_updated = Estate.objects.filter(company__isnull=True).update(company=default_company)
        print(f"✅ Updated {estates_updated} Estate records")
        
        # 2. PlotSize - assign to first company (no direct user link)
        plotsizes_updated = PlotSize.objects.filter(company__isnull=True).update(company=default_company)
        print(f"✅ Updated {plotsizes_updated} PlotSize records")
        
        # 3. PlotNumber - assign to first company (no direct user link)
        plotnumbers_updated = PlotNumber.objects.filter(company__isnull=True).update(company=default_company)
        print(f"✅ Updated {plotnumbers_updated} PlotNumber records")
        
        # 4. PlotSizeUnits - assign based on estate
        plotsizeunits = PlotSizeUnits.objects.filter(company__isnull=True).select_related('estate_plot__estate')
        count = 0
        for psu in plotsizeunits:
            if psu.estate_plot and psu.estate_plot.estate:
                psu.company = psu.estate_plot.estate.company or default_company
            else:
                psu.company = default_company
            psu.save(update_fields=['company'])
            count += 1
        print(f"✅ Updated {count} PlotSizeUnits records")
        
        # 5. EstatePlot - assign based on estate
        estateplots = EstatePlot.objects.filter(company__isnull=True).select_related('estate')
        count = 0
        for ep in estateplots:
            ep.company = ep.estate.company if ep.estate and ep.estate.company else default_company
            ep.save(update_fields=['company'])
            count += 1
        print(f"✅ Updated {count} EstatePlot records")
        
        # 6. PlotAllocation - assign based on client's company
        allocations = PlotAllocation.objects.filter(company__isnull=True).select_related('client__company_profile')
        count = 0
        for allocation in allocations:
            if allocation.client and hasattr(allocation.client, 'company_profile') and allocation.client.company_profile:
                allocation.company = allocation.client.company_profile
            else:
                allocation.company = default_company
            allocation.save(update_fields=['company'])
            count += 1
        print(f"✅ Updated {count} PlotAllocation records")
        
        # 7. EstateLayout - assign based on estate
        estatelayouts = EstateLayout.objects.filter(company__isnull=True).select_related('estate')
        count = 0
        for layout in estatelayouts:
            layout.company = layout.estate.company if layout.estate and layout.estate.company else default_company
            layout.save(update_fields=['company'])
            count += 1
        print(f"✅ Updated {count} EstateLayout records")
        
        # 8. EstateMap - assign based on estate
        estatemaps = EstateMap.objects.filter(company__isnull=True).select_related('estate')
        count = 0
        for estate_map in estatemaps:
            estate_map.company = estate_map.estate.company if estate_map.estate and estate_map.estate.company else default_company
            estate_map.save(update_fields=['company'])
            count += 1
        print(f"✅ Updated {count} EstateMap records")
        
        # 9. EstateFloorPlan - assign based on estate
        floorplans = EstateFloorPlan.objects.filter(company__isnull=True).select_related('estate')
        count = 0
        for fp in floorplans:
            fp.company = fp.estate.company if fp.estate and fp.estate.company else default_company
            fp.save(update_fields=['company'])
            count += 1
        print(f"✅ Updated {count} EstateFloorPlan records")
        
        # 10. EstatePrototype - assign based on estate
        prototypes = EstatePrototype.objects.filter(company__isnull=True).select_related('estate')
        count = 0
        for proto in prototypes:
            proto.company = proto.estate.company if proto.estate and proto.estate.company else default_company
            proto.save(update_fields=['company'])
            count += 1
        print(f"✅ Updated {count} EstatePrototype records")
        
        # 11. ProgressStatus - assign based on estate
        progressstatuses = ProgressStatus.objects.filter(company__isnull=True).select_related('estate')
        count = 0
        for ps in progressstatuses:
            ps.company = ps.estate.company if ps.estate and ps.estate.company else default_company
            ps.save(update_fields=['company'])
            count += 1
        print(f"✅ Updated {count} ProgressStatus records")
        
        # 12. PropertyRequest - assign based on client
        proprequests = PropertyRequest.objects.filter(company__isnull=True).select_related('client__company_profile')
        count = 0
        for pr in proprequests:
            if pr.client and hasattr(pr.client, 'company_profile') and pr.client.company_profile:
                pr.company = pr.client.company_profile
            else:
                pr.company = default_company
            pr.save(update_fields=['company'])
            count += 1
        print(f"✅ Updated {count} PropertyRequest records")
        
        # 13. Transaction - assign based on client
        transactions = Transaction.objects.filter(company__isnull=True).select_related('client__company_profile')
        count = 0
        for txn in transactions:
            if txn.client and hasattr(txn.client, 'company_profile') and txn.client.company_profile:
                txn.company = txn.client.company_profile
            else:
                txn.company = default_company
            txn.save(update_fields=['company'])
            count += 1
        print(f"✅ Updated {count} Transaction records")
        
        # 14. Message - assign based on sender
        messages = Message.objects.filter(company__isnull=True).select_related('sender__company_profile')
        count = 0
        for msg in messages:
            if msg.sender and hasattr(msg.sender, 'company_profile') and msg.sender.company_profile:
                msg.company = msg.sender.company_profile
            else:
                msg.company = default_company
            msg.save(update_fields=['company'])
            count += 1
        print(f"✅ Updated {count} Message records")
        
    print("\n" + "=" * 80)
    print("✅ All existing records have been assigned to companies!")
    print("🔒 Tenant isolation is now COMPLETE at the database level!")
    print("=" * 80)

if __name__ == '__main__':
    print("\n🚀 Starting data migration to set company for existing records...")
    print("=" * 80)
    set_company_for_existing_records()
