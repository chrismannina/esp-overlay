import threading
import time
import math
from pynput import mouse
from utils import logger

# Constants (Can be moved to config_constants)
AIM_SENSITIVITY = 0.15
AIM_SLEEP_INTERVAL = 0.01

class AimAssist:
    """Handles the aim assist logic in a separate thread."""
    def __init__(self, app_state):
        self.app_state = app_state
        self._aim_thread = None
        self._mouse_controller = mouse.Controller()

    def _aim_assist_loop(self):
        logger.info("Aim assist thread started.")
        while self.app_state.program_running:
            target_to_aim = None
            aim_enabled_this_loop = False
            screen_center_x = -1
            screen_center_y = -1

            # Read necessary state variables safely
            # Using the properties defined in AppState handles the locking
            aim_enabled_this_loop = self.app_state.aim_assist_enabled
            if aim_enabled_this_loop:
                target_to_aim = self.app_state.current_closest_target
                screen_center_x = self.app_state.screen_center_x
                screen_center_y = self.app_state.screen_center_y

            # Perform aim logic if enabled and target exists
            if aim_enabled_this_loop and target_to_aim and screen_center_x > 0:
                try:
                    bbox = target_to_aim['bbox']
                    target_x = (bbox[0] + bbox[2]) // 2
                    target_y = (bbox[1] + bbox[3]) // 2

                    # Calculate vector from screen center to target center
                    delta_x = target_x - screen_center_x
                    delta_y = target_y - screen_center_y

                    # Simple proportional movement
                    move_x = int(delta_x * AIM_SENSITIVITY)
                    move_y = int(delta_y * AIM_SENSITIVITY)

                    # Only move if there's a significant enough delta
                    if abs(move_x) > 0 or abs(move_y) > 0:
                        self._mouse_controller.move(move_x, move_y)
                        # logger.debug(f"Aim Assist moving mouse by ({move_x}, {move_y})")

                except KeyError as e:
                    logger.error(f"Error accessing target data in aim assist: Missing key {e}")
                except Exception as e:
                    logger.error(f"Error in aim assist logic: {e}", exc_info=False)

            # Prevent tight loop, sleep even if not aiming
            time.sleep(AIM_SLEEP_INTERVAL)

        logger.info("Aim assist thread finished.")

    def start(self):
        if self._aim_thread is not None:
            logger.warning("Aim assist thread already running.")
            return
        self._aim_thread = threading.Thread(target=self._aim_assist_loop, name="AimAssistThread", daemon=True)
        self._aim_thread.start()

    def stop(self):
        logger.info("Stopping aim assist...")
        # Loop exits based on app_state.program_running
        if self._aim_thread and self._aim_thread.is_alive():
            self._aim_thread.join(timeout=1.0)
            if self._aim_thread.is_alive():
                logger.warning("Aim assist thread did not stop gracefully.")
        self._aim_thread = None
        logger.info("Aim assist stopped.") 