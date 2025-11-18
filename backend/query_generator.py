import random
import re
from datetime import datetime

# ------------------------ GAURAV'S QUERY GENERATOR ------------------------

CUSTOMER_COLS = ["name", "email", "city", "join_date", "id"]
ORDER_COLS = ["customer_id", "order_date", "amount", "status", "id"]


class QueryGenerator:
    def __init__(self):
        self.customer_cycle = CUSTOMER_COLS.copy()
        self.order_cycle = ORDER_COLS.copy()
        self.current_focus = {
            "customers": {"most": self.customer_cycle[0], "least": self.customer_cycle[-1]},
            "orders": {"most": self.order_cycle[0], "least": self.order_cycle[-1]},
        }

    def rotate_focus_once(self):
        """Rotate column focus in a predictable cycle"""
        self.customer_cycle = self.customer_cycle[1:] + self.customer_cycle[:1]
        self.order_cycle = self.order_cycle[1:] + self.order_cycle[:1]
        self.current_focus["customers"]["most"] = self.customer_cycle[0]
        self.current_focus["customers"]["least"] = self.customer_cycle[-1]
        self.current_focus["orders"]["most"] = self.order_cycle[0]
        self.current_focus["orders"]["least"] = self.order_cycle[-1]

    def generate(self):
        """Generate queries using Gaurav's logic"""
        qtype = random.random()
        table = random.choice(["customers", "orders"])
        focus_col = (
            self.current_focus[table]["most"]
            if random.random() < 0.7
            else self.current_focus[table]["least"]
        )

        if qtype <= 0.25:
            # INSERT
            if table == "customers":
                values = (
                    f"User{random.randint(1, 10000)}",
                    f"user{random.randint(1, 10000)}@mail.com",
                    random.choice(["Delhi", "Mumbai", "Pune", "Kolkata"]),
                    datetime.now().strftime("%Y-%m-%d"),
                )
                sql = "INSERT INTO customers (name, email, city, join_date) VALUES (?, ?, ?, ?)"
                params = values
            else:
                values = (
                    random.randint(1, 50),
                    datetime.now().strftime("%Y-%m-%d"),
                    round(random.uniform(500, 10000), 2),
                    random.choice(["Pending", "Shipped", "Delivered"]),
                )
                sql = "INSERT INTO orders (customer_id, order_date, amount, status) VALUES (?, ?, ?, ?)"
                params = values
            return sql, params

        elif qtype <= 0.45:
            # UPDATE
            value = f"Update{random.randint(100, 999)}"
            sql = f"UPDATE {table} SET {focus_col} = ? WHERE id = ?"
            params = (value, random.randint(1, 50))
            return sql, params

        elif qtype >= 0.95:
            # DELETE
            value = random.choice(["Delhi", "Mumbai", "Pending", "Delivered"])
            sql = f"DELETE FROM {table} WHERE {focus_col} = ?"
            params = (value,)
            return sql, params

        else:
            # SELECT
            if table == "customers":
                sql = f"SELECT * FROM customers WHERE {focus_col} = ?"
                params = (random.choice(["Delhi", "Pune", "Kolkata"]),)
            else:
                sql = f"SELECT * FROM orders WHERE {focus_col} > ? ORDER BY order_date DESC"
                params = (random.randint(1000, 8000),)
            return sql, params

    @staticmethod
    def format_sql(sql, params):
        """Format SQL with params for display (replacing ? placeholders)"""
        if not params:
            return sql

        parts = sql.split("?")
        if len(parts) == 1:
            return sql

        result = []
        for i, part in enumerate(parts):
            result.append(part)
            if i < len(params):
                param = params[i]
                if isinstance(param, str):
                    result.append(f"'{param}'")
                else:
                    result.append(str(param))
        return "".join(result)


# ------------------------ COLUMN / TABLE EXTRACTION ------------------------

TABLE_PATTERN = re.compile(
    r"(?:FROM|INTO|UPDATE|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
    re.IGNORECASE,
)

KEYWORDS = {
    "SELECT", "FROM", "WHERE", "AND", "OR", "AS", "ON", "IN",
    "VALUES", "SET", "BY", "GROUP", "ORDER", "COUNT", "SUM",
    "AVG", "MAX", "MIN", "DESC", "ASC",
}


def extract_columns(sql: str):
    """Extract column names from SQL"""
    cols = []
    sql_upper = sql.upper()

    # INSERT INTO table (col1, col2, ...) VALUES
    insert_match = re.search(r"INSERT\s+INTO\s+\w+\s*\((.*?)\)", sql_upper, re.IGNORECASE)
    if insert_match:
        col_list = insert_match.group(1)
        for col in re.split(r"[,\s]+", col_list):
            col = col.strip()
            if col and col.upper() not in KEYWORDS:
                cols.append(col.lower())

    # UPDATE table SET col1 = ..., col2 = ...
    update_match = re.search(r"UPDATE\s+\w+\s+SET\s+(.*?)(?:\s+WHERE|$)", sql_upper, re.IGNORECASE)
    if update_match:
        set_clause = update_match.group(1)
        for col in re.split(r"[,\s=]+", set_clause):
            col = col.strip()
            if col and col.upper() not in KEYWORDS:
                cols.append(col.lower())

    # SELECT col1, col2 FROM or SELECT * FROM
    select_match = re.search(r"SELECT\s+(.*?)\s+FROM", sql_upper, re.IGNORECASE)
    if select_match:
        select_list = select_match.group(1)
        if select_list.strip() != "*":
            for col in re.split(r"[,\s]+", select_list):
                col = col.strip().split(".")[-1]  # Handle table.column
                col = re.sub(r"\(.*?\)", "", col)  # Remove function calls
                if col and col.upper() not in KEYWORDS:
                    cols.append(col.lower())

    # WHERE clause
    where_match = re.search(r"WHERE\s+(.*?)(?:\s+ORDER|\s+GROUP|\s+LIMIT|$)", sql_upper, re.IGNORECASE)
    if where_match:
        where_clause = where_match.group(1)
        for col in re.split(r"[,\s=<>!]+", where_clause):
            col = col.strip().split(".")[-1]
            if col and col.upper() not in KEYWORDS:
                cols.append(col.lower())

    # ORDER BY
    order_match = re.search(r"ORDER\s+BY\s+(.*?)(?:\s+DESC|\s+ASC|\s+LIMIT|$)", sql_upper, re.IGNORECASE)
    if order_match:
        order_list = order_match.group(1)
        for col in re.split(r"[,\s]+", order_list):
            col = col.strip().split(".")[-1]
            if col and col.upper() not in KEYWORDS:
                cols.append(col.lower())

    # Dedup + filter
    cols = list(set([c for c in cols if c and not c.isdigit()]))
    return cols


def extract_table(sql: str):
    """Extract table name from SQL"""
    match = TABLE_PATTERN.search(sql)
    if match:
        return match.group(1).lower()
    return "unknown"
