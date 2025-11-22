# Script to add company field to all remaining models
# Run this after base models are updated

from django.db import migrations, models
import django.db.models.deletion


def add_company_fields():
    """
    Models that need company field added:
    
    ✅ Already Added:
    - Company (base model)
    - Estate
    - Message  
    - PlotSize
    - PlotNumber
    - PlotAllocation
    
    ❌ Need to Add:
    - EstatePlot
    - EstateFloorPlan
    - EstatePrototype
    - EstateAmenitie
    - EstateLayout
    - EstateMap
    - Notification
    - NotificationDispatch
    - UserNotification
    - UserDeviceToken
    - ProgressStatus
    - PropertyRequest
    - Transaction
    - PaymentRecord
    - MarketerCommission
    - MarketerTarget
    - MarketerPerformanceRecord
    - PropertyPrice
    - PriceHistory
    - PromotionalOffer
    """
    
    models_needing_company = [
        'estateplot',
        'estatefloorplan',
        'estateprototype',
        'estateamenitie',
        'estatelayout',
        'estatemap',
        'notification',
        'notificationdispatch',
        'usernotification',
        'userdevicetoken',
        'progressstatus',
        'propertyrequest',
        'transaction',
        'paymentrecord',
        'marketercommission',
        'marketertarget',
        'marketerperformancerecord',
        'propertyprice',
        'pricehistory',
        'promotionaloffer',
    ]
    
    operations = []
    
    for model_name in models_needing_company:
        operations.append(
            migrations.AddField(
                model_name=model_name,
                name='company',
                field=models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name=f'{model_name}s',
                    to='estateApp.company',
                    verbose_name='Company'
                ),
            )
        )
    
    return operations


if __name__ == '__main__':
    print("Models that will get company field:")
    for op in add_company_fields():
        print(f"  - {op.model_name}")
