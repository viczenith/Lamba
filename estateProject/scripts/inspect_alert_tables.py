from django.db import connection

TABLES = [
    "estateApp_subscriptiontier",
    "estateApp_companyusage",
    "estateApp_subscriptionalert",
    "estateApp_healthcheck",
    "estateApp_systemalert",
]

cur = connection.cursor()
for table in TABLES:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % table)
    exists = cur.fetchone() is not None
    print(f"{table}: {'EXISTS' if exists else 'MISSING'}")
    if not exists:
        continue
    cur.execute("PRAGMA table_info('%s')" % table)
    cols = [(row[1], row[2]) for row in cur.fetchall()]
    print("  columns:", cols)
