# Generated manually to add tenant admin fields only
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estateApp', '0067_clientuser_company_user_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='is_system_admin',
            field=models.BooleanField(
                default=False,
                help_text='Has access to Tenant Admin dashboard and system-wide controls',
                verbose_name='Is System Administrator'
            ),
        ),
        migrations.AddField(
            model_name='customuser',
            name='admin_level',
            field=models.CharField(
                choices=[
                    ('system', 'System Admin - Full access'),
                    ('company', 'Company Admin - Company-only access'),
                    ('none', 'Not an admin')
                ],
                default='none',
                max_length=20,
                verbose_name='Admin Level'
            ),
        ),
    ]
