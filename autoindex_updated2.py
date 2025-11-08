import sqlite3
import time
import re
import random
import os
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

DB_NAME = "autoindex4.db"

# Step 1: Create updated query log table
def initialize_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS query_log_update2 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER,
        name TEXT,
        age INTEGER
    )
    """)
    conn.commit()
    conn.close()
    print("✅ Tables 'users' and 'query_log_update2' initialized.")

# Step 2: Execute and log queries (thread-safe)
def execute_and_log(query):
    try:
        local_conn = sqlite3.connect(DB_NAME)
        local_cursor = local_conn.cursor()
        local_cursor.execute(query)
        local_cursor.execute("INSERT INTO query_log_update2 (query) VALUES (?)", (query,))
        local_conn.commit()
        local_conn.close()
        print(f"[LOGGED] Executed and logged: {query}")
    except Exception as e:
        print(f"[ERROR] Query failed: {query}\nReason: {e}")

# Step 3: Analyze column usage
def analyze_queries():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT query FROM query_log_update2")
    queries = cursor.fetchall()
    conn.close()

    column_counter = Counter()
    where_pattern = re.compile(r"\bWHERE\b\s+(.*)", re.IGNORECASE)
    column_pattern = re.compile(r"\b(\w+)\s*=")

    for (query,) in queries:
        where_match = where_pattern.search(query)
        if where_match:
            condition = where_match.group(1)
            columns = column_pattern.findall(condition)
            column_counter.update(columns)

    return column_counter

# Step 4: Recommend indexes
def recommend_indexes(threshold=2):
    column_usage = analyze_queries()
    return [col for col, count in column_usage.items() if count >= threshold]

# Step 5: Apply indexes
def apply_indexes(table_name, recommended_columns):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    print("\n Applying Indexes:")
    for column in recommended_columns:
        index_name = f"idx_{table_name}_{column}"
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column})")
            print(f"   Index created: {index_name}")
        except Exception as e:
            print(f"   Failed to create index on {column}: {e}")
    conn.commit()
    conn.close()

# Step 6: Benchmark query performance
def timed_query(query):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    start = time.time()
    cursor.execute(query)
    end = time.time()
    conn.close()
    print(f"\n Benchmarking Query:\n  {query}\n  Time taken: {end - start:.6f} seconds")

# Step 7: Show query frequency stats
def print_query_stats():
    usage = analyze_queries()
    print("\n Column Usage Frequency:")
    for column, count in usage.items():
        print(f"  {column}: {count} times")

# Step 8: Show indexes created
def show_indexes(table_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA index_list('{table_name}')")
    indexes = cursor.fetchall()
    conn.close()
    print(f"\n Indexes on '{table_name}':")
    for idx in indexes:
        print(f"  {idx[1]}")

# Step 9: Export query log
def export_query_log(filename="query_log_update2.txt"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM query_log_update2")
    rows = cursor.fetchall()
    conn.close()
    with open(filename, "w") as f:
        for row in rows:
            f.write(f"{row}\n")
    print(f"\n Query log exported to '{filename}'")
    print(f" File path: {os.path.abspath(filename)}")

# Step 10: Generate randomized queries
names = ['Pranav', 'Gaurav', 'Abhay', 'Shivraj', 'Aryan', 'Neha', 'Riya', 'Kunal']
ages = [20, 25, 30, 35, 40]

def generate_query():
    r = random.random()
    if r < 0.50:
        col = random.choice(['name', 'age', 'id'])
        val = random.choice(names if col == 'name' else ages if col == 'age' else range(1, 10))
        return f"SELECT * FROM users WHERE {col} = '{val}'" if isinstance(val, str) else f"SELECT * FROM users WHERE {col} = {val}"
    elif r < 0.75:
        name = random.choice(names)
        age = random.choice(ages)
        new_id = random.randint(100, 10000)
        return f"INSERT INTO users (id, name, age) VALUES ({new_id}, '{name}', {age})"
    elif r < 0.95:
        name = random.choice(names)
        new_age = random.choice(ages)
        return f"UPDATE users SET age = {new_age} WHERE name = '{name}'"
    else:
        name = random.choice(names)
        return f"DELETE FROM users WHERE name = '{name}'"

# 🔁 Infinite query generator
def run_parallel_queries_forever(batch_size=100, delay=0.5):
    print("\n🚀 Starting infinite query generation... Press Ctrl+C to stop.\n")
    try:
        while True:
            queries = [generate_query() for _ in range(batch_size)]
            with ThreadPoolExecutor(max_workers=20) as executor:
                executor.map(execute_and_log, queries)
            time.sleep(delay)
    except KeyboardInterrupt:
        print("\n🛑 Query generation stopped by user.")

# ⏱️ Periodic auto-export every 5 minutes
def periodic_export(interval=300):
    def export_loop():
        while True:
            time.sleep(interval)
            export_query_log()
    threading.Thread(target=export_loop, daemon=True).start()

# Step 11: Main execution flow
def run_autoindex():
    print("\n Starting AutoIndex v2...\n")
    initialize_database()

    # Insert sample data
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    cursor.executemany("INSERT INTO users (id, name, age) VALUES (?, ?, ?)", [
        (1, 'Pranav', 25),
        (2, 'Gaurav', 30),
        (3, 'Abhay', 25),
        (4, 'Shivraj', 30)
    ])
    conn.commit()
    conn.close()
    print(" Sample data inserted into 'users' table.")

    # One-time test insert to verify logging
    test_query = "SELECT * FROM users WHERE name = 'Pranav'"
    execute_and_log(test_query)
    export_query_log()

    # Start periodic export
    periodic_export(interval=300)

    # Simulated infinite traffic
    run_parallel_queries_forever(batch_size=100, delay=0.5)

# Run the system
if __name__ == "__main__":
    run_autoindex()