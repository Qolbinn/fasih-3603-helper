import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from config import LOGS_DIR

class AppLogger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AppLogger, cls).__new__(cls)
                cls._instance._init_logger()
            return cls._instance

    def _init_logger(self):
        self.callbacks = []
        self._file_lock = threading.Lock()
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.log_file = LOGS_DIR / f"fasih3603_{today_str}.log"

    def register_callback(self, cb):
        """Mendaftarkan fungsi callback untuk menerima log di UI (level, message, timestamp)."""
        if cb not in self.callbacks:
            self.callbacks.append(cb)

    def unregister_callback(self, cb):
        if cb in self.callbacks:
            self.callbacks.remove(cb)

    def log(self, level, message):
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        full_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{time_str}] [{level.upper()}] {message}"

        # Tulis ke terminal lokal
        print(formatted)

        # Tulis ke file log harian secara thread-safe
        try:
            with self._file_lock:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{full_time_str}] [{level.upper()}] {message}\n")
        except Exception:
            pass

        # Broadcast ke callback UI
        for cb in list(self.callbacks):
            try:
                cb(level.upper(), message, time_str)
            except Exception:
                pass

    def info(self, msg):
        self.log("INFO", msg)

    def bot(self, msg):
        self.log("BOT", msg)

    def success(self, msg):
        self.log("SUCCESS", msg)

    def remarks(self, msg):
        self.log("REMARKS", msg)

    def warning(self, msg):
        self.log("WARNING", msg)

    def error(self, msg):
        self.log("ERROR", msg)

    def debug(self, msg):
        self.log("DEBUG", msg)

logger = AppLogger()
