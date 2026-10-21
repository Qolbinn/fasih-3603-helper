import queue
import threading
import time

class EngineState:
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    WAITING_CONFIRM_SUBMIT = "WAITING_CONFIRM_SUBMIT"

class EventBus:
    def __init__(self):
        self.ui_queue = queue.Queue()
        self._pause_event = threading.Event()
        self._pause_event.set() # Set = not paused (running)
        self._stop_event = threading.Event()
        self._submit_confirm_event = threading.Event()
        self._auth_confirm_event = threading.Event()
        self._state = EngineState.IDLE
        self._state_lock = threading.Lock()

    def set_state(self, new_state):
        with self._state_lock:
            self._state = new_state
            self.emit("state_changed", {"state": new_state})

    def get_state(self):
        with self._state_lock:
            return self._state

    def emit(self, event_type, payload):
        """Mengirim event dari background thread ke antrian UI."""
        self.ui_queue.put((event_type, payload))

    def poll_events(self):
        """Mengambil seluruh event yang terkumpul di antrian UI."""
        events = []
        while not self.ui_queue.empty():
            try:
                events.append(self.ui_queue.get_nowait())
            except queue.Empty:
                break
        return events

    # Control methods
    def request_pause(self):
        self._pause_event.clear()
        self.set_state(EngineState.PAUSED)

    def request_resume(self):
        self._pause_event.set()
        self.set_state(EngineState.RUNNING)

    def request_stop(self):
        self._stop_event.set()
        self._pause_event.set() # Unpause to allow loop to exit immediately
        self._submit_confirm_event.set()
        self.set_state(EngineState.STOPPING)

    def reset_controls(self):
        self._pause_event.set()
        self._stop_event.clear()
        self._submit_confirm_event.clear()
        self._auth_confirm_event.clear()
        self.set_state(EngineState.IDLE)

    def is_stop_requested(self):
        return self._stop_event.is_set()

    def is_paused(self):
        return not self._pause_event.is_set()

    def wait_if_paused(self, poll_interval=0.1):
        """Dipanggil di dalam worker thread: jika di-pause, akan memblokir thread secara responsif hingga di-resume atau stop."""
        while self.is_paused() and not self.is_stop_requested():
            self._pause_event.wait(timeout=poll_interval)

    def wait_for_submit_confirmation(self, poll_interval=0.1):
        """Dipanggil di mode review/debug: memblokir worker thread sampai tombol konfirmasi diklik atau stop."""
        self.set_state(EngineState.WAITING_CONFIRM_SUBMIT)
        self._submit_confirm_event.clear()
        while not self._submit_confirm_event.is_set() and not self.is_stop_requested():
            self._submit_confirm_event.wait(timeout=poll_interval)
        if not self.is_stop_requested():
            self.set_state(EngineState.RUNNING)

    def is_waiting_confirm_submit(self):
        return self.get_state() == EngineState.WAITING_CONFIRM_SUBMIT

    def confirm_submit(self):
        """Dipanggil dari UI saat tombol 'Konfirmasi Submit & Lanjut' diklik atau tombol Enter ditekan."""
        self._submit_confirm_event.set()

    def confirm_auth_login(self):
        """Dipanggil dari UI saat pengguna mengonfirmasi manual bahwa sudah login di browser."""
        self._auth_confirm_event.set()

    def reset_auth_confirmation(self):
        """Mereset status konfirmasi login manual."""
        self._auth_confirm_event.clear()

    def is_auth_confirmed(self):
        """Memeriksa apakah ada konfirmasi manual login dari pengguna."""
        return self._auth_confirm_event.is_set()
