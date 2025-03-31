# utils.py
import time
import yaml
import logging
import os
import sys
import importlib # Needed for lazy loading
from cryptography.fernet import Fernet

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Lazy Loaded Modules --- (Initialize as None)
_cv2 = None
_mss = None
_ort = None

def _load_cv2():
    global _cv2
    if _cv2 is None:
        try:
            _cv2 = importlib.import_module("cv2")
            logger.debug("cv2 loaded dynamically.")
        except ImportError:
            logger.error("Failed to import cv2. Please ensure OpenCV (opencv-python) is installed.")
            raise # Re-raise to stop execution if critical
    return _cv2

def _load_mss():
    global _mss
    if _mss is None:
        try:
            _mss = importlib.import_module("mss")
            logger.debug("mss loaded dynamically.")
        except ImportError:
            logger.error("Failed to import mss. Please ensure mss is installed.")
            raise
    return _mss

def _load_ort():
    global _ort
    if _ort is None:
        try:
            _ort = importlib.import_module("onnxruntime")
            logger.debug("onnxruntime loaded dynamically.")
        except ImportError:
            logger.error("Failed to import onnxruntime. Please ensure onnxruntime or onnxruntime-gpu is installed.")
            raise
    return _ort

# --- Public functions to get the modules ---
def get_cv2():
    return _load_cv2()

def get_mss():
    return _load_mss()

def get_ort():
    return _load_ort()
# --- End Lazy Loading ---

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