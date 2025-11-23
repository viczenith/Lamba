# Generated migration - Add slug field to Company model for tenancy isolation

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estateApp', '0068_add_tenant_admin_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='slug',
            field=models.SlugField(
                blank=True,
                db_index=True,
                help_text='Unique identifier for multi-tenant routing and isolation',
                max_length=255,
                null=True,
                unique=True,
                verbose_name='Company Slug (Tenancy ID)'
            ),
        ),
    ]
