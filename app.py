from flask import Flask, render_template, jsonify, request, redirect
import json
import os
from datetime import datetime, timezone, timedelta
import threading
import time
import random
from collections import deque
import requests
try:
	import psutil  # optional, for realistic cpu/memory
except Exception:
	psutil = None


app = Flask(__name__)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')


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


# ------------------------ QUERY GENERATOR ------------------------

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
		self.queries = deque(maxlen=200)
		self.storage_base = 221.0
		self.query_generator = QueryGenerator()  # Initialize query generator
		self._seed()

	def _seed(self):
		for i in range(self.window):
			self.labels.append(f"t-{self.window - i}")
			base_qps = 150 + random.randint(-15, 15)
			self.qps.append(base_qps)
			self.latency.append(max(8, 35 - (base_qps - 120) * 0.08 + random.random() * 2))
			self.cpu.append(min(95, max(5, (psutil.cpu_percent() if psutil else 35) + random.randint(-3, 3))))
			self.mem.append(min(95, max(5, (psutil.virtual_memory().percent if psutil else 50) + random.randint(-1, 1))))
			self.storage.append(self.storage_base + i * 0.02)
		for q in _read_json('queries.json', {"items": []}).get('items', []):
			self.queries.append(q)

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
			# benchmarks derived from recent latency window
			lat = list(self.latency)[-30:]
			if lat:
				baseline = [round(v + 8 + random.random()*1.5, 2) for v in lat]
				optimized = [round(max(1, v - 2 - random.random()*1.0), 2) for v in lat]
				_write_json('benchmarks.json', {"baseline": {"latencyMs": baseline}, "optimized": {"latencyMs": optimized}})
			# append a query log entry using the new QueryGenerator
			generated_query = self.query_generator.generate_query()
			self.queries.append({
				"timestamp": datetime.now(timezone.utc).isoformat(),
				"latencyMs": round(max(5, random.gauss(20, 6)), 2),
				"database": random.choice(["app","analytics","payments"]),
				"sql": generated_query["sql"],
				"type": generated_query["type"],
				"table": generated_query["table"]
			})
			_write_json('queries.json', {"items": list(self.queries)})


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


@app.route('/')
def index():
	return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
	return render_template('dashboard.html')


@app.route('/queries')
def queries_page():
	return render_template('queries.html')


@app.route('/performance')
def performance_page():
	return render_template('performance.html')


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
	page = int(request.args.get('page', 1))
	page_size = int(request.args.get('pageSize', 20))
	search = request.args.get('search', '').lower().strip()
	settings = _read_json('settings.json', {"dataSource": "json", "backendBaseUrl": ""})
	if settings.get('dataSource') == 'rest' and settings.get('backendBaseUrl'):
		try:
			res = requests.get(settings['backendBaseUrl'].rstrip('/') + f"/queries?page={page}&pageSize={page_size}&search={search}", timeout=3)
			return jsonify(res.json())
		except Exception:
			pass
	data = _read_json('queries.json', {"items": []})
	items = data.get('items', [])
	if search:
		items = [q for q in items if search in q.get('sql', '').lower()]
	total = len(items)
	start = (page - 1) * page_size
	end = start + page_size
	return jsonify({"items": items[start:end], "total": total, "page": page, "pageSize": page_size})


@app.route('/api/benchmarks')
def api_benchmarks():
	settings = _read_json('settings.json', {"dataSource": "json", "backendBaseUrl": ""})
	if settings.get('dataSource') == 'rest' and settings.get('backendBaseUrl'):
		try:
			res = requests.get(settings['backendBaseUrl'].rstrip('/') + '/benchmarks', timeout=3)
			return jsonify(res.json())
		except Exception:
			pass
	data = _read_json('benchmarks.json', {"baseline": {"latencyMs": []}, "optimized": {"latencyMs": []}})
	return jsonify(data)


@app.route('/api/statistics')
def api_statistics():
	"""Generate query statistics from recent queries"""
	queries_data = _read_json('queries.json', {"items": []})
	items = queries_data.get('items', [])
	
	if not items:
		return jsonify({
			"query_types": {},
			"table_usage": {},
			"hourly_distribution": {},
			"query_complexity": {},
			"total_queries": 0
		})
	
	# Analyze query types
	query_types = {}
	table_usage = {}
	hourly_distribution = {}
	query_complexity = {"simple": 0, "medium": 0, "complex": 0}
	
	for item in items:
		# Query type analysis
		query_type = item.get('type', 'UNKNOWN')
		query_types[query_type] = query_types.get(query_type, 0) + 1
		
		# Table usage analysis
		table = item.get('table', 'unknown')
		table_usage[table] = table_usage.get(table, 0) + 1
		
		# Hourly distribution
		try:
			timestamp = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
			hour = timestamp.hour
			hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
		except:
			pass
		
		# Query complexity analysis
		sql = item.get('sql', '').upper()
		if any(keyword in sql for keyword in ['JOIN', 'GROUP BY', 'HAVING', 'SUBQUERY']):
			query_complexity["complex"] += 1
		elif any(keyword in sql for keyword in ['WHERE', 'ORDER BY', 'LIMIT']):
			query_complexity["medium"] += 1
		else:
			query_complexity["simple"] += 1
	
	# Sort hourly distribution
	hourly_distribution = dict(sorted(hourly_distribution.items()))
	
	return jsonify({
		"query_types": query_types,
		"table_usage": table_usage,
		"hourly_distribution": hourly_distribution,
		"query_complexity": query_complexity,
		"total_queries": len(items)
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
	# start realtime simulator
	_start_simulator_thread()
	port = int(os.environ.get('PORT', 5000))
	use_waitress = os.environ.get('USE_WAITRESS', '0') == '1'
	if use_waitress:
		from waitress import serve
		serve(app, host='0.0.0.0', port=port)
	else:
		app.run(host='0.0.0.0', port=port, debug=True)
