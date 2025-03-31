# overlay.py
# import cv2 # Dynamic import
# import socket # No longer used
# import struct # No longer used
# import importlib # No longer used
import math
from utils import logger, FPSCounter, get_cv2 # Import getter

# --- Removed Dynamic Imports Section ---
# No longer need _cv2 global or _lazy_load_cv2 here

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
            'black': (0, 0, 0),
            'yellow': (0, 255, 255), # Added for closest target
            'cyan': (255, 255, 0)   # Added for snap lines
        }
        self.default_box_color = self.colors['red']
        self.closest_box_color = self.colors['yellow']
        self.snap_line_color = self.colors['cyan']
        self.default_text_color = self.colors['white']
        # _lazy_load_cv2() # Removed
        self.cv2 = get_cv2() # Get cv2 when needed

    def draw_overlays(self, frame, detections, closest_target):
        """Draws bounding boxes, info, snap lines, and highlights the closest target."""
        if frame is None:
            return None

        display_frame = frame.copy()
        frame_h, frame_w = display_frame.shape[:2]
        screen_center_x, screen_center_y = frame_w // 2, frame_h // 2

        # Draw crosshair (simple lines)
        crosshair_color = self.colors['green']
        crosshair_size = 10
        # Use self.cv2
        self.cv2.line(display_frame, (screen_center_x - crosshair_size, screen_center_y),
                 (screen_center_x + crosshair_size, screen_center_y), crosshair_color, 1)
        self.cv2.line(display_frame, (screen_center_x, screen_center_y - crosshair_size),
                 (screen_center_x, screen_center_y + crosshair_size), crosshair_color, 1)

        # Check if detections is a list
        if not isinstance(detections, list):
             logger.warning(f"draw_overlays received non-list detections: {type(detections)}")
             detections = [] # Prevent errors

        for det in detections:
            try:
                bbox = det['bbox'] # [x_min, y_min, x_max, y_max]
                confidence = det['confidence']
                class_id = det['class_id']
                is_closest = det.get('is_closest', False) # Get the flag

                x1, y1, x2, y2 = map(int, bbox)
                box_center_x = (x1 + x2) // 2
                box_center_y = (y1 + y2) // 2

                # Determine box color and thickness
                box_color = self.closest_box_color if is_closest else self.default_box_color
                box_thickness = 3 if is_closest else 2

                # Draw bounding box
                self.cv2.rectangle(display_frame, (x1, y1), (x2, y2), box_color, box_thickness)

                # Draw snap line from center screen to box center
                self.cv2.line(display_frame, (screen_center_x, screen_center_y),
                         (box_center_x, box_center_y), self.snap_line_color, 1)

                # Prepare label text
                # TODO: Map class_id to label name if available
                label = f"ID:{class_id} {confidence:.2f}"
                # Optional: Add distance if calculated and needed
                # dist = math.sqrt((box_center_x - screen_center_x)**2 + (box_center_y - screen_center_y)**2)
                # label += f" D:{dist:.0f}"

                # Calculate text size and position
                (text_width, text_height), baseline = self.cv2.getTextSize(label, self.cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                text_x = x1
                text_y = y1 - 10 # Position text above the box
                if text_y < 10: # If too close to top edge, put below box
                    text_y = y2 + text_height + 5

                # Draw background rectangle for text for better visibility
                self.cv2.rectangle(display_frame, (text_x, text_y - text_height - baseline), (text_x + text_width, text_y + baseline), self.colors['black'], self.cv2.FILLED)
                # Draw label text
                self.cv2.putText(display_frame, label, (text_x, text_y), self.cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.default_text_color, 1, self.cv2.LINE_AA)

            except Exception as e:
                logger.error(f"Error drawing detection {det}: {e}", exc_info=False) # Avoid excessive logging

        # Draw FPS counter
        if self.show_fps:
            fps = self.fps_counter.update() # Update FPS based on display rate
            fps_text = f"FPS: {fps:.2f}"
            self.cv2.putText(display_frame, fps_text, (10, 30), self.cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.colors['green'], 2, self.cv2.LINE_AA)

        return display_frame

    def display_frame(self, frame):
        """Displays the frame in an OpenCV window."""
        if frame is not None:
            self.cv2.imshow(self.window_title, frame)
        else:
            logger.warning("Attempted to display a None frame.")

    def check_exit_key(self, delay_ms=1):
        """Waits for a key press and returns True if 'q' is pressed."""
        key = self.cv2.waitKey(delay_ms) & 0xFF
        return key == ord('q')

    def cleanup(self):
        """Closes OpenCV display windows."""
        logger.info("Closing display windows.")
        # self.sock.close() # No socket to close
        self.cv2.destroyAllWindows() # Need this for local display
        logger.info("OverlayRenderer cleanup finished.") 