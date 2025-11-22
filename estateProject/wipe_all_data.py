"""
COMPLETE DATA WIPE - Start Fresh
Deletes all operational data while keeping company structure intact
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'estateProject.settings')
django.setup()

from estateApp.models import (
    Company, CustomUser, ClientUser, MarketerUser,
    Estate, PlotSize, PlotNumber, PlotAllocation, 
    Transaction, Message, Notification,
    PlotSizeUnits, ProgressStatus,
    MarketerPerformanceRecord, PromotionalOffer,
    PaymentRecord, Payment, Invoice
)
from adminSupport.models import (
    BirthdayTemplate, AutoSpecialSetting,
    MessagingSettings, OutboundMessage, OutboundMessageItem
)
from django.db import transaction as db_transaction

print("=" * 80)
print(" COMPLETE DATA WIPE - STARTING FRESH")
print("=" * 80)
print()
print("⚠️  WARNING: This will delete ALL operational data including:")
print("   - All users (clients, marketers, staff)")
print("   - All estates and properties")
print("   - All transactions and payments")
print("   - All messages and notifications")
print("   - All plot allocations and sizes")
print("   - All settings and configurations")
print()
print("✅ What will be PRESERVED:")
print("   - Company structures (Company A & Company B)")
print("   - Database schema and migrations")
print()

response = input("Type 'DELETE ALL DATA' to proceed: ")

if response != 'DELETE ALL DATA':
    print("\n❌ Aborted. No data was deleted.")
    exit(0)

print("\n🔥 Starting data wipe...")
print()

try:
    with db_transaction.atomic():
        # Get companies before deletion
        companies = Company.objects.all()
        company_info = [(c.id, c.company_name, c.email) for c in companies]
        
        # Delete in correct order to respect foreign keys
        
        print("📧 Deleting messages...")
        msg_count = Message.objects.all().count()
        Message.objects.all().delete()
        print(f"   ✅ Deleted {msg_count} messages")
        
        print("🔔 Deleting notifications...")
        notif_count = Notification.objects.all().count()
        Notification.objects.all().delete()
        print(f"   ✅ Deleted {notif_count} notifications")
        
        print("💰 Deleting transactions...")
        trans_count = Transaction.objects.all().count()
        Transaction.objects.all().delete()
        print(f"   ✅ Deleted {trans_count} transactions")
        
        print("📊 Deleting marketer performance records...")
        perf_count = MarketerPerformanceRecord.objects.all().count()
        MarketerPerformanceRecord.objects.all().delete()
        print(f"   ✅ Deleted {perf_count} performance records")
        
        print("🏘️ Deleting plot allocations...")
        alloc_count = PlotAllocation.objects.all().count()
        PlotAllocation.objects.all().delete()
        print(f"   ✅ Deleted {alloc_count} plot allocations")
        
        print("📐 Deleting plot size units...")
        psu_count = PlotSizeUnits.objects.all().count()
        PlotSizeUnits.objects.all().delete()
        print(f"   ✅ Deleted {psu_count} plot size units")
        
        print("📏 Deleting plot sizes...")
        ps_count = PlotSize.objects.all().count()
        PlotSize.objects.all().delete()
        print(f"   ✅ Deleted {ps_count} plot sizes")
        
        print("🔢 Deleting plot numbers...")
        pn_count = PlotNumber.objects.all().count()
        PlotNumber.objects.all().delete()
        print(f"   ✅ Deleted {pn_count} plot numbers")
        
        print("📈 Deleting estate progress status...")
        eps_count = ProgressStatus.objects.all().count()
        ProgressStatus.objects.all().delete()
        print(f"   ✅ Deleted {eps_count} progress updates")
        
        print("🏡 Deleting estates...")
        estate_count = Estate.objects.all().count()
        Estate.objects.all().delete()
        print(f"   ✅ Deleted {estate_count} estates")
        
        print("💳 Deleting payments and invoices...")
        pay_count = Payment.objects.all().count()
        Payment.objects.all().delete()
        inv_count = Invoice.objects.all().count()
        Invoice.objects.all().delete()
        pr_count = PaymentRecord.objects.all().count()
        PaymentRecord.objects.all().delete()
        print(f"   ✅ Deleted {pay_count} payments, {inv_count} invoices, {pr_count} payment records")
        
        print("🎁 Deleting promotional offers...")
        promo_count = PromotionalOffer.objects.all().count()
        PromotionalOffer.objects.all().delete()
        print(f"   ✅ Deleted {promo_count} promos")
        
        print("⚙️ Deleting messaging settings...")
        OutboundMessage.objects.all().delete()
        OutboundMessageItem.objects.all().delete()
        MessagingSettings.objects.all().delete()
        BirthdayTemplate.objects.all().delete()
        AutoSpecialSetting.objects.all().delete()
        print(f"   ✅ Deleted all messaging settings")
        
        print("👥 Deleting ALL USERS (clients, marketers, staff, admins)...")
        user_count = CustomUser.objects.all().count()
        CustomUser.objects.all().delete()
        print(f"   ✅ Deleted {user_count} users")
        
        print("🏢 Deleting ALL COMPANIES...")
        company_count = Company.objects.all().count()
        Company.objects.all().delete()
        print(f"   ✅ Deleted {company_count} companies")
        
        print()
        print("=" * 80)
        print(" DATA WIPE COMPLETE")
        print("=" * 80)
        print()
        print("📊 SUMMARY:")
        print(f"   Users deleted: {user_count}")
        print(f"   Estates deleted: {estate_count}")
        print(f"   Transactions deleted: {trans_count}")
        print(f"   Messages deleted: {msg_count}")
        print(f"   Notifications deleted: {notif_count}")
        print(f"   Plot allocations deleted: {alloc_count}")
        print(f"   Companies deleted: {company_count}")
        print()
        print("✅ DATABASE IS NOW CLEAN")
        print()
        print("🎯 NEXT STEPS:")
        print("   1. Create Company A (fresh company)")
        print("   2. Register admin user with proper company_profile")
        print("   3. Build data step-by-step with proper tenant isolation")
        print("   4. Test thoroughly after each addition")
        print()
        print("📝 Companies that were deleted:")
        for comp_id, comp_name, comp_email in company_info:
            print(f"   - {comp_name} ({comp_email}) - ID: {comp_id}")
        print()
        print("=" * 80)

except Exception as e:
    print(f"\n❌ ERROR during data wipe: {e}")
    print("Transaction rolled back - no data was deleted")
    import traceback
    traceback.print_exc()
