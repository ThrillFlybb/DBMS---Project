from flask import Flask, render_template, jsonify, request, redirect
import json
import os
from datetime import datetime, timezone, timedelta
import threading
import time
import random
from collections import deque, Counter
import requests
import sqlite3
import re
import queue
try:
	import psutil  # optional, for realistic cpu/memory
except Exception:
	psutil = None


app = Flask(__name__)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
QUERY_LOG_DIR = BASE_DIR
DB_PATH = os.path.join(QUERY_LOG_DIR, "auto_index.db")
LOG_FILE = os.path.join(QUERY_LOG_DIR, "query_log.txt")
STATUS_FILE = os.path.join(QUERY_LOG_DIR, "generator_status.txt")


def _read_json(filename, default):
	path = os.path.join(DATA_DIR, filename)
	try:
		with open(path, 'r', encoding='utf-8') as f:
			return json.load(f)
	except Exception:
		return default


def _write_json(filename, payload):
	path = os.path.join(DATA_DIR, filename)
	os.makedirs(DATA_DIR, exist_ok=True)
	with open(path, 'w', encoding='utf-8') as f:
		json.dump(payload, f, indent=2)


# ------------------------ GAURAV'S QUERY GENERATOR ------------------------

# Import Gaurav's query generator functions
CUSTOMER_COLS = ["name", "email", "city", "join_date", "id"]
ORDER_COLS = ["customer_id", "order_date", "amount", "status", "id"]

customer_cycle = CUSTOMER_COLS.copy()
order_cycle = ORDER_COLS.copy()

current_focus = {
	"customers": {"most": customer_cycle[0], "least": customer_cycle[-1]},
	"orders": {"most": order_cycle[0], "least": order_cycle[-1]}
}

def init_gaurav_db():
	"""Initialize Gaurav's database with customers and orders tables"""
	conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
	cur = conn.cursor()
	# Enable WAL mode for better concurrency
	cur.execute("PRAGMA journal_mode=WAL;")
	cur.executescript("""
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
	""")
	conn.commit()
	conn.close()

def rotate_focus():
	"""Rotate column focus in a predictable cycle"""
	global customer_cycle, order_cycle, current_focus
	while True:
		time.sleep(6)  # FOCUS_ROTATION_INTERVAL
		customer_cycle = customer_cycle[1:] + customer_cycle[:1]
		order_cycle = order_cycle[1:] + order_cycle[:1]
		current_focus["customers"]["most"] = customer_cycle[0]
		current_focus["customers"]["least"] = customer_cycle[-1]
		current_focus["orders"]["most"] = order_cycle[0]
		current_focus["orders"]["least"] = order_cycle[-1]

def generate_gaurav_query():
	"""Generate queries using Gaurav's logic"""
	qtype = random.choice(["INSERT", "UPDATE", "DELETE", "SELECT"])
	table = random.choice(["customers", "orders"])
	focus_col = current_focus[table]["most"] if random.random() < 0.7 else current_focus[table]["least"]
	
	if qtype == "INSERT":
		if table == "customers":
			values = (f"User{random.randint(1,10000)}",
					f"user{random.randint(1,10000)}@mail.com",
					random.choice(["Delhi", "Mumbai", "Pune", "Kolkata"]),
					datetime.now().strftime("%Y-%m-%d"))
			sql = "INSERT INTO customers (name, email, city, join_date) VALUES (?, ?, ?, ?)"
			params = values
		else:
			values = (random.randint(1, 50),
					datetime.now().strftime("%Y-%m-%d"),
					round(random.uniform(500, 10000), 2),
					random.choice(["Pending", "Shipped", "Delivered"]))
			sql = "INSERT INTO orders (customer_id, order_date, amount, status) VALUES (?, ?, ?, ?)"
			params = values
		return sql, params
	elif qtype == "UPDATE":
		value = f"Update{random.randint(100,999)}"
		sql = f"UPDATE {table} SET {focus_col} = ? WHERE id = ?"
		params = (value, random.randint(1, 50))
		return sql, params
	elif qtype == "DELETE":
		value = random.choice(["Delhi", "Mumbai", "Pending", "Delivered"])
		sql = f"DELETE FROM {table} WHERE {focus_col} = ?"
		params = (value,)
		return sql, params
	else:  # SELECT
		if table == "customers":
			sql = f"SELECT * FROM customers WHERE {focus_col} = ?"
			params = (random.choice(["Delhi", "Pune", "Kolkata"]),)
		else:
			sql = f"SELECT * FROM orders WHERE {focus_col} > ? ORDER BY order_date DESC"
			params = (random.randint(1000, 8000),)
		return sql, params

# Column extraction patterns for frequency counter
COLUMN_PATTERNS = [
	r"SELECT\s+(.*?)\s+FROM",
	r"WHERE\s+(.*?)\s*(?:GROUP|ORDER|LIMIT|;|$)",
	r"ORDER\s+BY\s+(.*?)\s*(?:LIMIT|;|$)",
	r"GROUP\s+BY\s+(.*?)\s*(?:ORDER|;|$)",
	r"SET\s+(.*?)\s*(?:WHERE|;|$)",
	r"INSERT\s+INTO\s+\w+\s*\((.*?)\)"
]
TABLE_PATTERN = r"(?:FROM|INTO|UPDATE|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)"

def extract_columns(sql):
	"""Extract column names from SQL"""
	cols = []
	sql_upper = sql.upper()
	
	# Handle INSERT INTO table (col1, col2, ...) VALUES
	insert_match = re.search(r"INSERT\s+INTO\s+\w+\s*\((.*?)\)", sql_upper, re.IGNORECASE)
	if insert_match:
		col_list = insert_match.group(1)
		for col in re.split(r"[,\s]+", col_list):
			col = col.strip()
			if col and col.upper() not in {"SELECT", "FROM", "WHERE", "AND", "OR", "AS", "ON", "IN", "VALUES", "SET", "BY", "GROUP", "ORDER"}:
				cols.append(col.lower())
	
	# Handle UPDATE table SET col1 = ..., col2 = ...
	update_match = re.search(r"UPDATE\s+\w+\s+SET\s+(.*?)(?:\s+WHERE|$)", sql_upper, re.IGNORECASE)
	if update_match:
		set_clause = update_match.group(1)
		for col in re.split(r"[,\s=]+", set_clause):
			col = col.strip()
			if col and col.upper() not in {"SELECT", "FROM", "WHERE", "AND", "OR", "AS", "ON", "IN", "VALUES", "SET", "BY", "GROUP", "ORDER"}:
				cols.append(col.lower())
	
	# Handle SELECT col1, col2 FROM or SELECT * FROM
	select_match = re.search(r"SELECT\s+(.*?)\s+FROM", sql_upper, re.IGNORECASE)
	if select_match:
		select_list = select_match.group(1)
		if select_list.strip() != "*":
			for col in re.split(r"[,\s]+", select_list):
				col = col.strip().split(".")[-1]  # Handle table.column format
				col = re.sub(r"\(.*?\)", "", col)  # Remove function calls
				if col and col.upper() not in {"SELECT", "FROM", "WHERE", "AND", "OR", "AS", "ON", "IN", "VALUES", "SET", "BY", "GROUP", "ORDER", "COUNT", "SUM", "AVG", "MAX", "MIN"}:
					cols.append(col.lower())
	
	# Handle WHERE clause columns
	where_match = re.search(r"WHERE\s+(.*?)(?:\s+ORDER|\s+GROUP|\s+LIMIT|$)", sql_upper, re.IGNORECASE)
	if where_match:
		where_clause = where_match.group(1)
		for col in re.split(r"[,\s=<>!]+", where_clause):
			col = col.strip().split(".")[-1]
			if col and col.upper() not in {"SELECT", "FROM", "WHERE", "AND", "OR", "AS", "ON", "IN", "VALUES", "SET", "BY", "GROUP", "ORDER"}:
				cols.append(col.lower())
	
	# Handle ORDER BY columns
	order_match = re.search(r"ORDER\s+BY\s+(.*?)(?:\s+DESC|\s+ASC|\s+LIMIT|$)", sql_upper, re.IGNORECASE)
	if order_match:
		order_list = order_match.group(1)
		for col in re.split(r"[,\s]+", order_list):
			col = col.strip().split(".")[-1]
			if col and col.upper() not in {"SELECT", "FROM", "WHERE", "AND", "OR", "AS", "ON", "IN", "VALUES", "SET", "BY", "GROUP", "ORDER", "DESC", "ASC"}:
				cols.append(col.lower())
	
	# Remove duplicates and filter
	cols = list(set([c for c in cols if c and len(c) > 0 and not c.isdigit()]))
	return cols

def extract_table(sql):
	"""Extract table name from SQL"""
	match = re.search(TABLE_PATTERN, sql, re.IGNORECASE)
	if match:
		return match.group(1).lower()
	return "unknown"

def update_frequency_counter(sql):
	"""Update frequency counter for columns in SQL"""
	max_retries = 3
	retry_delay = 0.1
	
	for attempt in range(max_retries):
		try:
			table_name = extract_table(sql)
			cols = extract_columns(sql)
			if not cols or table_name == "unknown":
				return
			
			conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5.0)
			cur = conn.cursor()
			
			# Create unique constraint if not exists
			try:
				cur.execute("""
					CREATE UNIQUE INDEX IF NOT EXISTS idx_freq_unique 
					ON attribute_frequency(table_name, column_name)
				""")
			except:
				pass
			
			for col in cols:
				# Try to update existing, if not exists, insert
				cur.execute("""
					UPDATE attribute_frequency 
					SET frequency = frequency + 1
					WHERE table_name = ? AND column_name = ?
				""", (table_name, col))
				
				if cur.rowcount == 0:
					cur.execute("""
						INSERT INTO attribute_frequency (table_name, column_name, frequency)
						VALUES (?, ?, 1)
					""", (table_name, col))
			
			conn.commit()
			conn.close()
			return  # Success, exit retry loop
		except sqlite3.OperationalError as e:
			if "locked" in str(e).lower() and attempt < max_retries - 1:
				time.sleep(retry_delay * (attempt + 1))
				continue
			else:
				pass
		except Exception as e:
			pass

def auto_manage_indexes():
	"""Gaurav's auto index management function"""
	max_retries = 3
	retry_delay = 0.1
	
	for attempt in range(max_retries):
		try:
			conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5.0)
			cur = conn.cursor()
			
			cur.execute("""
				SELECT table_name, column_name, frequency
				FROM attribute_frequency
				ORDER BY frequency DESC
			""")
			all_cols = cur.fetchall()
			
			if len(all_cols) < 3:
				conn.close()
				return
			
			top_three = all_cols[:3]
			bottom_six = all_cols[-6:]
			
			cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';")
			existing_indexes = {row[0] for row in cur.fetchall()}
			
			# Create indexes for top 3
			for table_name, column_name, _ in top_three:
				index_name = f"idx_{table_name}_{column_name}"
				if index_name not in existing_indexes:
					try:
						cur.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_name});")
					except Exception as e:
						pass
			
			# Drop indexes for bottom 6
			for table_name, column_name, _ in bottom_six:
				index_name = f"idx_{table_name}_{column_name}"
				if index_name in existing_indexes:
					try:
						cur.execute(f"DROP INDEX IF EXISTS {index_name};")
					except Exception as e:
						pass
			
			conn.commit()
			conn.close()
			return  # Success, exit retry loop
		except sqlite3.OperationalError as e:
			if "locked" in str(e).lower() and attempt < max_retries - 1:
				time.sleep(retry_delay * (attempt + 1))
				continue
			else:
				pass
		except Exception as e:
			pass

# ------------------------ OLD QUERY GENERATOR (DEPRECATED) ------------------------

class QueryGenerator:
	def __init__(self):
		# Define table schemas with realistic column types and constraints
		self.schemas = {
			"users": {
				"id": {"type": "int", "range": (1, 10000), "primary": True},
				"name": {"type": "string", "pattern": "name", "length": (3, 25)},
				"email": {"type": "string", "pattern": "email", "length": (10, 40)},
				"age": {"type": "int", "range": (18, 80)},
				"status": {"type": "enum", "values": ["active", "inactive", "pending", "suspended"]},
				"created_at": {"type": "date", "range": ("2020-01-01", "2024-12-31")},
				"is_premium": {"type": "boolean", "true_probability": 0.3}
			},
			"orders": {
				"id": {"type": "int", "range": (1, 50000), "primary": True},
				"user_id": {"type": "int", "range": (1, 10000), "foreign": "users.id"},
				"product_name": {"type": "string", "pattern": "product", "length": (5, 50)},
				"amount": {"type": "float", "range": (10.0, 2000.0), "decimals": 2},
				"status": {"type": "enum", "values": ["pending", "processing", "shipped", "delivered", "cancelled"]},
				"order_date": {"type": "date", "range": ("2023-01-01", "2024-12-31")},
				"quantity": {"type": "int", "range": (1, 10)}
			},
			"payments": {
				"id": {"type": "int", "range": (1, 75000), "primary": True},
				"order_id": {"type": "int", "range": (1, 50000), "foreign": "orders.id"},
				"amount": {"type": "float", "range": (10.0, 2000.0), "decimals": 2},
				"payment_method": {"type": "enum", "values": ["credit_card", "debit_card", "paypal", "bank_transfer"]},
				"status": {"type": "enum", "values": ["pending", "completed", "failed", "refunded"]},
				"transaction_date": {"type": "date", "range": ("2023-01-01", "2024-12-31")}
			},
			"audit_logs": {
				"id": {"type": "int", "range": (1, 100000), "primary": True},
				"user_id": {"type": "int", "range": (1, 10000), "foreign": "users.id"},
				"action": {"type": "enum", "values": ["login", "logout", "create", "update", "delete", "view"]},
				"table_name": {"type": "enum", "values": ["users", "orders", "payments", "audit_logs"]},
				"created_at": {"type": "date", "range": ("2023-01-01", "2024-12-31")},
				"ip_address": {"type": "string", "pattern": "ip", "length": (7, 15)}
			}
		}
		
		# Sample data for string generation
		self.name_samples = ["John", "Jane", "Mike", "Sarah", "David", "Lisa", "Chris", "Emma", "Alex", "Maria", "Tom", "Anna", "James", "Kate", "Ryan", "Sophie"]
		self.product_samples = ["Laptop", "Phone", "Tablet", "Headphones", "Camera", "Watch", "Book", "Shoes", "Shirt", "Bag", "Mouse", "Keyboard", "Monitor", "Speaker", "Charger"]
		self.email_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "company.com", "example.org"]
		
		# Query distribution weights
		self.query_weights = {"SELECT": 50, "INSERT": 20, "UPDATE": 20, "DELETE": 5}
	
	def _generate_string(self, pattern, length_range):
		"""Generate realistic string data based on pattern"""
		if pattern == "name":
			return random.choice(self.name_samples) + " " + random.choice(self.name_samples)
		elif pattern == "email":
			name = random.choice(self.name_samples).lower()
			domain = random.choice(self.email_domains)
			return f"{name}{random.randint(1, 999)}@{domain}"
		elif pattern == "product":
			base = random.choice(self.product_samples)
			variants = ["Pro", "Max", "Plus", "Standard", "Premium", "Basic", "Deluxe"]
			return f"{base} {random.choice(variants)}"
		elif pattern == "ip":
			return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
		else:
			# Generic string
			chars = "abcdefghijklmnopqrstuvwxyz"
			length = random.randint(length_range[0], length_range[1])
			return ''.join(random.choice(chars) for _ in range(length))
	
	def _generate_date(self, date_range):
		"""Generate random date within range"""
		start = datetime.strptime(date_range[0], "%Y-%m-%d")
		end = datetime.strptime(date_range[1], "%Y-%m-%d")
		delta = end - start
		random_days = random.randint(0, delta.days)
		return (start + timedelta(days=random_days)).strftime("%Y-%m-%d")
	
	def _generate_value(self, column_def):
		"""Generate a single value based on column definition"""
		col_type = column_def["type"]
		
		if col_type == "int":
			return random.randint(column_def["range"][0], column_def["range"][1])
		elif col_type == "float":
			value = random.uniform(column_def["range"][0], column_def["range"][1])
			return round(value, column_def.get("decimals", 2))
		elif col_type == "string":
			return self._generate_string(column_def["pattern"], column_def["length"])
		elif col_type == "enum":
			return random.choice(column_def["values"])
		elif col_type == "boolean":
			return random.random() < column_def.get("true_probability", 0.5)
		elif col_type == "date":
			return self._generate_date(column_def["range"])
		else:
			return "NULL"
	
	def generate_select_query(self, table_name):
		"""Generate realistic SELECT queries with various patterns"""
		schema = self.schemas[table_name]
		patterns = [
			"simple_select",      # SELECT * FROM table
			"where_like",         # SELECT * FROM table WHERE column LIKE '%pattern%'
			"where_range",        # SELECT * FROM table WHERE column BETWEEN x AND y
			"where_enum",         # SELECT * FROM table WHERE status = 'value'
			"count_query",        # SELECT COUNT(*) FROM table WHERE condition
			"join_query",         # SELECT * FROM table1 JOIN table2 ON condition
			"order_limit"         # SELECT * FROM table ORDER BY column LIMIT n
		]
		
		pattern = random.choice(patterns)
		
		if pattern == "simple_select":
			return f"SELECT * FROM {table_name} LIMIT {random.randint(10, 100)}"
		
		elif pattern == "where_like":
			string_cols = [col for col, defn in schema.items() if defn["type"] == "string" and defn.get("pattern") in ["name", "product"]]
			if string_cols:
				col = random.choice(string_cols)
				search_term = random.choice(self.name_samples if schema[col]["pattern"] == "name" else self.product_samples)
				return f"SELECT * FROM {table_name} WHERE {col} LIKE '%{search_term}%' LIMIT {random.randint(5, 50)}"
			else:
				return f"SELECT * FROM {table_name} LIMIT {random.randint(10, 100)}"
		
		elif pattern == "where_range":
			numeric_cols = [col for col, defn in schema.items() if defn["type"] in ["int", "float"]]
			if numeric_cols:
				col = random.choice(numeric_cols)
				col_def = schema[col]
				start_val = self._generate_value(col_def)
				end_val = self._generate_value(col_def)
				if start_val > end_val:
					start_val, end_val = end_val, start_val
				return f"SELECT * FROM {table_name} WHERE {col} BETWEEN {start_val} AND {end_val} LIMIT {random.randint(5, 50)}"
			else:
				return f"SELECT * FROM {table_name} LIMIT {random.randint(10, 100)}"
		
		elif pattern == "where_enum":
			enum_cols = [col for col, defn in schema.items() if defn["type"] == "enum"]
			if enum_cols:
				col = random.choice(enum_cols)
				value = random.choice(schema[col]["values"])
				return f"SELECT * FROM {table_name} WHERE {col} = '{value}' LIMIT {random.randint(5, 50)}"
			else:
				return f"SELECT * FROM {table_name} LIMIT {random.randint(10, 100)}"
		
		elif pattern == "count_query":
			enum_cols = [col for col, defn in schema.items() if defn["type"] == "enum"]
			if enum_cols:
				col = random.choice(enum_cols)
				value = random.choice(schema[col]["values"])
				return f"SELECT COUNT(*) FROM {table_name} WHERE {col} = '{value}'"
			else:
				return f"SELECT COUNT(*) FROM {table_name}"
		
		elif pattern == "join_query":
			# Simple join between related tables
			if table_name == "orders" and "user_id" in schema:
				return f"SELECT o.*, u.name FROM {table_name} o JOIN users u ON o.user_id = u.id LIMIT {random.randint(5, 30)}"
			elif table_name == "payments" and "order_id" in schema:
				return f"SELECT p.*, o.product_name FROM {table_name} p JOIN orders o ON p.order_id = o.id LIMIT {random.randint(5, 30)}"
			else:
				return f"SELECT * FROM {table_name} LIMIT {random.randint(10, 100)}"
		
		else:  # order_limit
			date_cols = [col for col, defn in schema.items() if defn["type"] == "date"]
			if date_cols:
				col = random.choice(date_cols)
				return f"SELECT * FROM {table_name} ORDER BY {col} DESC LIMIT {random.randint(5, 50)}"
			else:
				return f"SELECT * FROM {table_name} LIMIT {random.randint(10, 100)}"
	
	def generate_insert_query(self, table_name):
		"""Generate realistic INSERT queries"""
		schema = self.schemas[table_name]
		columns = []
		values = []
		
		for col_name, col_def in schema.items():
			if col_def.get("primary"):  # Skip auto-generated primary keys
				continue
			columns.append(col_name)
			values.append(self._generate_value(col_def))
		
		columns_str = ", ".join(columns)
		values_str = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in values])
		
		return f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str})"
	
	def generate_update_query(self, table_name):
		"""Generate realistic UPDATE queries"""
		schema = self.schemas[table_name]
		
		# Choose a column to update (not primary key)
		updatable_cols = [col for col, defn in schema.items() if not defn.get("primary")]
		if not updatable_cols:
			return f"SELECT * FROM {table_name} LIMIT 1"  # Fallback
		
		update_col = random.choice(updatable_cols)
		new_value = self._generate_value(schema[update_col])
		
		# Choose a condition column
		condition_cols = [col for col, defn in schema.items() if defn["type"] in ["int", "enum"]]
		if not condition_cols:
			return f"SELECT * FROM {table_name} LIMIT 1"  # Fallback
		
		condition_col = random.choice(condition_cols)
		condition_value = self._generate_value(schema[condition_col])
		
		value_str = f"'{new_value}'" if isinstance(new_value, str) else str(new_value)
		condition_str = f"'{condition_value}'" if isinstance(condition_value, str) else str(condition_value)
		
		return f"UPDATE {table_name} SET {update_col} = {value_str} WHERE {condition_col} = {condition_str}"
	
	def generate_delete_query(self, table_name):
		"""Generate realistic DELETE queries"""
		schema = self.schemas[table_name]
		
		# Choose a condition column
		condition_cols = [col for col, defn in schema.items() if defn["type"] in ["int", "enum", "date"]]
		if not condition_cols:
			return f"SELECT * FROM {table_name} LIMIT 1"  # Fallback
		
		condition_col = random.choice(condition_cols)
		condition_value = self._generate_value(schema[condition_col])
		
		condition_str = f"'{condition_value}'" if isinstance(condition_value, str) else str(condition_value)
		
		return f"DELETE FROM {table_name} WHERE {condition_col} = {condition_str}"
	
	def generate_query(self):
		"""Generate a random query based on distribution weights"""
		# Choose query type based on weights
		query_types = list(self.query_weights.keys())
		weights = list(self.query_weights.values())
		query_type = random.choices(query_types, weights=weights)[0]
		
		# Choose random table
		table_name = random.choice(list(self.schemas.keys()))
		
		# Generate appropriate query
		if query_type == "SELECT":
			sql = self.generate_select_query(table_name)
		elif query_type == "INSERT":
			sql = self.generate_insert_query(table_name)
		elif query_type == "UPDATE":
			sql = self.generate_update_query(table_name)
		elif query_type == "DELETE":
			sql = self.generate_delete_query(table_name)
		else:
			sql = f"SELECT * FROM {table_name} LIMIT 10"
		
		return {
			"type": query_type,
			"table": table_name,
			"sql": sql
		}


# ------------------------ REALTIME SIMULATOR ------------------------


class _RealtimeState:
	def __init__(self):
		self.lock = threading.Lock()
		self.window = 60  # keep last 60 points
		self.labels = deque(maxlen=self.window)
		self.qps = deque(maxlen=self.window)
		self.latency = deque(maxlen=self.window)
		self.cpu = deque(maxlen=self.window)
		self.mem = deque(maxlen=self.window)
		self.storage = deque(maxlen=self.window)
		self.storage_base = 221.0
		self.db_conn = None
		self._init_db_connection()
		self._seed()
	
	def _init_db_connection(self):
		"""Initialize database connection for query execution"""
		try:
			self.db_conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
			init_gaurav_db()
		except Exception as e:
			print(f"Error initializing DB: {e}")

	def _seed(self):
		for i in range(self.window):
			self.labels.append(f"t-{self.window - i}")
			base_qps = 150 + random.randint(-15, 15)
			self.qps.append(base_qps)
			self.latency.append(max(8, 35 - (base_qps - 120) * 0.08 + random.random() * 2))
			self.cpu.append(min(95, max(5, (psutil.cpu_percent() if psutil else 35) + random.randint(-3, 3))))
			self.mem.append(min(95, max(5, (psutil.virtual_memory().percent if psutil else 50) + random.randint(-1, 1))))
			self.storage.append(self.storage_base + i * 0.02)

	def tick(self):
		with self.lock:
			# metrics
			last_qps = self.qps[-1] if self.qps else 150
			qps_val = max(80, min(240, last_qps + random.randint(-6, 6)))
			lat_val = max(6, 40 - (qps_val - 100) * 0.09 + random.random() * 2)
			cpu_val = min(98, max(5, (psutil.cpu_percent() if psutil else (self.cpu[-1] if self.cpu else 40)) + random.randint(-2, 3)))
			mem_val = min(98, max(5, (psutil.virtual_memory().percent if psutil else (self.mem[-1] if self.mem else 52)) + random.randint(-1, 1)))
			stor_val = (self.storage[-1] if self.storage else self.storage_base) + (0.00 if random.random() < 0.6 else 0.02)
			self.labels.append(datetime.now(timezone.utc).strftime('%H:%M:%S'))
			self.qps.append(round(qps_val, 2))
			self.latency.append(round(lat_val, 2))
			self.cpu.append(round(cpu_val, 2))
			self.mem.append(round(mem_val, 2))
			self.storage.append(round(stor_val, 2))
			# write out metrics.json for visibility
			_write_json('metrics.json', {
				"timestamp": datetime.now(timezone.utc).isoformat(),
				"series": {
					"labels": list(self.labels),
					"qps": list(self.qps),
					"latencyMs": list(self.latency),
					"cpu": list(self.cpu),
					"memory": list(self.mem),
					"storageGb": list(self.storage)
				}
			})
			# Generate query using Gaurav's generator
			try:
				sql, params = generate_gaurav_query()
				timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
				
				# Execute query in database
				if self.db_conn:
					try:
						cur = self.db_conn.cursor()
						cur.execute(sql, params or ())
						self.db_conn.commit()
					except sqlite3.OperationalError as e:
						# If locked, try to reconnect
						if "locked" in str(e).lower():
							try:
								self.db_conn.close()
							except:
								pass
							try:
								self.db_conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
							except:
								pass
					except Exception as e:
						pass
				
				# Format SQL with params for display
				formatted_sql = sql
				if params:
					# Replace ? placeholders with actual values (handle multiple ?)
					parts = formatted_sql.split('?')
					if len(parts) > 1:
						result = []
						for i, part in enumerate(parts):
							result.append(part)
							if i < len(params):
								param = params[i]
								if isinstance(param, str):
									result.append(f"'{param}'")
								else:
									result.append(str(param))
						formatted_sql = ''.join(result)
				
				# Update frequency counter
				update_frequency_counter(formatted_sql)
				
				# Write to log file
				log_entry = f"{timestamp} | {formatted_sql} | {params}\n"
				with open(LOG_FILE, "a", encoding="utf-8") as f:
					f.write(log_entry)
				
				# Update status file
				with open(STATUS_FILE, "w") as f:
					f.write(str(time.time()))
			except Exception as e:
				pass


STATE = _RealtimeState()


def _start_simulator_thread():
	def _loop():
		while True:
			try:
				STATE.tick()
			except Exception:
				pass
			time.sleep(1)
	thr = threading.Thread(target=_loop, daemon=True)
	thr.start()

def _start_index_manager_thread():
	"""Auto-manage indexes every 10 seconds"""
	def _loop():
		while True:
			try:
				time.sleep(10)
				auto_manage_indexes()
			except Exception:
				pass
	thr = threading.Thread(target=_loop, daemon=True)
	thr.start()

def _start_focus_rotation_thread():
	"""Rotate column focus every 6 seconds"""
	thr = threading.Thread(target=rotate_focus, daemon=True)
	thr.start()


@app.route('/')
def index():
	return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
	return render_template('dashboard.html')


@app.route('/queries')
def queries_page():
	return render_template('queries.html')




@app.route('/settings')
def settings_page():
	settings = _read_json('settings.json', {
		"db": {"host": "localhost", "port": 5432, "user": "admin", "database": "app"},
		"refreshIntervalMs": 5000,
		"dataSource": "json"
	})
	return render_template('settings.html', settings=settings)


@app.route('/statistics')
def statistics_page():
	return render_template('statistics.html')


# ------------------------ API ENDPOINTS ------------------------


@app.route('/api/metrics')
def api_metrics():
	settings = _read_json('settings.json', {"dataSource": "json", "backendBaseUrl": ""})
	if settings.get('dataSource') == 'rest' and settings.get('backendBaseUrl'):
		try:
			res = requests.get(settings['backendBaseUrl'].rstrip('/') + '/metrics', timeout=3)
			return jsonify(res.json())
		except Exception:
			pass
	data = _read_json('metrics.json', {"timestamp": datetime.now(timezone.utc).isoformat(), "series": {"labels": [], "qps": [], "latencyMs": [], "cpu": [], "memory": [], "storageGb": []}})
	return jsonify(data)


@app.route('/api/queries')
def api_queries():
	"""Read queries from query_log.txt (last 20) or REST backend"""
	settings = _read_json('settings.json', {"dataSource": "json", "backendBaseUrl": ""})
	if settings.get('dataSource') == 'rest' and settings.get('backendBaseUrl'):
		try:
			page = int(request.args.get('page', 1))
			page_size = int(request.args.get('pageSize', 20))
			search = request.args.get('search', '').strip()
			url = f"{settings['backendBaseUrl'].rstrip('/')}/queries?page={page}&pageSize={page_size}&search={search}"
			res = requests.get(url, timeout=3)
			return jsonify(res.json())
		except Exception:
			pass
	
	try:
		items = []
		if os.path.exists(LOG_FILE):
			with open(LOG_FILE, "r", encoding="utf-8") as f:
				lines = f.readlines()
				# Get last 20 lines
				for line in lines[-20:]:
					parts = line.strip().split("|")
					if len(parts) >= 2:
						timestamp = parts[0].strip()
						sql = parts[1].strip()
						params = parts[2].strip() if len(parts) > 2 else ""
						
						# Extract query type
						sql_upper = sql.upper()
						if sql_upper.startswith("SELECT"):
							qtype = "SELECT"
						elif sql_upper.startswith("INSERT"):
							qtype = "INSERT"
						elif sql_upper.startswith("UPDATE"):
							qtype = "UPDATE"
						elif sql_upper.startswith("DELETE"):
							qtype = "DELETE"
						else:
							qtype = "UNKNOWN"
						
						# Extract table
						table = extract_table(sql)
						
						items.append({
							"timestamp": timestamp,
							"latencyMs": round(max(5, random.gauss(20, 6)), 2),
							"database": "app",
							"sql": sql,
							"type": qtype,
							"table": table
						})
		
		# Reverse to show newest first
		items.reverse()
		
		# Apply search filter
		search = request.args.get('search', '').lower().strip()
		if search:
			items = [q for q in items if search in q.get('sql', '').lower()]
		
		# Pagination
		page = int(request.args.get('page', 1))
		page_size = int(request.args.get('pageSize', 20))
		total = len(items)
		start = (page - 1) * page_size
		end = start + page_size
		
		return jsonify({"items": items[start:end], "total": total, "page": page, "pageSize": page_size})
	except Exception as e:
		return jsonify({"items": [], "total": 0, "page": 1, "pageSize": 20})




@app.route('/api/statistics')
def api_statistics():
	"""Generate query statistics including column frequency"""
	import traceback
	settings = _read_json('settings.json', {"dataSource": "json", "backendBaseUrl": ""})
	if settings.get('dataSource') == 'rest' and settings.get('backendBaseUrl'):
		try:
			res = requests.get(settings['backendBaseUrl'].rstrip('/') + '/statistics', timeout=3)
			return jsonify(res.json())
		except Exception:
			pass
	
	try:
		# Get column frequency from database
		column_frequency = []
		total_freq = 0
		if os.path.exists(DB_PATH):
			max_retries = 3
			retry_delay = 0.1
			for attempt in range(max_retries):
				try:
					conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5.0)
					cur = conn.cursor()
					cur.execute("""
						SELECT table_name, column_name, frequency
						FROM attribute_frequency
						ORDER BY frequency DESC
					""")
					rows = cur.fetchall()
					for table_name, column_name, frequency in rows:
						column_frequency.append({
							"table": table_name,
							"column": column_name,
							"frequency": frequency
						})
						total_freq += frequency
					conn.close()
					break  # Success, exit retry loop
				except sqlite3.OperationalError as e:
					if "locked" in str(e).lower() and attempt < max_retries - 1:
						time.sleep(retry_delay * (attempt + 1))
						continue
					else:
						break
				except Exception as e:
					break
		
		# Calculate percentages
		for item in column_frequency:
			item["percent"] = round((item["frequency"] / total_freq * 100), 2) if total_freq > 0 else 0
		
		# Get current indexes
		current_indexes = []
		if os.path.exists(DB_PATH):
			max_retries = 3
			retry_delay = 0.1
			for attempt in range(max_retries):
				try:
					conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5.0)
					cur = conn.cursor()
					cur.execute("""
						SELECT name, tbl_name, sql
						FROM sqlite_master
						WHERE type='index' AND name NOT LIKE 'sqlite_%'
					""")
					for name, tbl_name, sql in cur.fetchall():
						current_indexes.append({
							"name": name,
							"table": tbl_name,
							"sql": sql
						})
					conn.close()
					break  # Success, exit retry loop
				except sqlite3.OperationalError as e:
					if "locked" in str(e).lower() and attempt < max_retries - 1:
						time.sleep(retry_delay * (attempt + 1))
						continue
					else:
						break
				except Exception as e:
					break
		
		# Read queries from log file for query type and table usage
		query_types = {}
		table_usage = {}
		if os.path.exists(LOG_FILE):
			with open(LOG_FILE, "r", encoding="utf-8") as f:
				lines = f.readlines()
				for line in lines:
					parts = line.strip().split("|")
					if len(parts) >= 2:
						sql = parts[1].strip()
						sql_upper = sql.upper()
						
						# Query type
						if sql_upper.startswith("SELECT"):
							qtype = "SELECT"
						elif sql_upper.startswith("INSERT"):
							qtype = "INSERT"
						elif sql_upper.startswith("UPDATE"):
							qtype = "UPDATE"
						elif sql_upper.startswith("DELETE"):
							qtype = "DELETE"
						else:
							qtype = "UNKNOWN"
						query_types[qtype] = query_types.get(qtype, 0) + 1
						
						# Table usage
						table = extract_table(sql)
						table_usage[table] = table_usage.get(table, 0) + 1
		
		return jsonify({
			"query_types": query_types,
			"table_usage": table_usage,
			"column_frequency": column_frequency,
			"current_indexes": current_indexes,
			"total_queries": sum(query_types.values())
		})
	except Exception as e:
		error_msg = str(e)
		print(f"Error in api_statistics: {error_msg}")
		print(traceback.format_exc())
		return jsonify({
			"query_types": {},
			"table_usage": {},
			"column_frequency": [],
			"current_indexes": [],
			"total_queries": 0,
			"error": error_msg
	})


@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
	if request.method == 'GET':
		settings = _read_json('settings.json', {
			"db": {"host": "localhost", "port": 5432, "user": "admin", "database": "app"},
			"refreshIntervalMs": 5000,
			"dataSource": "json"
		})
		return jsonify(settings)
	else:
		payload = request.get_json(silent=True) or {}
		_write_json('settings.json', payload)
		return jsonify({"ok": True})


if __name__ == '__main__':
	# Initialize database
	init_gaurav_db()
	
	# Start background threads
	_start_simulator_thread()
	_start_index_manager_thread()
	_start_focus_rotation_thread()
	
	port = int(os.environ.get('PORT', 5000))
	use_waitress = os.environ.get('USE_WAITRESS', '0') == '1'
	if use_waitress:
		from waitress import serve
		serve(app, host='0.0.0.0', port=port)
	else:
		app.run(host='0.0.0.0', port=port, debug=True)
