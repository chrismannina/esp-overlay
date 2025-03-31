# capture.py
# import cv2 # Dynamic import
# import mss # Dynamic import
import numpy as np
import time
import threading
# import importlib # No longer needed here
from queue import Queue, Full
from abc import ABC, abstractmethod
from utils import logger, get_cv2, get_mss # Import getters
# Import constants from main (or define them here)
from config_constants import (
    CONFIG_DEVICE_INDEX, CONFIG_RESOLUTION, CONFIG_FPS, 
    CONFIG_MONITOR, CONFIG_REGION, CONFIG_CAPTURE_TYPE
)

# --- Removed Dynamic Imports Section ---
# No longer need _cv2, _mss globals or _lazy_load_deps here

class BaseCapture(ABC):
    """Abstract base class for different capture methods."""
    def __init__(self, frame_queue):
        self.frame_queue = frame_queue
        self._stop_event = threading.Event()
        self._capture_thread = None
        self.width = 0
        self.height = 0
        self.fps = 0

    @abstractmethod
    def _capture_loop(self):
        """The main loop to capture frames and put them in the queue."""
        pass

    def start(self):
        """Starts the capture thread."""
        if self._capture_thread is not None:
            logger.warning("Capture thread already running.")
            return
        logger.info(f"Starting capture thread for {self.__class__.__name__}...")
        self._stop_event.clear()
        self._capture_thread = threading.Thread(target=self._capture_loop, name=f"{self.__class__.__name__}Thread")
        self._capture_thread.daemon = True # Ensure thread exits when main program exits
        self._capture_thread.start()

    def stop(self):
        """Signals the capture thread to stop."""
        if self._capture_thread is None:
            logger.warning("Capture thread not running.")
            return
        logger.info(f"Stopping capture thread for {self.__class__.__name__}...")
        self._stop_event.set()
        self._capture_thread.join(timeout=2) # Wait for thread to finish
        if self._capture_thread.is_alive():
            logger.warning("Capture thread did not stop gracefully.")
        self._capture_thread = None
        logger.info("Capture thread stopped.")

    def get_properties(self):
        """Returns the capture properties (width, height, fps)."""
        return self.width, self.height, self.fps


class WebcamCapture(BaseCapture):
    """Captures video from a webcam or UVC device like Elgato Neo."""
    def __init__(self, frame_queue):
        super().__init__(frame_queue)
        self.device_index = CONFIG_DEVICE_INDEX
        self.target_resolution = tuple(CONFIG_RESOLUTION) if CONFIG_RESOLUTION else None
        self.target_fps = CONFIG_FPS
        # _lazy_load_deps() # Removed
        self.cv2 = get_cv2() # Get cv2 when needed
        self.cap = None

    def _capture_loop(self):
        try:
            logger.info(f"Initializing webcam/UVC device index: {self.device_index}")
            # Use self.cv2 which holds the loaded module
            self.cap = self.cv2.VideoCapture(self.device_index, self.cv2.CAP_ANY)

            if not self.cap.isOpened():
                logger.error(f"Failed to open video capture device {self.device_index}.")
                self.cap.release()
                return

            # --- Configure Capture Properties ---
            if self.target_resolution:
                logger.info(f"Setting resolution to {self.target_resolution}")
                self.cap.set(self.cv2.CAP_PROP_FRAME_WIDTH, self.target_resolution[0])
                self.cap.set(self.cv2.CAP_PROP_FRAME_HEIGHT, self.target_resolution[1])

            if self.target_fps:
                logger.info(f"Setting FPS to {self.target_fps}")
                self.cap.set(self.cv2.CAP_PROP_FPS, self.target_fps)

            # --- Read Actual Properties ---
            self.width = int(self.cap.get(self.cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(self.cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(self.cv2.CAP_PROP_FPS)
            logger.info(f"Capture device opened: {self.width}x{self.height} @ {self.fps:.2f} FPS")

            if self.width == 0 or self.height == 0:
                 logger.error("Capture device reported zero resolution. Check device index or permissions.")
                 self.cap.release()
                 return

            while not self._stop_event.is_set():
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    logger.warning("Failed to grab frame or end of stream.")
                    time.sleep(0.1) # Avoid busy-waiting if stream ends or fails
                    # Attempt to reopen if necessary?
                    # For now, just break the loop
                    break

                try:
                    # Put the frame into the queue, overwriting oldest if full
                    self.frame_queue.put_nowait((time.time(), frame))
                except Full:
                    # Queue is full, drop the oldest frame and put the new one
                    try:
                        self.frame_queue.get_nowait() # Discard oldest
                        self.frame_queue.put_nowait((time.time(), frame)) # Add newest
                        logger.debug("Frame queue full, dropped oldest frame.")
                    except Exception as e_inner:
                        # Handle potential race condition if queue becomes empty between get/put
                        logger.warning(f"Error managing full queue: {e_inner}")
                except Exception as e:
                     logger.error(f"Error putting frame in queue: {e}")

        except Exception as e:
            logger.error(f"Exception in Webcam capture loop: {e}", exc_info=True)
        finally:
            if self.cap and self.cap.isOpened():
                self.cap.release()
                logger.info("Webcam capture resources released.")


class ScreenCapture(BaseCapture):
    """Captures video from a screen region."""
    def __init__(self, frame_queue):
        super().__init__(frame_queue)
        self.monitor_number = CONFIG_MONITOR
        self.region = CONFIG_REGION
        # _lazy_load_deps() # Removed
        self.cv2 = get_cv2()
        self.mss = get_mss()
        self.sct = None
        self.monitor = None

    def _capture_loop(self):
        try:
            with self.mss.mss() as self.sct:
                monitors = self.sct.monitors
                if self.monitor_number >= len(monitors) or self.monitor_number < 1:
                    logger.error(f"Invalid monitor number {self.monitor_number}. Available monitors: {len(monitors) -1}")
                    return

                self.monitor = monitors[self.monitor_number]

                if self.region:
                    # Use specified region relative to the chosen monitor
                    capture_region = {
                        "left": self.monitor["left"] + self.region[0],
                        "top": self.monitor["top"] + self.region[1],
                        "width": self.region[2],
                        "height": self.region[3],
                        "mon": self.monitor_number # Specify monitor context for region
                    }
                    self.width = self.region[2]
                    self.height = self.region[3]
                    logger.info(f"Capturing region {self.region} on monitor {self.monitor_number}")
                else:
                    # Capture the full monitor
                    capture_region = self.monitor
                    self.width = self.monitor["width"]
                    self.height = self.monitor["height"]
                    logger.info(f"Capturing full monitor {self.monitor_number}: {self.width}x{self.height}")

                # Estimate FPS - mss doesn't provide a fixed FPS
                self.fps = 60 # Assume 60 for now, could be measured
                logger.info(f"Screen capture started: {self.width}x{self.height} (Target FPS depends on system performance)")

                while not self._stop_event.is_set():
                    start_time = time.perf_counter()

                    # Grab the screen
                    sct_img = self.sct.grab(capture_region)

                    if sct_img:
                        # Convert to OpenCV format (BGRA to BGR)
                        frame = np.array(sct_img)
                        frame = self.cv2.cvtColor(frame, self.cv2.COLOR_BGRA2BGR)

                        try:
                            self.frame_queue.put_nowait((time.time(), frame))
                        except Full:
                            try:
                                self.frame_queue.get_nowait()
                                self.frame_queue.put_nowait((time.time(), frame))
                                logger.debug("Frame queue full, dropped oldest frame.")
                            except Exception as e_inner:
                                logger.warning(f"Error managing full queue: {e_inner}")
                        except Exception as e:
                            logger.error(f"Error putting frame in queue: {e}")

                    # Control capture rate - aim for roughly 60 FPS max if possible
                    elapsed = time.perf_counter() - start_time
                    sleep_time = max(0, (1/self.fps) - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Exception in Screen capture loop: {e}", exc_info=True)
        finally:
             logger.info("Screen capture resources released.")

def get_capture_source(frame_queue):
    """Factory function to create the appropriate capture source based on config."""
    capture_type = CONFIG_CAPTURE_TYPE.lower()
    logger.info(f"Selected capture type: {capture_type}")

    if capture_type == 'webcam' or capture_type == 'elgato':
        # Treat Elgato Neo as a UVC webcam
        return WebcamCapture(frame_queue)
    elif capture_type == 'screen':
        return ScreenCapture(frame_queue)
    else:
        logger.error(f"Unsupported capture type: {capture_type}. Defaulting to webcam.")
        # Default fallback - Note: This now hardcodes the fallback type too
        # If you want a dynamic fallback, you might need more complex logic
        # For now, it uses the hardcoded type or errors if unsupported
        if 'webcam' in ['webcam', 'elgato']: # Check if default is valid
             return WebcamCapture(frame_queue)
        else:
             # If the primary hardcoded type is invalid AND webcam isn't allowed,
             # we have an issue. Raise or log critical error.
             logger.critical("Unsupported hardcoded capture type AND fallback 'webcam' not viable!")
             # Decide how to handle: raise Exception("Invalid config") or return None
             return None # Or raise error 