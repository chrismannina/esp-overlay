import threading
import time
from pynput import keyboard
from utils import logger

# Define Hotkeys (Can be moved to config_constants if preferred)
ESP_TOGGLE_KEY = keyboard.Key.f1
AIM_TOGGLE_KEY = keyboard.Key.f2
EXIT_KEY = keyboard.Key.f4

class InputHandler:
    """Handles keyboard input for toggling features and exiting."""
    def __init__(self, app_state):
        self.app_state = app_state
        self._listener_thread = None
        self._listener = None

    def _on_press(self, key):
        try:
            # Access state via the app_state instance
            if key == ESP_TOGGLE_KEY:
                current_state = self.app_state.esp_enabled
                self.app_state.esp_enabled = not current_state
                logger.info(f"ESP {'ENABLED' if not current_state else 'DISABLED'}")
            elif key == AIM_TOGGLE_KEY:
                current_state = self.app_state.aim_assist_enabled
                self.app_state.aim_assist_enabled = not current_state
                logger.info(f"Aim Assist {'ENABLED' if not current_state else 'DISABLED'}")
            elif key == EXIT_KEY:
                logger.info("Exit key pressed. Initiating shutdown...")
                self.app_state.request_shutdown() # Use the method in AppState

        except AttributeError:
            # Handle non-special keys if necessary
            pass
        except Exception as e:
             logger.error(f"Error in _on_press: {e}")

    def _listener_loop(self):
        logger.info(f"Starting keyboard listener. Press {ESP_TOGGLE_KEY} to toggle ESP, {AIM_TOGGLE_KEY} to toggle Aim Assist, {EXIT_KEY} to exit.")
        # Setup the listener in this thread
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.start()
        logger.info("Keyboard listener started.")

        # Keep the thread alive while the listener is running and program hasn't exited
        while self.app_state.program_running and self._listener.is_alive():
            time.sleep(0.1)

        logger.info("Keyboard listener loop exiting.")
        if self._listener and self._listener.is_alive():
             self._listener.stop()

    def start(self):
        if self._listener_thread is not None:
            logger.warning("Input listener thread already running.")
            return
        # Start the listener loop in a separate thread
        self._listener_thread = threading.Thread(target=self._listener_loop, name="KeyboardListenerThread", daemon=True)
        self._listener_thread.start()

    def stop(self):
        logger.info("Stopping input handler...")
        # The loop will exit based on app_state.program_running
        # We just need to wait for the thread to finish
        if self._listener_thread and self._listener_thread.is_alive():
             self._listener_thread.join(timeout=1.0)
             if self._listener_thread.is_alive():
                  logger.warning("Keyboard listener thread did not stop gracefully.")
        self._listener_thread = None
        logger.info("Input handler stopped.") 