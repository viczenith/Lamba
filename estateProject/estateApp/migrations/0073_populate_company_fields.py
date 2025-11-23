# Generated data migration to populate company field for existing records
# This migration should run after 0072_add_company_to_transaction_paymentrecord_propertyprice

from django.db import migrations


def populate_company_transaction(apps, schema_editor):
    """Populate company field for Transaction records using allocation.estate.company"""
    Transaction = apps.get_model('estateApp', 'Transaction')
    for transaction in Transaction.objects.filter(company__isnull=True):
        if transaction.allocation and transaction.allocation.estate:
            transaction.company = transaction.allocation.estate.company
            transaction.save(update_fields=['company'])


def populate_company_paymentrecord(apps, schema_editor):
    """Populate company field for PaymentRecord records using transaction.allocation.estate.company"""
    PaymentRecord = apps.get_model('estateApp', 'PaymentRecord')
    for record in PaymentRecord.objects.filter(company__isnull=True):
        if record.transaction and record.transaction.allocation and record.transaction.allocation.estate:
            record.company = record.transaction.allocation.estate.company
            record.save(update_fields=['company'])


def populate_company_propertyprice(apps, schema_editor):
    """Populate company field for PropertyPrice records using estate.company"""
    PropertyPrice = apps.get_model('estateApp', 'PropertyPrice')
    for price in PropertyPrice.objects.filter(company__isnull=True):
        if price.estate:
            price.company = price.estate.company
            price.save(update_fields=['company'])


def reverse_populate(apps, schema_editor):
    """Reverse operation - clear company fields"""
    Transaction = apps.get_model('estateApp', 'Transaction')
    PaymentRecord = apps.get_model('estateApp', 'PaymentRecord')
    PropertyPrice = apps.get_model('estateApp', 'PropertyPrice')
    
    Transaction.objects.all().update(company=None)
    PaymentRecord.objects.all().update(company=None)
    PropertyPrice.objects.all().update(company=None)


class Migration(migrations.Migration):

    dependencies = [
        ('estateApp', '0072_add_company_to_transaction_paymentrecord_propertyprice'),
    ]

    operations = [
        migrations.RunPython(
            code=populate_company_transaction,
            reverse_code=reverse_populate,
        ),
        migrations.RunPython(
            code=populate_company_paymentrecord,
            reverse_code=reverse_populate,
        ),
        migrations.RunPython(
            code=populate_company_propertyprice,
            reverse_code=reverse_populate,
        ),
    ]
