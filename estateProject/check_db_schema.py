import sqlite3
import os

db_path = r'c:\Users\HP\Documents\VictorGodwin\RE\Multi-Tenant Architecture\RealEstateMSApp\estateProject\db.sqlite3'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check PlotSize schema
cursor.execute("PRAGMA table_info(estateApp_plotsize)")
print("PlotSize columns:")
for row in cursor.fetchall():
    print(f"  {row}")

# Check PlotNumber schema
cursor.execute("PRAGMA table_info(estateApp_plotnumber)")
print("\nPlotNumber columns:")
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
