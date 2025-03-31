# Central location for hardcoded configuration values

# --- Capture Settings ---
CONFIG_CAPTURE_TYPE = 'webcam' # 'webcam', 'elgato', 'screen'
CONFIG_DEVICE_INDEX = 0
CONFIG_RESOLUTION = [1920, 1080] # Desired resolution (width, height). Set to None to use default.
CONFIG_FPS = 60 # Desired FPS. Set to None to use default.
CONFIG_MONITOR = 1 # Monitor number (1 for primary, 2 for secondary, etc.)
# Bounding box for capture region [left, top, width, height]. Set to None for full monitor.
CONFIG_REGION = None # Example: capture only top-left 800x600 region: [0, 0, 800, 600]

# --- AI Settings ---
CONFIG_MODEL_PATH = 'models/yolov5n.onnx'
CONFIG_CONF_THRESHOLD = 0.4 # Confidence threshold for detections (0.0 to 1.0)
CONFIG_NMS_THRESHOLD = 0.5  # Non-Maximum Suppression (NMS) threshold (0.0 to 1.0)
# Class IDs to detect (e.g., [0] for 'person' in COCO)
# Check your model's class definition. Set to None to detect all classes.
CONFIG_CLASSES_TO_DETECT = [0] 
# Use GPU for ONNX Runtime? Requires onnxruntime-gpu package and compatible hardware/drivers.
CONFIG_USE_GPU = False # Set to False to use CPU.

# --- Output Settings ---
CONFIG_SHOW_FPS = True # Show the FPS on the output window
CONFIG_WINDOW_TITLE = 'ESP Overlay MVP' # Title of the output window

# --- Performance Settings ---
# Max size of the frame queue between capture and processing
# Smaller values reduce latency but might drop more frames if AI is slow.
# Larger values buffer more, increasing latency but smoothing temporary slowdowns.
# 1 or 2 is usually good for low latency.
CONFIG_FRAME_QUEUE_SIZE = 2 