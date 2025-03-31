# Real-Time Game Video ESP Overlay - MVP

This project is a Minimum Viable Product (MVP) for a real-time ESP (Extra Sensory Perception) video overlay. It captures video from various sources (webcam, Elgato capture card via UVC, screen), performs object detection using an ONNX model (e.g., YOLOv5), and displays the video feed with bounding box overlays in real-time.

## Features

*   **Modular Design:** Separate modules for capture, AI processing, and overlay rendering.
*   **Multiple Capture Sources:** Supports standard webcams, UVC-compliant capture cards (like Elgato Game Capture Neo), and screen capture (specific monitor or region).
*   **Configurable:** Uses `config.yaml` to easily switch capture sources, set model paths, confidence thresholds, etc.
*   **Real-time Processing:** Uses multi-threading to pipeline capture and AI inference for lower latency.
*   **ONNX Runtime:** Leverages ONNX Runtime for efficient AI model inference, supporting CPU and optionally GPU (CUDA/DirectML).
*   **Basic Overlay:** Draws bounding boxes and confidence scores for detected objects using OpenCV.

## Project Structure

```
esp-overlay/
├── config.yaml         # Configuration file
├── requirements.txt    # Python dependencies
├── main.py             # Main application entry point
├── capture.py          # Video capture module (Webcam, Screen)
├── processing.py       # AI processing module (ONNX inference)
├── overlay.py          # Overlay drawing and display module
├── utils.py            # Utility functions (config loading, FPS counter)
├── models/             # Directory to place your ONNX model(s)
│   └── (yolov5n.onnx)  # Example: Download/place your model here
├── dev_guide.md        # Original development guide
└── README.md           # This file
```

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url> # Or just have the files in a directory
    cd esp-overlay
    ```

2.  **Create a Python virtual environment (Recommended):**
    ```bash
    python -m venv venv
    # Activate the environment
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    *   **For CPU Inference:**
        ```bash
        pip install -r requirements.txt
        ```
    *   **For GPU Inference (NVIDIA CUDA or DirectML):**
        First, ensure you have the necessary GPU drivers and CUDA Toolkit (for NVIDIA) installed.
        Then, install the appropriate `onnxruntime-gpu` package instead of the standard `onnxruntime`.
        *Comment out `onnxruntime` in `requirements.txt`* and run:
        ```bash
        # Example for CUDA 11.x
        pip install onnxruntime-gpu==1.15.1 # Choose version matching your CUDA/cuDNN
        # Or for DirectML (Windows DX12 GPU - NVIDIA/AMD/Intel)
        # pip install onnxruntime-directml==1.15.1

        # Then install the rest
        pip install opencv-python numpy mss pyyaml ultralytics
        ```
        *Refer to the official ONNX Runtime documentation for exact GPU package names and compatibility.* 

4.  **Download an ONNX Model:**
    *   You need an object detection model in ONNX format (e.g., YOLOv5, YOLOv8).
    *   You can export one from PyTorch or download pre-trained models.
        *   Example: Download `yolov5n.onnx` from the YOLOv5 releases ([https://github.com/ultralytics/yolov5/releases](https://github.com/ultralytics/yolov5/releases)).
    *   Place the downloaded `.onnx` file inside the `models/` directory (create the directory if it doesn't exist).
    *   Update the `model_path` in `config.yaml` to match your model file name (`models/your_model.onnx`).

5.  **Configure `config.yaml`:**
    *   Open `config.yaml` and adjust the settings:
        *   `capture`: Set `type` to `webcam`, `elgato` (if it acts as webcam index 0, 1, etc.), or `screen`.
        *   If `webcam`/`elgato`, set the correct `device_index`. You might need to try different indices (0, 1, 2...) to find your camera/card.
        *   If `screen`, set the `monitor` number (1 for primary usually) and optionally a `region` `[left, top, width, height]`.
        *   `ai`: Verify `model_path`, set `confidence_threshold`, `nms_threshold`, and `classes_to_detect` (e.g., `[0]` for the 'person' class in COCO-trained models).
        *   Set `use_gpu` to `true` if you installed `onnxruntime-gpu` and want to use the GPU, otherwise `false`.

## Running the Application

1.  **Ensure your virtual environment is active.**
2.  **Run the main script:**
    ```bash
    python main.py
    ```
3.  An OpenCV window should appear displaying the video feed from your chosen source with bounding boxes around detected objects.
4.  Press **'q'** in the output window to quit the application gracefully.

## Next Steps & Potential Improvements

*   **Class Labels:** Map detected `class_id`s to human-readable names (e.g., using a COCO names file).
*   **Tracking:** Implement object tracking (e.g., SORT) between detections for smoother bounding boxes.
*   **Performance Tuning:** Profile the application to identify bottlenecks (capture, preprocessing, inference, drawing) and optimize further (e.g., use DirectML/TensorRT, optimize drawing).
*   **Advanced Overlay:** Use a dedicated graphics library (SDL, SFML, DirectX) for more sophisticated overlay rendering (transparency, custom shapes, player-facing overlay window).
*   **Game Profiles:** Implement a system to load different models/settings specific to different games.
*   **Error Handling:** Add more robust error handling and recovery (e.g., attempt to reconnect capture device if it fails).
*   **GUI:** Create a simple GUI using PyQt or Tkinter to manage settings and start/stop the process. 