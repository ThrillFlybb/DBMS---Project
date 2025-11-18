import sqlite3
import time

from backend.config import DB_PATH
from backend.query_generator import extract_columns, extract_table


class DBManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10.0)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=OFF;")
        self.init_schema()

    def init_schema(self):
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                city TEXT,
                join_date TEXT
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                order_date TEXT,
                amount REAL,
                status TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );
            CREATE TABLE IF NOT EXISTS attribute_frequency (
                table_name TEXT,
                column_name TEXT,
                frequency INTEGER
            );
            """
        )
        # Unique index for frequency table
        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_freq_unique 
            ON attribute_frequency(table_name, column_name)
            """
        )
        self._conn.commit()

    def execute(self, sql: str, params=None, retries: int = 3, delay: float = 0.05):
        """Execute a query with basic retry on 'database is locked'."""
        if params is None:
            params = ()
        for attempt in range(retries):
            try:
                cur = self._conn.cursor()
                cur.execute(sql, params)
                # we always commit; this is a write-heavy simulator
                self._conn.commit()
                return cur
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
                    continue
                raise

    def update_frequency_counter(self, sql: str):
        """Update frequency counter for columns in SQL"""
        table_name = extract_table(sql)
        cols = extract_columns(sql)
        if not cols or table_name == "unknown":
            return

        cur = self._conn.cursor()

        for col in cols:
            cur.execute(
                """
                UPDATE attribute_frequency
                SET frequency = frequency + 1
                WHERE table_name = ? AND column_name = ?
                """,
                (table_name, col),
            )
            if cur.rowcount == 0:
                cur.execute(
                    """
                    INSERT INTO attribute_frequency (table_name, column_name, frequency)
                    VALUES (?, ?, 1)
                    """,
                    (table_name, col),
                )

        self._conn.commit()

    def auto_manage_indexes(self):
        """Auto index management based on attribute_frequency"""
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT table_name, column_name, frequency
            FROM attribute_frequency
            ORDER BY frequency DESC
            """
        )
        all_cols = cur.fetchall()
        if len(all_cols) < 3:
            return

        top_three = all_cols[:3]
        bottom_six = all_cols[-6:]

        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';"
        )
        existing_indexes = {row[0] for row in cur.fetchall()}

        # Create indexes for top 3
        for table_name, column_name, _ in top_three:
            index_name = f"idx_{table_name}_{column_name}"
            if index_name not in existing_indexes:
                try:
                    cur.execute(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_name});"
                    )
                except Exception:
                    pass

        # Drop indexes for bottom 6
        for table_name, column_name, _ in bottom_six:
            index_name = f"idx_{table_name}_{column_name}"
            if index_name in existing_indexes:
                try:
                    cur.execute(f"DROP INDEX IF EXISTS {index_name};")
                except Exception:
                    pass

        self._conn.commit()
