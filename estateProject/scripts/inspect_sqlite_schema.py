import sqlite3

DB_PATH = "db.sqlite3"
TABLES = [
    "estateApp_subscriptiontier",
    "estateApp_companyusage",
    "estateApp_subscriptionalert",
    "estateApp_healthcheck",
    "estateApp_systemalert",
]

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

for t in TABLES:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,))
    exists = cur.fetchone() is not None
    print(f"{t}: {'EXISTS' if exists else 'MISSING'}")
    if not exists:
        continue
    cur.execute(f"PRAGMA table_info('{t}')")
    cols = [(r[1], r[2]) for r in cur.fetchall()]
    print("  columns:", cols)

    cur.execute(f"PRAGMA index_list('{t}')")
    idxs = cur.fetchall()
    print("  indexes:")
    for idx in idxs:
        # idx: (seq, name, unique, origin, partial) on newer SQLite
        idx_name = idx[1]
        unique = bool(idx[2])
        print(f"    - {idx_name} (unique={unique})")
        cur.execute(f"PRAGMA index_info('{idx_name}')")
        cols = [r[2] for r in cur.fetchall()]
        print(f"      cols={cols}")

con.close()
