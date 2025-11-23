# Generated migration to add company field to PlotSize and PlotNumber models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('estateApp', '0070_subscriptionbillingmodel'),
    ]

    operations = [
        migrations.AddField(
            model_name='plotsize',
            name='company',
            field=models.ForeignKey(blank=True, null=True, help_text='Company that owns this plot size', on_delete=django.db.models.deletion.CASCADE, related_name='plot_sizes', to='estateApp.company'),
        ),
        migrations.AddField(
            model_name='plotnumber',
            name='company',
            field=models.ForeignKey(blank=True, null=True, help_text='Company that owns this plot number', on_delete=django.db.models.deletion.CASCADE, related_name='plot_numbers', to='estateApp.company'),
        ),
        migrations.AlterUniqueTogether(
            name='plotsize',
            unique_together={('company', 'size')},
        ),
        migrations.AlterUniqueTogether(
            name='plotnumber',
            unique_together={('company', 'number')},
        ),
    ]
