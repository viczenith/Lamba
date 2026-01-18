import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%feature%'")
print("Feature tables:", [row[0] for row in cursor.fetchall()])

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%subscription%'")
print("\nSubscription tables:")
for row in cursor.fetchall():
    print(f"  - {row[0]}")

conn.close()
