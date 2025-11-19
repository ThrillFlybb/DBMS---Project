import threading
import time
import random
import os
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
        
        self.db_manager = db_manager
        self.query_generator = query_generator
        
        # Track query count for QPS calculation
        self.query_count = 0
        self.last_qps_time = time.time()
        self.query_times = deque(maxlen=100)  # Track last 100 query timestamps
        
        # Get current process for CPU/Memory tracking
        self.current_process = None
        if psutil:
            try:
                self.current_process = psutil.Process(os.getpid())
            except Exception:
                pass

        self._seed()

    def _seed(self):
        """Initialize with current database metrics"""
        db_size = self.db_manager.get_database_size()
        avg_latency = self.db_manager.get_average_latency() or 10.0
        
        for i in range(self.window):
            self.labels.append(f"t-{self.window - i}")
            self.qps.append(0)  # Will be calculated from actual queries
            self.latency.append(avg_latency)
            
            # Get process CPU/Memory if available
            if self.current_process:
                try:
                    cpu_val = self.current_process.cpu_percent(interval=0.1) or 0
                    mem_info = self.current_process.memory_info()
                    mem_val = (mem_info.rss / (1024 ** 3)) * 100  # Convert to GB then percentage (rough estimate)
                except Exception:
                    cpu_val = 0
                    mem_val = 0
            else:
                cpu_val = 0
                mem_val = 0
            
            self.cpu.append(max(0, min(100, cpu_val)))
            self.mem.append(max(0, min(100, mem_val)))
            self.storage.append(db_size)

    def tick(self):
        with self.lock:
            now_utc = datetime.now(timezone.utc)
            current_time = time.time()
            
            # query generation & execution
            query_executed = False
            query_latency = 0.0
            
            try:
                sql, params = self.query_generator.generate()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Execute in DB and get actual execution time
                try:
                    result, exec_time_ms = self.db_manager.execute(sql, params or ())
                    query_executed = True
                    query_latency = exec_time_ms
                    
                    # Track query time for QPS calculation
                    self.query_times.append(current_time)
                    self.query_count += 1
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
                    f.write(str(current_time))

            except Exception:
                pass

            # Calculate QPS from recent queries (last second)
            time_window = 1.0  # 1 second window
            recent_queries = [t for t in self.query_times if current_time - t <= time_window]
            qps_val = len(recent_queries)
            
            # Get actual latency from database manager
            avg_latency = self.db_manager.get_average_latency()
            if avg_latency > 0:
                lat_val = avg_latency
            elif query_latency > 0:
                lat_val = query_latency
            else:
                # Fallback to last known latency
                lat_val = self.latency[-1] if self.latency else 10.0

            # Get system-wide CPU and Memory usage (not just process)
            if psutil:
                try:
                    # CPU: system-wide CPU usage percentage
                    cpu_val = psutil.cpu_percent(interval=0.1) or 0
                    # Memory: system-wide memory usage percentage
                    system_mem = psutil.virtual_memory()
                    mem_val = system_mem.percent
                except Exception:
                    cpu_val = self.cpu[-1] if self.cpu else 0
                    mem_val = self.mem[-1] if self.mem else 0
            else:
                cpu_val = self.cpu[-1] if self.cpu else 0
                mem_val = self.mem[-1] if self.mem else 0

            # Get actual database file size
            db_size = self.db_manager.get_database_size()
            stor_val = db_size if db_size > 0 else (self.storage[-1] if self.storage else 0.0)

            # Update metrics
            self.labels.append(now_utc.strftime('%H:%M:%S'))
            self.qps.append(round(qps_val, 2))
            self.latency.append(round(lat_val, 2))
            self.cpu.append(round(max(0, min(100, cpu_val)), 2))
            self.mem.append(round(max(0, min(100, mem_val)), 2))
            self.storage.append(round(stor_val, 4))  # More precision for storage

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
