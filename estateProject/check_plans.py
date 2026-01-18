import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

print("=== Current superAdmin plans ===")
cursor.execute('SELECT id, name, tier, monthly_price, max_plots FROM superAdmin_subscriptionplan ORDER BY id')
for row in cursor.fetchall():
    print(f"ID {row[0]}: {row[1]} ({row[2]}) - Price: {row[3]}, Plots: {row[4]}")

print("\n=== Current estateApp plans ===")
cursor.execute('SELECT id, name, tier, monthly_price, max_plots FROM estateApp_subscriptionplan ORDER BY id')
for row in cursor.fetchall():
    print(f"ID {row[0]}: {row[1]} ({row[2]}) - Price: {row[3]}, Plots: {row[4]}")

# Update superAdmin plans with correct data from estateApp
print("\n=== Updating superAdmin plans ===")
cursor.execute('''
    UPDATE superAdmin_subscriptionplan 
    SET name = 'Starter', 
        tier = 'starter',
        monthly_price = 70000.00,
        max_plots = 100
    WHERE id = 1
''')
print("Updated ID 1 to Starter")

print("\nFinal superAdmin plans:")
cursor.execute('SELECT id, name, tier, monthly_price, max_plots FROM superAdmin_subscriptionplan ORDER BY id')
for row in cursor.fetchall():
    print(f"ID {row[0]}: {row[1]} ({row[2]}) - Price: {row[3]}, Plots: {row[4]}")

conn.commit()
conn.close()
