# Generated migration for adding Paystack customer code field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estateApp', '0001_initial'),  # Update this to match your latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='paystack_customer_code',
            field=models.CharField(
                max_length=255,
                unique=True,
                null=True,
                blank=True,
                verbose_name='Paystack Customer Code'
            ),
        ),
        migrations.AddIndex(
            model_name='company',
            index=models.Index(fields=['paystack_customer_code'], name='estateapp_c_paysta_idx'),
        ),
    ]
