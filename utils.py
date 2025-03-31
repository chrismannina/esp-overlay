# utils.py
import time
import yaml
import logging
import os
import sys
from cryptography.fernet import Fernet

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
logger = logging.getLogger(__name__)

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

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path) 