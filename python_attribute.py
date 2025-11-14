import sqlite3
import re
from collections import Counter

DB_NAME = "autoindex4.db"

def analyze_queries():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT query FROM query_log_update2")
    queries = cursor.fetchall()
    conn.close()

    column_counter = Counter()

    where_pattern = re.compile(r"\bWHERE\b\s+(.*)", re.IGNORECASE)
    set_pattern = re.compile(r"\bSET\b\s+(.*)", re.IGNORECASE)
    insert_pattern = re.compile(r"\bINSERT INTO users\s*\((.*?)\)", re.IGNORECASE)
    column_pattern = re.compile(r"\b(\w+)\s*=")

    for (query,) in queries:
        if where_match := where_pattern.search(query):
            columns = column_pattern.findall(where_match.group(1))
            column_counter.update(columns)

        if set_match := set_pattern.search(query):
            columns = column_pattern.findall(set_match.group(1))
            column_counter.update(columns)

        if insert_match := insert_pattern.search(query):
            columns = [col.strip() for col in insert_match.group(1).split(",")]
            column_counter.update(columns)

    return column_counter

def print_query_stats():
    usage = analyze_queries()
    print("\n📊 Attribute Usage Frequency Across Queries:")
    for column, count in usage.items():
        print(f"  {column}: {count} times")

if __name__ == "__main__":
    print_query_stats()