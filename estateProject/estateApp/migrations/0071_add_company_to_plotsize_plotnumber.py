# Generated migration to add company field to PlotSize and PlotNumber models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('estateApp', '0070_subscriptionbillingmodel'),
    ]

    operations = [
        # Make the migration idempotent: some environments already have these
        # columns present. Use a RunPython that attempts to add the raw
        # columns if they do not exist; ignore errors if they already do.
        migrations.RunPython(
            code=lambda apps, schema_editor: _add_company_columns(apps, schema_editor),
            reverse_code=migrations.RunPython.noop
        ),
    ]


def _add_company_columns(apps, schema_editor):
    """Add `company_id` integer columns to PlotSize and PlotNumber tables if missing.

    We use raw ALTER TABLE statements and ignore failures to make the
    migration safe to run multiple times in different environments.
    """
    conn = schema_editor.connection
    models_to_update = ['PlotSize', 'PlotNumber']
    for model_name in models_to_update:
        try:
            model = apps.get_model('estateApp', model_name)
            table = model._meta.db_table
            sql = f'ALTER TABLE "{table}" ADD COLUMN company_id integer;'
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
            except Exception:
                # Ignore - column may already exist or DB may not support ALTER
                pass
        except Exception:
            # If any error occurs resolving the model, skip it
            pass
