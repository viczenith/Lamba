from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('estateApp', '0076_companyceo'),
    ]

    operations = [
        migrations.CreateModel(
            name='IsolationAuditLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=20)),
                ('model_name', models.CharField(max_length=100)),
                ('object_id', models.IntegerField(null=True, blank=True)),
                ('description', models.TextField(blank=True)),
                ('ip_address', models.GenericIPAddressField(null=True, blank=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('resolved', models.BooleanField(default=False)),
                ('resolution_notes', models.TextField(blank=True)),
                ('company', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, to='estateApp.Company')),
                ('user', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, to='estateApp.CustomUser')),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='isolationauditlog',
            index=models.Index(fields=['company', 'timestamp'], name='estateApp_company_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='isolationauditlog',
            index=models.Index(fields=['timestamp'], name='estateApp_timestamp_idx'),
        ),
    ]
