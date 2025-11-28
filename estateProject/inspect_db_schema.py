import sqlite3
import os

DB='db.sqlite3'
path=os.path.join(os.path.dirname(__file__), DB)
print('Using DB:', path)
conn=sqlite3.connect(path)
cur=conn.cursor()

tables=['estateApp_message','estateApp_clientuser','estateApp_marketeruser']
for t in tables:
    try:
        cur.execute(f"PRAGMA table_info('{t}')")
        cols=[r[1] for r in cur.fetchall()]
        print(f"Table {t}: columns=", cols)
    except Exception as e:
        print(f"Table {t}: ERROR ->", e)

conn.close()