# main.py
import time
import threading
from queue import Queue, Empty
import sys
import math # Added for aim assist calculation

# Input handling
from pynput import keyboard, mouse

from utils import logger
from state import AppState
from capture import get_capture_source
from processing import AIProcessor
from overlay import OverlayRenderer
from input_handler import InputHandler
from aim_assist import AimAssist

# Import constants
from config_constants import (
    CONFIG_CAPTURE_TYPE, CONFIG_DEVICE_INDEX, CONFIG_RESOLUTION, CONFIG_FPS,
    CONFIG_MONITOR, CONFIG_REGION, CONFIG_MODEL_PATH, CONFIG_CONF_THRESHOLD,
    CONFIG_NMS_THRESHOLD, CONFIG_CLASSES_TO_DETECT, CONFIG_SHOW_FPS,
    CONFIG_WINDOW_TITLE, CONFIG_FRAME_QUEUE_SIZE, CONFIG_USE_GPU
)

# --- Constants ---
AIM_SENSITIVITY = 0.15 # How strongly the aim pulls towards the target (0.0 to 1.0+) Adjust as needed!
AIM_SLEEP_INTERVAL = 0.01 # Seconds between aim adjustments

# Hotkeys (Using F keys, easy to press without interfering with game keys usually)
ESP_TOGGLE_KEY = keyboard.Key.f1
AIM_TOGGLE_KEY = keyboard.Key.f2
EXIT_KEY = keyboard.Key.f4 # Use F4 to exit cleanly

# --- Global State ---
# Using globals for simplicity in this example. For larger apps, consider a state class.
esp_enabled = True
aim_assist_enabled = False
program_running = True

# Shared data between main loop and aim assist loop
current_closest_target = None
screen_center_x = -1
screen_center_y = -1

# Thread safety for shared data
state_lock = threading.Lock() # Ensure this is defined globally

# Pynput controllers (initialize once)
mouse_controller = mouse.Controller()

# --- Hotkey Functions ---
def on_press(key):
    global esp_enabled, aim_assist_enabled, program_running
    try:
        with state_lock: # Use the lock to ensure thread safety
            if key == ESP_TOGGLE_KEY:
                esp_enabled = not esp_enabled
                logger.info(f"ESP {'ENABLED' if esp_enabled else 'DISABLED'}")
            elif key == AIM_TOGGLE_KEY:
                aim_assist_enabled = not aim_assist_enabled
                logger.info(f"Aim Assist {'ENABLED' if aim_assist_enabled else 'DISABLED'}")
            elif key == EXIT_KEY:
                logger.info("Exit key pressed. Initiating shutdown...")
                program_running = False

    except AttributeError:
        # Handle special keys if needed, otherwise ignore
        pass

def keyboard_listener_thread():
    logger.info(f"Starting keyboard listener. Press {ESP_TOGGLE_KEY} to toggle ESP, {AIM_TOGGLE_KEY} to toggle Aim Assist, {EXIT_KEY} to exit.")
    # Collect events until listener.stop() is called or thread exits
    # We'll use program_running flag to control exit instead of listener.join()
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    logger.info("Keyboard listener started.")
    while program_running:
         time.sleep(0.1) # Keep thread alive while checking flag
    listener.stop()
    logger.info("Keyboard listener stopped.")


# --- Aim Assist Thread ---
def aim_assist_loop():
    global current_closest_target, screen_center_x, screen_center_y, program_running, aim_assist_enabled

    logger.info("Aim assist thread started.")
    while program_running:
        target_to_aim = None
        aim_enabled_this_loop = False

        with state_lock: # Use lock for reading shared state
            aim_enabled_this_loop = aim_assist_enabled # Check if enabled
            if aim_enabled_this_loop:
                 target_to_aim = current_closest_target # Safely read the shared target

        if aim_enabled_this_loop and target_to_aim and screen_center_x > 0:
            try:
                bbox = target_to_aim['bbox']
                target_x = (bbox[0] + bbox[2]) // 2
                target_y = (bbox[1] + bbox[3]) // 2

                # Calculate vector from screen center to target center
                delta_x = target_x - screen_center_x
                delta_y = target_y - screen_center_y

                # Simple proportional movement (apply sensitivity)
                move_x = int(delta_x * AIM_SENSITIVITY)
                move_y = int(delta_y * AIM_SENSITIVITY)

                # Only move if there's a significant enough delta
                if abs(move_x) > 0 or abs(move_y) > 0:
                    # Ensure we don't block other threads while potentially moving the mouse
                    # No lock needed for mouse_controller.move itself unless pynput docs specify otherwise
                    mouse_controller.move(move_x, move_y)
                    # logger.debug(f"Aim Assist moving mouse by ({move_x}, {move_y})")

            except Exception as e:
                logger.error(f"Error in aim assist logic: {e}", exc_info=False)

        # Prevent tight loop, sleep even if not aiming
        time.sleep(AIM_SLEEP_INTERVAL)

    logger.info("Aim assist thread finished.")


def main():
    app_state = AppState()

    # Initialize modules
    capture_source = None
    ai_processor = None
    overlay_renderer = None
    input_handler = None
    aim_assist = None

    try:
        # Create shared queues
        frame_queue = Queue(maxsize=CONFIG_FRAME_QUEUE_SIZE)
        results_queue = Queue(maxsize=CONFIG_FRAME_QUEUE_SIZE + 2) # Slightly larger

        # --- Initialize Modules ---
        # Pass app_state where needed
        capture_source = get_capture_source(frame_queue)
        ai_processor = AIProcessor(frame_queue, results_queue)
        overlay_renderer = OverlayRenderer()
        input_handler = InputHandler(app_state)
        aim_assist = AimAssist(app_state)

        # --- Start Background Threads ---
        capture_source.start()
        time.sleep(1) # Give capture time to initialize

        # Set screen center in AppState after capture starts
        width, height, _ = capture_source.get_properties()
        if width > 0 and height > 0:
            app_state.screen_center_x = width // 2
            app_state.screen_center_y = height // 2
            logger.info(f"Capture dimensions received: {width}x{height}. Screen center set in AppState.")
        else:
            logger.warning("Capture source failed to provide valid dimensions.")
            # Fallback logic (moved here from old main)
            try:
                res = CONFIG_RESOLUTION
                if res and len(res) == 2:
                    app_state.screen_center_x = res[0] // 2
                    app_state.screen_center_y = res[1] // 2
                    logger.info(f"Using fallback center from config: ({app_state.screen_center_x}, {app_state.screen_center_y})")
                else: raise ValueError("Invalid config resolution")
            except Exception:
                app_state.screen_center_x = 1920 // 2 # Last resort default
                app_state.screen_center_y = 1080 // 2
                logger.warning(f"Using default screen center: ({app_state.screen_center_x}, {app_state.screen_center_y})")

        ai_processor.start()
        input_handler.start()
        aim_assist.start()

        logger.info("Main loop starting. Use hotkeys to control features.")

        # --- Main Display Loop ---
        while app_state.program_running:
            try:
                # Get the latest processed result
                result_data = results_queue.get(timeout=0.5)
            except Empty:
                if not app_state.program_running: break # Check again after timeout
                # Optional: Check if worker threads are alive (though they should exit if app_state.program_running is False)
                # ... (add checks for capture_source._capture_thread.is_alive() etc. if needed)
                continue
            except Exception as e:
                logger.error(f"Error getting results from queue: {e}")
                app_state.request_shutdown()
                break

            # Extract data
            frame = result_data.get('frame')
            detections = result_data.get('detections', [])
            closest_target_from_queue = result_data.get('closest_target')

            if frame is None:
                logger.warning("Received None frame in main loop. Skipping display.")
                continue

            # Update shared state
            app_state.current_closest_target = closest_target_from_queue

            # Draw overlays based on state
            display_frame = None
            if app_state.esp_enabled:
                display_frame = overlay_renderer.draw_overlays(frame, detections, closest_target_from_queue)
            else:
                # Still draw the frame, but without ESP elements (boxes, lines)
                # OverlayRenderer might still draw crosshair/FPS
                display_frame = overlay_renderer.draw_overlays(frame, [], None)

            # Display the frame
            if display_frame is not None:
                overlay_renderer.display_frame(display_frame)
            else:
                logger.debug("display_frame was None, skipping display.")

            # Check for exit via OpenCV window 'q' key
            if overlay_renderer.check_exit_key(delay_ms=1):
                logger.info("Output window closed or 'q' pressed, initiating shutdown.")
                app_state.request_shutdown()
                break # Exit main loop immediately

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, initiating shutdown.")
        if app_state: app_state.request_shutdown()
    except Exception as e:
        logger.error(f"Unhandled exception in main setup or loop: {e}", exc_info=True)
        if app_state: app_state.request_shutdown()
    finally:
        # --- Cleanup --- (
        logger.info("Shutting down threads and resources...")

        # Ensure shutdown is signaled (might be redundant but safe)
        if app_state: app_state.request_shutdown()

        # Stop threads in reverse order of dependency (or based on function)
        if aim_assist: aim_assist.stop()
        if input_handler: input_handler.stop()
        if ai_processor: ai_processor.stop()
        if capture_source: capture_source.stop()

        # Cleanup display last
        if overlay_renderer: overlay_renderer.cleanup()

        logger.info("Application finished.")

if __name__ == "__main__":
    main() 