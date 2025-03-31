# overlay.py
# import cv2 # Dynamic import
from utils import logger, FPSCounter
import socket
import struct # For packing frame size
import importlib

# --- Dynamic Imports ---
_cv2 = None

def _lazy_load_cv2():
    global _cv2
    if _cv2 is None:
        try:
            _cv2 = importlib.import_module("cv2")
            logger.debug("cv2 loaded dynamically for overlay.")
        except ImportError:
            logger.error("Failed to import cv2. Please ensure OpenCV is installed.")
            raise # Re-raise to stop execution if critical
# --- End Dynamic Imports ---

# Import constants from main (or define them here)
from config_constants import (CONFIG_SHOW_FPS, CONFIG_WINDOW_TITLE)

class OverlayRenderer:
    """Handles drawing overlays onto frames and displaying the result locally."""
    def __init__(self):
        # self.config = config['output'] # Removed
        self.show_fps = CONFIG_SHOW_FPS
        self.window_title = CONFIG_WINDOW_TITLE
        self.fps_counter = FPSCounter()

        # --- Network Setup ---
        # Remove UDP network setup
        # self.udp_ip = self.config.get('udp_ip', '127.0.0.1')
        # self.udp_port = self.config.get('udp_port', 9999)
        # self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # logger.info(f"OverlayRenderer configured to send frames via UDP to {self.udp_ip}:{self.udp_port}")

        # --- Colors ---
        self.colors = {
            'red': (0, 0, 255),
            'green': (0, 255, 0),
            'blue': (255, 0, 0),
            'white': (255, 255, 255),
            'black': (0, 0, 0)
        }
        self.default_box_color = self.colors['red']
        self.default_text_color = self.colors['white']
        _lazy_load_cv2() # Ensure cv2 is loaded

    def draw_overlays(self, frame, detections):
        """Draws bounding boxes and info for detected objects."""
        if frame is None:
            return None

        display_frame = frame.copy()

        for det in detections:
            try:
                bbox = det['bbox'] # [x_min, y_min, x_max, y_max]
                confidence = det['confidence']
                class_id = det['class_id']

                x1, y1, x2, y2 = map(int, bbox)

                # Draw bounding box
                _cv2.rectangle(display_frame, (x1, y1), (x2, y2), self.default_box_color, 2)

                # Prepare label text
                # TODO: Map class_id to label name if available
                label = f"ID:{class_id} {confidence:.2f}"

                # Calculate text size and position
                (text_width, text_height), baseline = _cv2.getTextSize(label, _cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                text_x = x1
                text_y = y1 - 10 # Position text above the box
                if text_y < 10: # If too close to top edge, put below box
                    text_y = y2 + text_height + 5

                # Draw background rectangle for text for better visibility
                _cv2.rectangle(display_frame, (text_x, text_y - text_height - baseline), (text_x + text_width, text_y + baseline), self.colors['black'], _cv2.FILLED)
                # Draw label text
                _cv2.putText(display_frame, label, (text_x, text_y), _cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.default_text_color, 1, _cv2.LINE_AA)

            except Exception as e:
                logger.error(f"Error drawing detection {det}: {e}", exc_info=False) # Avoid excessive logging

        # Draw FPS counter
        if self.show_fps:
            fps = self.fps_counter.update() # Update FPS based on display rate
            fps_text = f"FPS: {fps:.2f}"
            _cv2.putText(display_frame, fps_text, (10, 30), _cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.colors['green'], 2, _cv2.LINE_AA)

        return display_frame

    def display_frame(self, frame):
        """Displays the frame in an OpenCV window."""
        if frame is not None:
            _cv2.imshow(self.window_title, frame)
        else:
            logger.warning("Attempted to display a None frame.")

    def check_exit_key(self, delay_ms=1):
        """Waits for a key press and returns True if 'q' is pressed."""
        key = _cv2.waitKey(delay_ms) & 0xFF
        return key == ord('q')

    def cleanup(self):
        """Closes OpenCV display windows."""
        logger.info("Closing display windows.")
        # self.sock.close() # No socket to close
        _cv2.destroyAllWindows() # Need this for local display
        logger.info("OverlayRenderer cleanup finished.") 