import sqlite3
import json

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

print("=== Copying plans from estateApp to superAdmin ===")
cursor.execute('SELECT * FROM estateApp_subscriptionplan')
plans = cursor.fetchall()

cursor.execute('PRAGMA table_info(estateApp_subscriptionplan)')
columns = [col[1] for col in cursor.fetchall()]

for plan in plans:
    values = dict(zip(columns, plan))
    plan_id = values['id']
    
    print(f"\nProcessing: {values['name']} (ID={plan_id}, tier={values['tier']})")
    
    # Insert into superAdmin table with same ID
    try:
        cursor.execute('''
            INSERT INTO superAdmin_subscriptionplan 
            (id, tier, name, description, monthly_price, annual_price, 
             max_plots, max_agents, max_api_calls_daily, max_estates, 
             max_allocations, max_clients, max_affiliates, features, 
             is_active, created_at, updated_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            plan_id, values['tier'], values['name'], values.get('description', ''),
            values['monthly_price'], values.get('annual_price'), 
            values['max_plots'], values['max_agents'], values['max_api_calls_daily'],
            values.get('max_estates'), values.get('max_allocations'), 
            values.get('max_clients'), values.get('max_affiliates'),
            values.get('features', '{}'), values['is_active'], 
            values['created_at'], values['updated_at']
        ))
        print(f"  ✓ Inserted with ID {plan_id}")
    except sqlite3.IntegrityError as e:
        print(f"  - Already exists or constraint violation: {e}")

conn.commit()

print("\n=== Final state ===")
cursor.execute('SELECT id, name, tier FROM superAdmin_subscriptionplan ORDER BY id')
print("superAdmin_subscriptionplan:")
for row in cursor.fetchall():
    print(f"  ID {row[0]}: {row[1]} ({row[2]})")

cursor.execute('SELECT id, company_id, current_plan_id FROM estateApp_subscriptionbillingmodel WHERE current_plan_id IS NOT NULL')
print("\nBilling subscriptions:")
for row in cursor.fetchall():
    print(f"  Company {row[1]} -> Plan {row[2]}")

conn.close()
print("\nDone! You can now run migrate command.")
