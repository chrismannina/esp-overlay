# main.py
import time
import threading
from queue import Queue, Empty
import sys

from utils import logger, load_config
from capture import get_capture_source
from processing import AIProcessor
from overlay import OverlayRenderer

def main():
    # Load configuration
    config = load_config()
    if config is None:
        logger.error("Failed to load configuration. Exiting.")
        sys.exit(1)

    # Create shared queues
    # Queue for raw frames from capture to processing
    frame_queue_size = config.get('frame_queue_size', 2)
    frame_queue = Queue(maxsize=frame_queue_size)
    # Queue for processed results (frame + detections) from processing to display
    # Make this queue slightly larger to handle potential display fluctuations
    results_queue = Queue(maxsize=frame_queue_size + 2)

    # --- Initialize Modules ---
    # Capture Module (runs in its own thread)
    capture_source = get_capture_source(config, frame_queue)

    # AI Processing Module (runs in its own thread)
    # Ensure AI config exists
    if 'ai' not in config:
        logger.error("'ai' section missing in config.yaml. Exiting.")
        sys.exit(1)
    ai_processor = AIProcessor(frame_queue, results_queue, config)

    # Overlay and Output Module (runs in the main thread)
    # Ensure output config exists
    if 'output' not in config:
        logger.error("'output' section missing in config.yaml. Exiting.")
        sys.exit(1)
    overlay_renderer = OverlayRenderer(config)

    # --- Start Threads ---
    capture_source.start()
    # Give capture a moment to initialize and report properties
    time.sleep(1)
    width, height, fps = capture_source.get_properties()
    if width == 0 or height == 0:
         logger.warning("Capture source failed to provide valid dimensions. Trying to continue...")
         # Attempt to start processor anyway, might fail later
    ai_processor.start()

    logger.info("Main loop starting. Press 'q' in the output window to exit.")
    # --- Main Display Loop ---
    try:
        while True:
            # Get the latest processed result
            try:
                result_data = results_queue.get(timeout=0.5) # Wait up to 500ms for a result
            except Empty:
                # No new results, maybe check if threads are alive or just continue
                if not capture_source._capture_thread.is_alive():
                    logger.error("Capture thread has stopped unexpectedly. Exiting.")
                    break
                if not ai_processor._processing_thread.is_alive():
                     logger.error("Processing thread has stopped unexpectedly. Exiting.")
                     break
                logger.debug("No results in queue, waiting...")
                continue
            except Exception as e:
                 logger.error(f"Error getting results from queue: {e}")
                 break

            # Extract frame and detections
            frame = result_data.get('frame')
            detections = result_data.get('detections', [])

            if frame is None:
                logger.warning("Received None frame in main loop. Skipping display.")
                continue

            # Draw overlays
            display_frame = overlay_renderer.draw_overlays(frame, detections)

            # Display the frame
            overlay_renderer.display_frame(display_frame)

            # Check for exit key
            if overlay_renderer.check_exit_key(delay_ms=1): # Small delay for UI responsiveness
                logger.info("'q' pressed, initiating shutdown.")
                break

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, initiating shutdown.")
    except Exception as e:
         logger.error(f"Unhandled exception in main loop: {e}", exc_info=True)
    finally:
        # --- Cleanup ---
        logger.info("Shutting down threads and resources...")
        capture_source.stop()
        ai_processor.stop()
        overlay_renderer.cleanup()
        logger.info("Application finished.")

if __name__ == "__main__":
    main() 