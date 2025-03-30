# overlay.py
import cv2
from utils import logger, FPSCounter

class OverlayRenderer:
    """Handles drawing overlays onto frames and displaying the result."""
    def __init__(self, config):
        self.config = config['output']
        self.show_fps = self.config.get('show_fps', True)
        self.window_title = self.config.get('window_title', 'ESP Overlay')
        self.fps_counter = FPSCounter()

        # Basic color definitions (BGR format)
        self.colors = {
            'red': (0, 0, 255),
            'green': (0, 255, 0),
            'blue': (255, 0, 0),
            'white': (255, 255, 255),
            'black': (0, 0, 0)
        }
        self.default_box_color = self.colors['red']
        self.default_text_color = self.colors['white']

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
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), self.default_box_color, 2)

                # Prepare label text
                # TODO: Map class_id to label name if available
                label = f"ID:{class_id} {confidence:.2f}"

                # Calculate text size and position
                (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                text_x = x1
                text_y = y1 - 10 # Position text above the box
                if text_y < 10: # If too close to top edge, put below box
                    text_y = y2 + text_height + 5

                # Draw background rectangle for text for better visibility
                cv2.rectangle(display_frame, (text_x, text_y - text_height - baseline), (text_x + text_width, text_y + baseline), self.colors['black'], cv2.FILLED)
                # Draw label text
                cv2.putText(display_frame, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.default_text_color, 1, cv2.LINE_AA)

            except Exception as e:
                logger.error(f"Error drawing detection {det}: {e}", exc_info=False) # Avoid excessive logging

        # Draw FPS counter
        if self.show_fps:
            fps = self.fps_counter.update() # Update FPS based on display rate
            fps_text = f"FPS: {fps:.2f}"
            cv2.putText(display_frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.colors['green'], 2, cv2.LINE_AA)

        return display_frame

    def display_frame(self, frame):
        """Displays the frame in an OpenCV window."""
        if frame is not None:
            cv2.imshow(self.window_title, frame)
        else:
            logger.warning("Attempted to display a None frame.")

    def check_exit_key(self, delay_ms=1):
        """Waits for a key press and returns True if 'q' is pressed."""
        key = cv2.waitKey(delay_ms) & 0xFF
        return key == ord('q')

    def cleanup(self):
        """Closes OpenCV display windows."""
        logger.info("Closing display windows.")
        cv2.destroyAllWindows() 