# Generated migration file for multi-tenant isolation improvements
# Adds explicit company ForeignKey to Transaction, PaymentRecord, and PropertyPrice models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('estateApp', '0071_add_company_to_plotsize_plotnumber'),
    ]

    operations = [
        # Add company FK to Transaction model
        migrations.AddField(
            model_name='transaction',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='estateApp.company'),
        ),
        
        # Add company FK to PaymentRecord model
        migrations.AddField(
            model_name='paymentrecord',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payment_records', to='estateApp.company'),
        ),
        
        # Add company FK to PropertyPrice model
        migrations.AddField(
            model_name='propertyprice',
            name='company',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='property_prices', to='estateApp.company'),
        ),
    ]
