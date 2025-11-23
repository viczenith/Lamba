# Generated migration for SubscriptionBillingModel

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('estateApp', '0069_add_company_slug_field'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubscriptionBillingModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('trial', 'Trial'), ('active', 'Active'), ('grace', 'Grace Period'), ('suspended', 'Suspended'), ('cancelled', 'Cancelled'), ('expired', 'Expired')], default='trial', max_length=20)),
                ('trial_started_at', models.DateTimeField(blank=True, null=True)),
                ('trial_ends_at', models.DateTimeField(blank=True, null=True)),
                ('subscription_started_at', models.DateTimeField(blank=True, null=True)),
                ('subscription_ends_at', models.DateTimeField(blank=True, null=True)),
                ('billing_cycle', models.CharField(choices=[('monthly', 'Monthly'), ('annual', 'Annual')], default='monthly', max_length=20)),
                ('auto_renew', models.BooleanField(default=True)),
                ('next_billing_date', models.DateField(blank=True, null=True)),
                ('grace_period_started_at', models.DateTimeField(blank=True, null=True)),
                ('grace_period_ends_at', models.DateTimeField(blank=True, null=True)),
                ('last_payment_date', models.DateTimeField(blank=True, null=True)),
                ('payment_method', models.CharField(blank=True, choices=[('stripe', 'Stripe'), ('paystack', 'Paystack'), ('bank_transfer', 'Bank Transfer'), ('free_trial', 'Free Trial')], max_length=20, null=True)),
                ('stripe_subscription_id', models.CharField(blank=True, max_length=255, null=True)),
                ('paystack_subscription_code', models.CharField(blank=True, max_length=255, null=True)),
                ('monthly_amount', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True)),
                ('annual_amount', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True)),
                ('warning_level', models.IntegerField(default=0, help_text='0=No warning, 1=Yellow, 2=Orange, 3=Red')),
                ('last_warning_sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='billing', to='estateApp.company')),
                ('current_plan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subscriptions', to='estateApp.subscriptionplan')),
            ],
            options={
                'verbose_name': 'Subscription Billing',
                'verbose_name_plural': 'Subscription Billings',
            },
        ),
        migrations.CreateModel(
            name='BillingHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_date', models.DateTimeField(auto_now_add=True)),
                ('transaction_type', models.CharField(choices=[('subscription_created', 'Subscription Created'), ('subscription_renewed', 'Subscription Renewed'), ('subscription_upgraded', 'Subscription Upgraded'), ('payment_received', 'Payment Received'), ('payment_failed', 'Payment Failed'), ('subscription_cancelled', 'Subscription Cancelled'), ('grace_period_started', 'Grace Period Started'), ('grace_period_ended', 'Grace Period Ended')], max_length=50)),
                ('amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('description', models.TextField(blank=True)),
                ('subscription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='history', to='estateApp.subscriptionbillingmodel')),
            ],
            options={
                'verbose_name_plural': 'Billing Histories',
                'ordering': ['-transaction_date'],
            },
        ),
    ]
