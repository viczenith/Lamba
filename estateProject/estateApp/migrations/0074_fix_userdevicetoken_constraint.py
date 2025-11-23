# Generated migration to fix UserDeviceToken unique constraint
# Changes from global unique=True to unique_together on (user, token)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estateApp', '0073_populate_company_fields'),
    ]

    operations = [
        # Remove the global unique constraint on token
        migrations.AlterField(
            model_name='userdevicetoken',
            name='token',
            field=models.CharField(max_length=255),
        ),
        
        # Add unique_together constraint
        migrations.AlterUniqueTogether(
            name='userdevicetoken',
            unique_together={('user', 'token')},
        ),
    ]
