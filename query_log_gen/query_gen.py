import sqlite3
import threading
import queue
import time
import datetime
import random
import signal
import os

DB_PATH = "auto_index.db"
LOG_FILE = "query_log.txt"
STATUS_FILE = "generator_status.txt"
FLUSH_INTERVAL = 2
FOCUS_ROTATION_INTERVAL = 6  

q = queue.Queue()
log_buffer = []
buffer_lock = threading.Lock()
stop_event = threading.Event()

CUSTOMER_COLS = ["name", "email", "city", "join_date", "id"]
ORDER_COLS = ["customer_id", "order_date", "amount", "status", "id"]

customer_cycle = CUSTOMER_COLS.copy()
order_cycle = ORDER_COLS.copy()

current_focus = {
    "customers": {"most": customer_cycle[0], "least": customer_cycle[-1]},
    "orders": {"most": order_cycle[0], "least": order_cycle[-1]}
}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
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
    """)
    conn.commit()
    conn.close()


def rotate_focus():
    """Rotate column focus in a predictable cycle to show dynamic hot/cold changes."""
    global customer_cycle, order_cycle
    while not stop_event.is_set():
        time.sleep(FOCUS_ROTATION_INTERVAL)

        customer_cycle = customer_cycle[1:] + customer_cycle[:1]
        order_cycle = order_cycle[1:] + order_cycle[:1]

        current_focus["customers"]["most"] = customer_cycle[0]
        current_focus["customers"]["least"] = customer_cycle[-1]
        current_focus["orders"]["most"] = order_cycle[0]
        current_focus["orders"]["least"] = order_cycle[-1]

        print(f"\n[Pattern Shift]")
        print(f"  customers: most = {customer_cycle[0]}, least = {customer_cycle[-1]}")
        print(f"  orders:    most = {order_cycle[0]}, least = {order_cycle[-1]}\n")


def generate_query():
    """Generate queries biased toward the most/least used columns."""
    qtype = random.choice(["INSERT", "UPDATE", "DELETE", "SELECT"])
    table = random.choice(["customers", "orders"])

    focus_col = current_focus[table]["most"] if random.random() < 0.7 else current_focus[table]["least"]

    if qtype == "INSERT":
        if table == "customers":
            values = (f"User{random.randint(1,10000)}",
                      f"user{random.randint(1,10000)}@mail.com",
                      random.choice(["Delhi", "Mumbai", "Pune", "Kolkata"]),
                      datetime.datetime.now().strftime("%Y-%m-%d"))
            return ("INSERT INTO customers (name, email, city, join_date) VALUES (?, ?, ?, ?)", values)
        else:
            values = (random.randint(1, 50),
                      datetime.datetime.now().strftime("%Y-%m-%d"),
                      round(random.uniform(500, 10000), 2),
                      random.choice(["Pending", "Shipped", "Delivered"]))
            return ("INSERT INTO orders (customer_id, order_date, amount, status) VALUES (?, ?, ?, ?)", values)

    elif qtype == "UPDATE":
        value = f"Update{random.randint(100,999)}"
        return (f"UPDATE {table} SET {focus_col} = ? WHERE id = ?", (value, random.randint(1, 50)))

    elif qtype == "DELETE":
        value = random.choice(["Delhi", "Mumbai", "Pending", "Delivered"])
        return (f"DELETE FROM {table} WHERE {focus_col} = ?", (value,))

    else:  # SELECT
        if table == "customers":
            return (f"SELECT * FROM customers WHERE {focus_col} = ?", (random.choice(["Delhi", "Pune", "Kolkata"]),))
        else:
            return (f"SELECT * FROM orders WHERE {focus_col} > ? ORDER BY order_date DESC", (random.randint(1000, 8000),))


def db_worker():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    while not stop_event.is_set() or not q.empty():
        try:
            sql, params = q.get(timeout=0.1)
            cur.execute(sql, params or ())
            conn.commit()
            print(f"[EXECUTING] {sql} | {params}")
        except queue.Empty:
            continue
        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with buffer_lock:
                log_buffer.append(f"{timestamp} | {sql} | {params}\n")
            q.task_done()
    conn.close()


def flusher():
    while not stop_event.is_set():
        time.sleep(FLUSH_INTERVAL)
        with buffer_lock:
            if log_buffer:
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.writelines(log_buffer)
                log_buffer.clear()


def signal_handler(sig, frame):
    print("\nStopping generator...")
    stop_event.set()


def main():
    init_db()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    threading.Thread(target=db_worker, daemon=True).start()
    threading.Thread(target=flusher, daemon=True).start()
    threading.Thread(target=rotate_focus, daemon=True).start()

    print("Query generator running. Press Ctrl+C to stop.\n")

    try:
        while not stop_event.is_set():
            q.put(generate_query())
            with open(STATUS_FILE, "w") as f:
                f.write(str(time.time()))
            time.sleep(0.05)
    except KeyboardInterrupt:
        stop_event.set()

    q.join()
    time.sleep(FLUSH_INTERVAL + 0.2)
    with open(STATUS_FILE, "w") as f:
        f.write("STOP")
    time.sleep(0.3)
    os.remove(STATUS_FILE)
    print("Generator shutdown complete.")


if __name__ == "__main__":
    main()
