"""Restore subscription/alert models safely.

This project has historically had these tables created, later deleted from the code,
and then reintroduced. Some environments may already have the tables (SQLite) while
the migration history says they don't.

This migration is therefore intentionally idempotent:
- If tables are missing, it creates them.
- If tables exist, it only applies missing schema changes (e.g. add hide_until).
"""

import django.db.models.deletion
from django.db import migrations, models


def _sqlite_table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=%s", (table_name,)
    )
    return cursor.fetchone() is not None


def _sqlite_columns(cursor, table_name: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info('{table_name}')")
    return {row[1] for row in cursor.fetchall()}


def _sqlite_index_columns(cursor, table_name: str) -> tuple[set[tuple[str, ...]], set[tuple[str, ...]]]:
    """Returns (non_unique_indexes, unique_indexes) by column tuples."""
    cursor.execute(f"PRAGMA index_list('{table_name}')")
    index_list = cursor.fetchall()

    non_unique: set[tuple[str, ...]] = set()
    unique: set[tuple[str, ...]] = set()

    for idx in index_list:
        # idx is (seq, name, unique, origin, partial) on newer SQLite
        idx_name = idx[1]
        is_unique = bool(idx[2])
        cursor.execute(f"PRAGMA index_info('{idx_name}')")
        cols = tuple(row[2] for row in cursor.fetchall())
        if not cols:
            continue
        if is_unique:
            unique.add(cols)
        else:
            non_unique.add(cols)

    return non_unique, unique


def sync_restore_subscription_alert_tables(apps, schema_editor):
    """Ensure tables exist and are aligned with restored models."""
    connection = schema_editor.connection
    # This migration is primarily to reconcile SQLite environments.
    if connection.vendor != 'sqlite':
        return

    cursor = connection.cursor()

    model_names = [
        'SubscriptionTier',
        'CompanyUsage',
        'SubscriptionAlert',
        'HealthCheck',
        'SystemAlert',
    ]

    for model_name in model_names:
        model = apps.get_model('estateApp', model_name)
        table = model._meta.db_table

        if not _sqlite_table_exists(cursor, table):
            schema_editor.create_model(model)
            continue

        existing_cols = _sqlite_columns(cursor, table)

        # Add missing columns (the known real-world drift is hide_until).
        if model_name == 'SubscriptionAlert' and 'hide_until' not in existing_cols:
            schema_editor.add_field(model, model._meta.get_field('hide_until'))
            existing_cols.add('hide_until')

        # Ensure indexes/uniques exist without duplicating equivalent ones.
        non_unique_idx, unique_idx = _sqlite_index_columns(cursor, table)

        for index in getattr(model._meta, 'indexes', []) or []:
            cols = tuple(index.fields)
            if cols in non_unique_idx or cols in unique_idx:
                continue
            schema_editor.add_index(model, index)

        for ut in getattr(model._meta, 'unique_together', []) or []:
            field_names = tuple(ut)
            db_cols = tuple(model._meta.get_field(n).column for n in field_names)
            if db_cols in unique_idx:
                continue

            # Avoid relying on private schema_editor APIs (signatures vary across Django versions).
            index_name = f"{table}_{'_'.join(db_cols)}_uniq_0096"
            quoted_table = schema_editor.quote_name(table)
            quoted_cols = ", ".join(schema_editor.quote_name(c) for c in db_cols)
            quoted_index = schema_editor.quote_name(index_name)
            schema_editor.execute(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {quoted_index} ON {quoted_table} ({quoted_cols})"
            )


class Migration(migrations.Migration):

    dependencies = [
        ('estateApp', '0095_estate_estate_size_unit_alter_estate_estate_size'),
    ]

    operations = [
        # 1) Update migration state without touching the DB (avoids "table already exists").
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='SubscriptionTier',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('tier', models.CharField(choices=[('starter', 'Starter'), ('professional', 'Professional'), ('enterprise', 'Enterprise')], max_length=20, unique=True, verbose_name='Tier')),
                        ('name', models.CharField(max_length=100, verbose_name='Display Name')),
                        ('description', models.TextField(verbose_name='Description')),
                        ('price_per_month', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Monthly Price')),
                        ('price_per_year', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Annual Price')),
                        ('max_plots', models.PositiveIntegerField(verbose_name='Max Plots')),
                        ('max_agents', models.PositiveIntegerField(verbose_name='Max Agents')),
                        ('max_api_calls_daily', models.PositiveIntegerField(verbose_name='Max Daily API Calls')),
                        ('max_storage_gb', models.PositiveIntegerField(verbose_name='Max Storage GB')),
                        ('features', models.JSONField(default=list, verbose_name='Available Features')),
                        ('support_level', models.CharField(choices=[('email', 'Email Support'), ('priority', 'Priority Support'), ('dedicated', 'Dedicated Support')], default='email', max_length=20, verbose_name='Support Level')),
                        ('sla_uptime_percent', models.DecimalField(decimal_places=2, default=99.5, max_digits=5, verbose_name='SLA Uptime %')),
                        ('is_active', models.BooleanField(default=True, verbose_name='Is Active')),
                        ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                        ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                    ],
                    options={
                        'verbose_name': 'Subscription Tier',
                        'verbose_name_plural': 'Subscription Tiers',
                        'ordering': ['price_per_month'],
                    },
                ),
                migrations.CreateModel(
                    name='CompanyUsage',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('feature', models.CharField(choices=[('plots', 'Estate Plots'), ('agents', 'Agents/Marketers'), ('api_calls', 'API Calls'), ('storage', 'Storage'), ('exports', 'Exports'), ('reports', 'Reports')], max_length=20, verbose_name='Feature')),
                        ('usage_count', models.BigIntegerField(default=0, verbose_name='Usage Count')),
                        ('usage_limit', models.BigIntegerField(verbose_name='Usage Limit')),
                        ('period', models.CharField(choices=[('daily', 'Daily'), ('monthly', 'Monthly'), ('yearly', 'Yearly')], default='monthly', max_length=10, verbose_name='Period')),
                        ('reset_date', models.DateTimeField(verbose_name='Reset Date')),
                        ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                        ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                        ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usage_metrics', to='estateApp.company')),
                    ],
                    options={
                        'verbose_name': 'Company Usage',
                        'verbose_name_plural': 'Company Usage Metrics',
                    },
                ),
                migrations.CreateModel(
                    name='SubscriptionAlert',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('alert_type', models.CharField(choices=[('trial_ending', 'Trial Ending'), ('trial_expired', 'Trial Expired'), ('grace_period', 'Grace Period Active'), ('subscription_renewing', 'Subscription Renewing'), ('subscription_failed', 'Subscription Payment Failed'), ('usage_warning', 'Usage Limit Warning'), ('usage_exceeded', 'Usage Limit Exceeded'), ('read_only_mode', 'Read-Only Mode Activated'), ('data_deletion_warning', 'Data Deletion Warning'), ('system_alert', 'System Alert')], max_length=30, verbose_name='Alert Type')),
                        ('severity', models.CharField(choices=[('info', 'Info'), ('warning', 'Warning'), ('critical', 'Critical'), ('urgent', 'Urgent')], default='warning', max_length=10, verbose_name='Severity')),
                        ('status', models.CharField(choices=[('active', 'Active'), ('acknowledged', 'Acknowledged'), ('resolved', 'Resolved'), ('dismissed', 'Dismissed'), ('blocked', 'Blocked')], default='active', max_length=20, verbose_name='Status')),
                        ('title', models.CharField(max_length=255, verbose_name='Title')),
                        ('message', models.TextField(verbose_name='Message')),
                        ('action_url', models.URLField(blank=True, null=True, verbose_name='Action URL')),
                        ('action_label', models.CharField(blank=True, max_length=100, null=True, verbose_name='Action Label')),
                        ('is_dismissible', models.BooleanField(default=True, verbose_name='Is Dismissible')),
                        ('show_on_dashboard', models.BooleanField(default=True, verbose_name='Show on Dashboard')),
                        ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                        ('acknowledged_at', models.DateTimeField(blank=True, null=True, verbose_name='Acknowledged At')),
                        ('resolved_at', models.DateTimeField(blank=True, null=True, verbose_name='Resolved At')),
                        ('dismissed_at', models.DateTimeField(blank=True, null=True, verbose_name='Dismissed At')),
                        ('hide_until', models.DateTimeField(blank=True, null=True, verbose_name='Hide Until')),
                        ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscription_alerts', to='estateApp.company')),
                    ],
                    options={
                        'verbose_name': 'Subscription Alert',
                        'verbose_name_plural': 'Subscription Alerts',
                        'ordering': ['-created_at'],
                    },
                ),
                migrations.CreateModel(
                    name='HealthCheck',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('service_name', models.CharField(choices=[('database', 'Database'), ('cache', 'Cache/Redis'), ('api', 'API Server'), ('email', 'Email Service'), ('payment_gateway', 'Payment Gateway'), ('storage', 'Storage Service'), ('websocket', 'WebSocket')], max_length=50, verbose_name='Service Name')),
                        ('status', models.CharField(choices=[('healthy', 'Healthy'), ('degraded', 'Degraded'), ('unhealthy', 'Unhealthy'), ('unknown', 'Unknown')], default='unknown', max_length=20, verbose_name='Status')),
                        ('response_time_ms', models.FloatField(blank=True, null=True, verbose_name='Response Time (ms)')),
                        ('error_message', models.TextField(blank=True, null=True, verbose_name='Error Message')),
                        ('last_check', models.DateTimeField(auto_now=True, verbose_name='Last Check')),
                        ('last_failure', models.DateTimeField(blank=True, null=True, verbose_name='Last Failure')),
                        ('alert_sent', models.BooleanField(default=False, verbose_name='Alert Sent')),
                        ('alert_sent_at', models.DateTimeField(blank=True, null=True, verbose_name='Alert Sent At')),
                    ],
                    options={
                        'verbose_name': 'Health Check',
                        'verbose_name_plural': 'Health Checks',
                        'ordering': ['-last_check'],
                    },
                ),
                migrations.CreateModel(
                    name='SystemAlert',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('alert_type', models.CharField(choices=[('performance', 'Performance Issue'), ('security', 'Security Issue'), ('maintenance', 'Maintenance'), ('downtime', 'Downtime'), ('capacity', 'Capacity Issue'), ('error', 'Error')], max_length=20, verbose_name='Alert Type')),
                        ('severity', models.CharField(choices=[('info', 'Info'), ('warning', 'Warning'), ('critical', 'Critical'), ('emergency', 'Emergency')], default='warning', max_length=20, verbose_name='Severity')),
                        ('status', models.CharField(choices=[('active', 'Active'), ('acknowledged', 'Acknowledged'), ('resolved', 'Resolved')], default='active', max_length=20, verbose_name='Status')),
                        ('title', models.CharField(max_length=255, verbose_name='Title')),
                        ('message', models.TextField(verbose_name='Message')),
                        ('resolution_steps', models.TextField(blank=True, null=True, verbose_name='Resolution Steps')),
                        ('affected_users_count', models.PositiveIntegerField(default=0, verbose_name='Affected Users Count')),
                        ('affected_companies_count', models.PositiveIntegerField(default=0, verbose_name='Affected Companies Count')),
                        ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                        ('acknowledged_at', models.DateTimeField(blank=True, null=True, verbose_name='Acknowledged At')),
                        ('resolved_at', models.DateTimeField(blank=True, null=True, verbose_name='Resolved At')),
                    ],
                    options={
                        'verbose_name': 'System Alert',
                        'verbose_name_plural': 'System Alerts',
                        'ordering': ['-created_at'],
                    },
                ),
                migrations.AddIndex(
                    model_name='companyusage',
                    index=models.Index(fields=['company', 'feature'], name='estateApp_c_company_096_restore_idx'),
                ),
                migrations.AddIndex(
                    model_name='companyusage',
                    index=models.Index(fields=['reset_date'], name='estateApp_c_reset_d_096_restore_idx'),
                ),
                migrations.AlterUniqueTogether(
                    name='companyusage',
                    unique_together={('company', 'feature', 'period')},
                ),
                migrations.AlterUniqueTogether(
                    name='healthcheck',
                    unique_together={('service_name',)},
                ),
                migrations.AddIndex(
                    model_name='subscriptionalert',
                    index=models.Index(fields=['company', 'status'], name='estateApp_s_company_096_restore_idx'),
                ),
                migrations.AddIndex(
                    model_name='subscriptionalert',
                    index=models.Index(fields=['severity', 'created_at'], name='estateApp_s_severit_096_restore_idx'),
                ),
                migrations.AddIndex(
                    model_name='subscriptionalert',
                    index=models.Index(fields=['alert_type'], name='estateApp_s_alert_t_096_restore_idx'),
                ),
                migrations.AddIndex(
                    model_name='systemalert',
                    index=models.Index(fields=['severity', 'status'], name='estateApp_s_severit_096_sys_idx'),
                ),
                migrations.AddIndex(
                    model_name='systemalert',
                    index=models.Index(fields=['alert_type'], name='estateApp_s_alert_t_096_sys_idx'),
                ),
            ],
        ),

        # 2) Actually sync the database schema to match the restored state.
        migrations.RunPython(sync_restore_subscription_alert_tables, migrations.RunPython.noop),
    ]
