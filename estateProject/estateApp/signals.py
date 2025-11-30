from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from estateApp.views import PerformanceDataAPI
from .models import *
from django.core.exceptions import ValidationError
from django.utils import timezone

from .ws_utils import broadcast_user_notification
from DRF.shared_drf.push_service import send_chat_message_push, send_user_notification_push

@receiver(pre_save, sender=PlotAllocation)
def prevent_over_allocation(sender, instance, **kwargs):
    if kwargs.get('raw', False):
        return

    # Validate before saving
    if instance._state.adding:  # New allocation
        if instance.plot_size_unit.available_units <= 0:
            raise ValidationError(
                f"No available units left for {instance.plot_size.size}"
            )

@receiver(post_save, sender=PlotAllocation)
@receiver(post_delete, sender=PlotAllocation)
def update_unit_availability(sender, instance, **kwargs):
    if kwargs.get('raw', False):
        return

    # Update parent unit availability
    unit = instance.plot_size_unit
    unit.save()  # Triggers availability recalculation


# ========== Company User Profile Signals ==========

@receiver(post_save, sender=MarketerAffiliation)
def create_company_marketer_profile_on_affiliation(sender, instance, created, **kwargs):
    """
    When a marketer is affiliated with a company, create a CompanyMarketerProfile
    with a unique company-specific ID and UID.
    """
    if kwargs.get('raw', False):
        return
    
    if created:
        try:
            from django.db.models import Max
            from django.db import transaction as db_transaction
            
            # Get the marketer and company
            marketer = instance.marketer
            company = instance.company
            
            # Check if profile already exists
            if CompanyMarketerProfile.objects.filter(marketer=marketer, company=company).exists():
                return
            
            # Generate company-specific ID for this marketer in this company
            with db_transaction.atomic():
                maxv = CompanyMarketerProfile.objects.filter(
                    company=company
                ).aggregate(maxv=Max('company_marketer_id'))
                next_id = (maxv.get('maxv') or 0) + 1
                
                # Get company prefix
                try:
                    prefix = company._company_prefix()
                except Exception:
                    prefix = (company.company_name or 'CMP')[:3].upper()
                
                # Generate UID
                base_uid = f"{prefix}MKT{next_id:03d}"
                
                # Ensure uniqueness
                if CompanyMarketerProfile.objects.filter(company_marketer_uid=base_uid).exists():
                    base_uid = f"{prefix}{company.id}MKT{next_id:03d}"
                
                # Create the profile
                CompanyMarketerProfile.objects.create(
                    marketer=marketer,
                    company=company,
                    company_marketer_id=next_id,
                    company_marketer_uid=base_uid
                )
        except Exception as e:
            # Log but don't fail the affiliation creation
            pass


# @receiver(post_save, sender=Transaction)
# @receiver(post_save, sender=PaymentRecord)
# def update_current_performance(sender, instance, **kwargs):
#     marketer = (instance.marketer
#                 if isinstance(instance, Transaction)
#                 else instance.transaction.marketer)
#     if not marketer:
#         return

#     today = timezone.now().date()
#     month_period = today.strftime('%Y-%m')

#     # Delegate to PerformanceDataAPI logic for this one marketer
#     api = PerformanceDataAPI()
#     # hack: build a fake GET request
#     from django.test import RequestFactory
#     rf = RequestFactory()
#     req = rf.get(f'/api/performance-data/?period_type=monthly&specific_period={month_period}')
#     # Call .get(), ignoring its JSON return, since update_or_create runs inside
#     api.request = req
#     api.get(req)

# Add WebSocket notification signal
@receiver(post_save, sender=UserNotification)
def send_notification_via_websocket(sender, instance, created, **kwargs):
    if kwargs.get('raw', False):
        return

    if not created:
        return

    broadcast_user_notification(instance)
    send_user_notification_push(instance)


@receiver(post_save, sender=Message)
def send_chat_push(sender, instance, created, **kwargs):
    if kwargs.get('raw', False):
        return

    if not created:
        return

    send_chat_message_push(instance)


# ========== SaaS Signals ==========

@receiver(post_save, sender=CustomUser)
def create_client_dashboard(sender, instance, created, **kwargs):
    """
    Auto-create ClientDashboard when a client user is registered.
    This ensures every client has a dashboard for portfolio aggregation.
    """
    if kwargs.get('raw', False):
        return
    
    if created and instance.role == 'client':
        # Create ClientDashboard if it doesn't exist
        from estateApp.models import ClientDashboard
        ClientDashboard.objects.get_or_create(client=instance)

