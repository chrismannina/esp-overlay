import threading

class AppState:
    """Encapsulates the shared state of the application."""
    def __init__(self):
        self.lock = threading.Lock()
        self._esp_enabled = True
        self._aim_assist_enabled = False
        self._program_running = True
        self._current_closest_target = None
        self._screen_center_x = -1
        self._screen_center_y = -1

    # Use properties with locks to ensure thread-safe access and modification
    @property
    def esp_enabled(self):
        with self.lock:
            return self._esp_enabled

    @esp_enabled.setter
    def esp_enabled(self, value):
        with self.lock:
            self._esp_enabled = value

    @property
    def aim_assist_enabled(self):
        with self.lock:
            return self._aim_assist_enabled

    @aim_assist_enabled.setter
    def aim_assist_enabled(self, value):
        with self.lock:
            self._aim_assist_enabled = value

    @property
    def program_running(self):
        with self.lock:
            return self._program_running

    @program_running.setter
    def program_running(self, value):
        with self.lock:
            # Ensure once set to False, it stays False
            if not value:
                self._program_running = False

    @property
    def current_closest_target(self):
        with self.lock:
            return self._current_closest_target

    @current_closest_target.setter
    def current_closest_target(self, value):
        with self.lock:
            self._current_closest_target = value

    @property
    def screen_center_x(self):
        with self.lock:
            return self._screen_center_x

    @screen_center_x.setter
    def screen_center_x(self, value):
        with self.lock:
            self._screen_center_x = value

    @property
    def screen_center_y(self):
        with self.lock:
            return self._screen_center_y

    @screen_center_y.setter
    def screen_center_y(self, value):
        with self.lock:
            self._screen_center_y = value

    def request_shutdown(self):
        """Signals the application to shut down."""
        self.program_running = False # Uses the setter logic 