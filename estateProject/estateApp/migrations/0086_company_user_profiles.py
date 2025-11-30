# Generated migration for CompanyMarketerProfile and CompanyClientProfile

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('estateApp', '0085_message_company_companysequence'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyMarketerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_marketer_id', models.PositiveIntegerField(db_index=True, verbose_name='Company-Specific Marketer ID')),
                ('company_marketer_uid', models.CharField(db_index=True, max_length=64, unique=True, verbose_name='Company-Specific Marketer UID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marketer_profiles', to='estateApp.company', verbose_name='Company')),
                ('marketer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='company_profiles', to='estateApp.marketeruser', verbose_name='Marketer')),
            ],
            options={
                'verbose_name': 'Company Marketer Profile',
                'verbose_name_plural': 'Company Marketer Profiles',
            },
        ),
        migrations.CreateModel(
            name='CompanyClientProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_client_id', models.PositiveIntegerField(db_index=True, verbose_name='Company-Specific Client ID')),
                ('company_client_uid', models.CharField(db_index=True, max_length=64, unique=True, verbose_name='Company-Specific Client UID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='company_profiles', to='estateApp.clientuser', verbose_name='Client')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='client_profiles', to='estateApp.company', verbose_name='Company')),
            ],
            options={
                'verbose_name': 'Company Client Profile',
                'verbose_name_plural': 'Company Client Profiles',
            },
        ),
        migrations.AddIndex(
            model_name='companymarketerprofile',
            index=models.Index(fields=['company', 'company_marketer_id'], name='estateApp_c_company_12ab3d_idx'),
        ),
        migrations.AddIndex(
            model_name='companymarketerprofile',
            index=models.Index(fields=['marketer', 'company'], name='estateApp_c_markete_4cdef5_idx'),
        ),
        migrations.AddConstraint(
            model_name='companymarketerprofile',
            constraint=models.UniqueConstraint(fields=['marketer', 'company'], name='unique_marketer_company'),
        ),
        migrations.AddIndex(
            model_name='companyclientprofile',
            index=models.Index(fields=['company', 'company_client_id'], name='estateApp_c_company_56fg7h_idx'),
        ),
        migrations.AddIndex(
            model_name='companyclientprofile',
            index=models.Index(fields=['client', 'company'], name='estateApp_c_client_89ij1k_idx'),
        ),
        migrations.AddConstraint(
            model_name='companyclientprofile',
            constraint=models.UniqueConstraint(fields=['client', 'company'], name='unique_client_company'),
        ),
    ]
