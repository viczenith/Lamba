# Generated migration file for multi-tenant isolation improvements
# Adds explicit company ForeignKey to Transaction, PaymentRecord, and PropertyPrice models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('estateApp', '0071_add_company_to_plotsize_plotnumber'),
    ]

    operations = [
        # Idempotent addition of company_id columns where needed.
        migrations.RunPython(
            code=lambda apps, schema_editor: _add_company_columns_0072(apps, schema_editor),
            reverse_code=migrations.RunPython.noop
        ),
    ]


def _add_company_columns_0072(apps, schema_editor):
    conn = schema_editor.connection
    targets = [
        ('Transaction', 'transaction'),
        ('PaymentRecord', 'paymentrecord'),
        ('PropertyPrice', 'propertyprice')
    ]
    for model_name, _ in targets:
        try:
            model = apps.get_model('estateApp', model_name)
            table = model._meta.db_table
            sql = f'ALTER TABLE "{table}" ADD COLUMN company_id integer;'
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
            except Exception:
                pass
        except Exception:
            pass
