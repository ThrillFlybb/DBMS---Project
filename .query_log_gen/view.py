import sqlite3
conn = sqlite3.connect("auto_index.db")
for row in conn.execute("SELECT * FROM attribute_frequency ORDER BY frequency DESC"):
    print(row)
