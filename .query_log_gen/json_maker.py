import sqlite3
import json

DB_PATH = "auto_index.db"
OUTPUT_JSON = "frequency_stats.json"

def export_frequency_stats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT table_name, column_name, frequency
        FROM attribute_frequency
        ORDER BY frequency DESC
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("No data found in attribute_frequency table.")
        return

    total_freq = sum(freq for _, _, freq in rows)
    data = [
        {
            "table_name": t,
            "column_name": c,
            "frequency": f,
            "frequency_percent": round((f / total_freq) * 100, 2)
        }
        for t, c, f in rows
    ]

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    print(f"Exported {len(data)} records to {OUTPUT_JSON}.")

if __name__ == "__main__":
    export_frequency_stats()
