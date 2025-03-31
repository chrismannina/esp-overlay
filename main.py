# main.py
import time
import threading
from queue import Queue, Empty
import sys
import math # Added for aim assist calculation

# Input handling
from pynput import keyboard, mouse

from utils import logger
from capture import get_capture_source
from processing import AIProcessor
from overlay import OverlayRenderer

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
    global program_running, current_closest_target, screen_center_x, screen_center_y, state_lock, esp_enabled, aim_assist_enabled

    # Initialize module variables to None for robust cleanup
    capture_source = None
    ai_processor = None
    overlay_renderer = None
    listener_thread = None
    aim_thread = None

    try:
        # Create shared queues
        frame_queue = Queue(maxsize=CONFIG_FRAME_QUEUE_SIZE)
        results_queue = Queue(maxsize=CONFIG_FRAME_QUEUE_SIZE + 2)

        # --- Initialize Modules ---
        capture_source = get_capture_source(frame_queue)
        ai_processor = AIProcessor(frame_queue, results_queue)
        overlay_renderer = OverlayRenderer()

        # --- Start Threads ---
        capture_source.start()
        time.sleep(1) # Give capture time to initialize

        # Get capture dimensions for aim assist
        width, height, _ = capture_source.get_properties()
        if width > 0 and height > 0:
            screen_center_x = width // 2
            screen_center_y = height // 2
            logger.info(f"Capture dimensions received: {width}x{height}. Screen center: ({screen_center_x}, {screen_center_y})")
        else:
            logger.warning("Capture source failed to provide valid dimensions. Aim assist might not work correctly.")
            # Fallback - try getting from config? Or use a reasonable default.
            try:
                res = CONFIG_RESOLUTION
                if res and len(res) == 2:
                    screen_center_x = res[0] // 2
                    screen_center_y = res[1] // 2
                    logger.info(f"Using fallback center from config: ({screen_center_x}, {screen_center_y})")
                else: raise ValueError("Invalid config resolution")
            except Exception:
                screen_center_x = 1920 // 2 # Last resort default
                screen_center_y = 1080 // 2
                logger.warning(f"Using default screen center: ({screen_center_x}, {screen_center_y})")


        ai_processor.start()

        # Start helper threads
        listener_thread = threading.Thread(target=keyboard_listener_thread, name="KeyboardListenerThread", daemon=True)
        listener_thread.start()

        aim_thread = threading.Thread(target=aim_assist_loop, name="AimAssistThread", daemon=True)
        aim_thread.start()


        logger.info("Main loop starting. Use hotkeys to control features.")
        # --- Main Display Loop ---
        while program_running: # Check global flag controlled by hotkey listener
            # Get the latest processed result
            try:
                result_data = results_queue.get(timeout=0.5)
            except Empty:
                if not program_running: break # Exit if flag was set while waiting
                # Check if worker threads are alive (more robust check)
                if not capture_source or not capture_source._capture_thread or not capture_source._capture_thread.is_alive():
                    logger.error("Capture thread has stopped unexpectedly. Exiting.")
                    program_running = False # Signal other threads
                    break
                if not ai_processor or not ai_processor._processing_thread or not ai_processor._processing_thread.is_alive():
                    logger.error("Processing thread has stopped unexpectedly. Exiting.")
                    program_running = False # Signal other threads
                    break
                continue # Continue loop if threads are okay but queue is empty
            except Exception as e:
                logger.error(f"Error getting results from queue: {e}")
                program_running = False # Signal other threads
                break

            # Extract data
            frame = result_data.get('frame')
            detections = result_data.get('detections', [])
            closest_target_from_queue = result_data.get('closest_target') # Can be None

            if frame is None:
                logger.warning("Received None frame in main loop. Skipping display.")
                continue

            # Update shared target info for aim assist thread
            with state_lock: # Use lock for writing shared state
                current_closest_target = closest_target_from_queue

            # Draw overlays only if ESP is enabled
            display_frame = None
            esp_on = False
            with state_lock: esp_on = esp_enabled # Check state safely

            if esp_on:
                # Pass detections and the specific closest target to draw_overlays
                display_frame = overlay_renderer.draw_overlays(frame, detections, closest_target_from_queue)
            else:
                # If ESP is off, show frame without detections but still call overlay logic
                # to potentially show FPS or crosshair if those are desired even when ESP boxes are off.
                display_frame = overlay_renderer.draw_overlays(frame, [], None) # Pass empty detections

            # Display the frame
            if display_frame is not None:
                overlay_renderer.display_frame(display_frame)
            else:
                logger.debug("display_frame was None, skipping display.")


            # Check for exit using cv2 window 'q' key
            if overlay_renderer.check_exit_key(delay_ms=1):
                logger.info("Output window closed or 'q' pressed, initiating shutdown.")
                program_running = False # Signal other threads
                break


    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, initiating shutdown.")
        program_running = False # Signal other threads
    except Exception as e:
        logger.error(f"Unhandled exception in main loop: {e}", exc_info=True)
        program_running = False # Signal other threads
    finally:
        # --- Cleanup ---
        logger.info("Shutting down threads and resources...")
        # Ensure program_running is false to signal threads cleanly
        if program_running: # Check if it wasn't already set by exception/hotkey
            with state_lock:
                program_running = False

        # Stop capture and processing threads first
        if capture_source: capture_source.stop()
        if ai_processor: ai_processor.stop()

        # Wait gently for aim thread (it's daemon, but helps ensure clean exit)
        if aim_thread and aim_thread.is_alive():
            logger.debug("Waiting for AimAssistThread...")
            aim_thread.join(timeout=1.0)
            if aim_thread.is_alive():
                logger.warning("Aim assist thread did not exit cleanly.")

        # Wait gently for keyboard listener thread
        if listener_thread and listener_thread.is_alive():
            logger.debug("Waiting for KeyboardListenerThread...")
            listener_thread.join(timeout=1.0) # Listener should stop when program_running becomes False
            if listener_thread.is_alive():
                logger.warning("Keyboard listener thread did not exit cleanly.")


        if overlay_renderer: overlay_renderer.cleanup() # Close CV2 windows
        logger.info("Application finished.")

if __name__ == "__main__":
    main() 