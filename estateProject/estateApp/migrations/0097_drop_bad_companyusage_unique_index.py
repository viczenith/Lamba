from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('estateApp', '0096_restore_subscription_alert_models'),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP INDEX IF EXISTS estateApp_companyusage_company_feature_period_uniq_0096;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
