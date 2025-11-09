import sqlite3

DB_PATH = "auto_index.db"

def auto_manage_indexes():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Step 1: Get top 3 and bottom 6 columns by frequency
    cur.execute("""
        SELECT table_name, column_name, frequency
        FROM attribute_frequency
        ORDER BY frequency DESC
    """)
    all_cols = cur.fetchall()

    if len(all_cols) < 3:
        print("Not enough data in attribute_frequency table.")
        conn.close()
        return

    top_three = all_cols[:3]
    bottom_six = all_cols[-6:]

    print("\nTop 3 columns selected for indexing:")
    for t, c, f in top_three:
        print(f"  {t}.{c} ({f} uses)")

    print("\nBottom 6 columns selected for index removal:")
    for t, c, f in bottom_six:
        print(f"  {t}.{c} ({f} uses)")

    # Step 2: Get list of existing indexes
    cur.execute("SELECT name FROM sqlite_master WHERE type='index';")
    existing_indexes = {row[0] for row in cur.fetchall()}

    # Step 4: Create indexes for top 3 if not already present
    for table_name, column_name, _ in top_three:
        index_name = f"idx_{table_name}_{column_name}"
        if index_name not in existing_indexes:
            try:
                cur.execute(f"CREATE INDEX {index_name} ON {table_name} ({column_name});")
                print(f"Created index: {index_name}")
            except Exception as e:
                print(f"Error creating index {index_name}: {e}")
        else:
            print(f"Index already exists: {index_name}")

    # Step 5: Drop indexes for bottom 6 if they exist
    for table_name, column_name, _ in bottom_six:
        index_name = f"idx_{table_name}_{column_name}"
        if index_name in existing_indexes:
            try:
                cur.execute(f"DROP INDEX {index_name};")
                print(f"Removed index: {index_name}")
            except Exception as e:
                print(f"Error dropping index {index_name}: {e}")
        else:
            print(f"No index found for: {index_name}")

    conn.commit()
    conn.close()
    print("\nIndex management completed.\n")

if __name__ == "__main__":
    auto_manage_indexes()