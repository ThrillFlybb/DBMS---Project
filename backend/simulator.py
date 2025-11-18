import threading
import time
import random
from collections import deque
from datetime import datetime, timezone

from backend.config import psutil, write_json, DB_PATH, LOG_FILE, STATUS_FILE
from backend.db_manager import DBManager
from backend.query_generator import QueryGenerator


class MetricsSimulator:
    def __init__(self, db_manager: DBManager, query_generator: QueryGenerator, window: int = 60):
        self.lock = threading.Lock()
        self.window = window
        self.labels = deque(maxlen=self.window)
        self.qps = deque(maxlen=self.window)
        self.latency = deque(maxlen=self.window)
        self.cpu = deque(maxlen=self.window)
        self.mem = deque(maxlen=self.window)
        self.storage = deque(maxlen=self.window)
        self.storage_base = 1.0

        self.db_manager = db_manager
        self.query_generator = query_generator

        self._seed()

    def _seed(self):
        for i in range(self.window):
            self.labels.append(f"t-{self.window - i}")
            base_qps = 150 + random.randint(-15, 15)
            self.qps.append(base_qps)
            self.latency.append(
                max(8, 35 - (base_qps - 120) * 0.08 + random.random() * 2)
            )
            cpu_base = psutil.cpu_percent() if psutil else 35
            mem_base = psutil.virtual_memory().percent if psutil else 50
            self.cpu.append(min(95, max(5, cpu_base + random.randint(-3, 3))))
            self.mem.append(min(95, max(5, mem_base + random.randint(-1, 1))))
            self.storage.append(self.storage_base + i * 0.02)

    def tick(self):
        with self.lock:
            # metrics
            last_qps = self.qps[-1] if self.qps else 150
            qps_val = max(80, min(240, last_qps + random.randint(-6, 6)))
            lat_val = max(6, 40 - (qps_val - 100) * 0.09 + random.random() * 2)

            cpu_base = (
                psutil.cpu_percent()
                if psutil
                else (self.cpu[-1] if self.cpu else 40)
            )
            mem_base = (
                psutil.virtual_memory().percent
                if psutil
                else (self.mem[-1] if self.mem else 52)
            )

            cpu_val = min(98, max(5, cpu_base + random.randint(-2, 3)))
            mem_val = min(98, max(5, mem_base + random.randint(-1, 1)))
            stor_val = (
                self.storage[-1] if self.storage else self.storage_base
            ) + (0.00 if random.random() < 0.6 else 0.02)

            now_utc = datetime.now(timezone.utc)
            self.labels.append(now_utc.strftime('%H:%M:%S'))
            self.qps.append(round(qps_val, 2))
            self.latency.append(round(lat_val, 2))
            self.cpu.append(round(cpu_val, 2))
            self.mem.append(round(mem_val, 2))
            self.storage.append(round(stor_val, 2))

            # write metrics.json
            write_json(
                'metrics.json',
                {
                    "timestamp": now_utc.isoformat(),
                    "series": {
                        "labels": list(self.labels),
                        "qps": list(self.qps),
                        "latencyMs": list(self.latency),
                        "cpu": list(self.cpu),
                        "memory": list(self.mem),
                        "storageGb": list(self.storage),
                    },
                },
            )

            # query generation & execution
            try:
                sql, params = self.query_generator.generate()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Execute in DB
                try:
                    self.db_manager.execute(sql, params or ())
                except Exception:
                    pass

                # Format SQL for logging & frequency
                formatted_sql = self.query_generator.format_sql(sql, params)
                try:
                    self.db_manager.update_frequency_counter(formatted_sql)
                except Exception:
                    pass

                # Write log
                log_entry = f"{timestamp} | {formatted_sql} | {params}\n"
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(log_entry)

                # Update status file
                with open(STATUS_FILE, "w") as f:
                    f.write(str(time.time()))

            except Exception:
                pass


# Singletons
db_manager = DBManager(DB_PATH)
query_generator = QueryGenerator()
simulator = MetricsSimulator(db_manager, query_generator)


def start_simulator_thread(interval_sec: float = 0.001):
    """Run tick loop; 0.001s ≈ 1000 ticks/sec (subject to reality)."""
    def _loop():
        while True:
            try:
                time.sleep(0.0005)
                simulator.tick()
            except Exception:
                pass
            time.sleep(interval_sec)

    thr = threading.Thread(target=_loop, daemon=True)
    thr.start()


def start_index_manager_thread():
    """Auto-manage indexes every 10 seconds."""
    def _loop():
        while True:
            try:
                time.sleep(10)
                db_manager.auto_manage_indexes()
            except Exception:
                pass

    thr = threading.Thread(target=_loop, daemon=True)
    thr.start()


def start_focus_rotation_thread():
    """Rotate column focus every 6 seconds."""
    def _loop():
        while True:
            try:
                time.sleep(6)
                query_generator.rotate_focus_once()
            except Exception:
                pass

    thr = threading.Thread(target=_loop, daemon=True)
    thr.start()
