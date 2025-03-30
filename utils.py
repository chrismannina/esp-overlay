# utils.py
import time
import yaml
import logging

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(path="config.yaml"):
    """Loads configuration from a YAML file."""
    try:
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {path}")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {path}")
        return None
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return None

class FPSCounter:
    """A simple class to calculate and display FPS."""
    def __init__(self):
        self._start_time = time.time()
        self._frame_count = 0
        self._fps = 0.0

    def update(self):
        """Call this once per frame."""
        self._frame_count += 1
        elapsed_time = time.time() - self._start_time
        if elapsed_time >= 1.0:
            self._fps = self._frame_count / elapsed_time
            self._start_time = time.time()
            self._frame_count = 0
        return self._fps

    def get_fps(self):
        """Get the current calculated FPS."""
        return self._fps 