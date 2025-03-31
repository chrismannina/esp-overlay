# Real-Time Game Video ESP Overlay - MVP (Obfuscated Test Version)

This project is a Minimum Viable Product (MVP) for a real-time ESP (Extra Sensory Perception) video overlay, modified to simulate some basic obfuscation techniques for testing anti-cheat software. It captures video from various sources (webcam, Elgato capture card via UVC, screen), performs object detection using an ONNX model (e.g., YOLOv5), and displays the video feed with bounding box overlays in real-time.

**Note:** Configuration values (capture device, model path, thresholds, etc.) are now **hardcoded** directly into the Python scripts (`main.py`, `capture.py`, `processing.py`, `overlay.py`). There is no external `config.yaml` file.

## Features (Modified)

*   **Modular Design:** Separate modules for capture, AI processing, and overlay rendering.
*   **Multiple Capture Sources:** Supports standard webcams, UVC-compliant capture cards, and screen capture (configured via hardcoded values).
*   **Dynamic Library Loading:** Uses `importlib` to load heavy dependencies (`opencv`, `onnxruntime`, `mss`) dynamically, slightly obscuring imports.
*   **Real-time Processing:** Uses multi-threading for capture and AI inference.
*   **ONNX Runtime:** Leverages ONNX Runtime for AI inference (CPU/GPU based on hardcoded setting).
*   **Basic Overlay:** Draws bounding boxes using OpenCV.

## Project Structure

```
esp-overlay/
├── requirements.txt    # Python dependencies
├── main.py             # Main application entry point (Contains hardcoded config)
├── capture.py          # Video capture module (Uses hardcoded config)
├── processing.py       # AI processing module (Uses hardcoded config)
├── overlay.py          # Overlay drawing module (Uses hardcoded config)
├── utils.py            # Utility functions (FPS counter)
├── models/             # Directory to place your ONNX model(s)
│   └── (yolov5n.onnx)  # Example: Ensure hardcoded path matches
├── find_cameras.py     # Helper script to find camera indices
├── dev_guide.md        # Original development guide
└── README.md           # This file
```

## Setup

1.  **Clone the repository or download files.**

2.  **Create a Python virtual environment (Recommended):**
    ```bash
    python -m venv venv
    # Activate:
    # Windows: .\venv\Scripts\activate
    # macOS/Linux: source venv/bin/activate
    ```

3.  **Install dependencies:**
    *   **For CPU Inference (Default hardcoded setting):**
        ```bash
        pip install -r requirements.txt
        ```
    *   **For GPU Inference:**
        If you intend to modify the code to use the GPU (`CONFIG_USE_GPU = True` in `main.py` and `processing.py`), ensure you have drivers/CUDA installed.
        *Comment out `onnxruntime` in `requirements.txt`* and install the GPU version:
        ```bash
        # Example for CUDA 11.x
        # pip install onnxruntime-gpu==1.15.1 # Choose appropriate version
        # Or for DirectML (Windows DX12 GPU)
        # pip install onnxruntime-directml==1.15.1

        # Then install the rest (excluding the removed yaml/crypto libs)
        pip install opencv-python numpy mss ultralytics
        ```

4.  **Download an ONNX Model:**
    *   Place your chosen object detection model (e.g., `yolov5n.onnx`) inside the `models/` directory.
    *   **Crucially:** Ensure the filename matches the `CONFIG_MODEL_PATH` variable hardcoded in `main.py` (`models/yolov5n.onnx` by default).

5.  **Verify Hardcoded Settings (If Necessary):**
    *   If the default hardcoded settings (like `CONFIG_CAPTURE_TYPE`, `CONFIG_DEVICE_INDEX`, `CONFIG_MODEL_PATH`, etc. in `main.py`) don't match your hardware or desired setup, **you must edit the Python files directly** (primarily `main.py` where they are defined) and potentially `capture.py`, `processing.py` where they might be used.
    *   Use `python find_cameras.py` to identify the correct `device_index` for your webcam/capture card if needed.

## Running the Application

1.  **Ensure your virtual environment is active.**
2.  **Run the main script:**
    ```bash
    python main.py
    ```
3.  An OpenCV window should appear displaying the video feed with bounding boxes.
4.  Press **'q'** in the output window to quit.

## Packaging with PyInstaller

To create a standalone executable for easier distribution or obfuscation, you can use PyInstaller.

1.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```

2.  **Generate Executable:**
    Navigate to the project's root directory in your terminal and run:

    ```bash
    pyinstaller --noconsole --onefile --name=esp_overlay_tool main.py
    ```

    *   `--noconsole`: Prevents the console window from appearing when the executable runs (important for overlays).
    *   `--onefile`: Packages everything into a single executable file.
    *   `--name=esp_overlay_tool`: Sets the name of the output executable and related files/folders.
    *   `main.py`: Specifies the main script of your application.

3.  **Include Assets (Models):**
    PyInstaller might not automatically include data files like your `.onnx` model. You need to tell it where to find them.

    *   **Option A (Using `--add-data`):**
        This is often the easiest way. You specify the source path and the destination path within the bundle. The syntax is `source:destination` or `source;destination` (use `;` on Windows, `:` on Mac/Linux).

        ```bash
        # Example for macOS/Linux (assuming model is in ./models)
        pyinstaller --noconsole --onefile --name=esp_overlay_tool --add-data "models/*.onnx:models" main.py

        # Example for Windows (assuming model is in ./models)
        pyinstaller --noconsole --onefile --name=esp_overlay_tool --add-data "models\\*.onnx;models" main.py
        ```
        Inside your code (`main.py` or wherever the model is loaded), you'll need to adjust the path to find the model within the packaged structure. PyInstaller sets up a temporary directory at runtime. You can get the base path like this:

        ```python
        import sys
        import os

        def resource_path(relative_path):
            """ Get absolute path to resource, works for dev and for PyInstaller """
            try:
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")

            return os.path.join(base_path, relative_path)

        # Example usage when loading the model:
        # model_path = resource_path("models/your_model.onnx")
        # model = cv2.dnn.readNetFromONNX(model_path)
        ```
        **Remember to replace `"models/your_model.onnx"` with your actual model file path relative to the project root and update the model loading code in `processing.py` to use `resource_path`.**

    *   **Option B (Spec File):**
        For more complex scenarios, you can generate a `.spec` file (`pyinstaller main.py`) and then edit it manually to include data files before building (`pyinstaller main.spec`). This offers more control.

4.  **Locate Executable:**
    After running PyInstaller, the executable will be located in the `dist` directory.

**Note:** Anti-cheat software often looks for signatures of known tools like PyInstaller. More advanced cheats might use custom loaders or packers to further obfuscate the executable.

## Anti-Cheat Testing Considerations

This version now simulates a cheat that:
*   Doesn't use an obvious `python.exe` process (when packaged).
*   Doesn't have external configuration files (`.yaml`, `.encrypted`).
*   Loads libraries dynamically.

Your anti-cheat should now focus on detecting:
*   Signatures of the packaged executable (`updater.exe`).
*   Signatures or behavior of the bundled libraries (`onnxruntime`, `opencv`, `mss`) in memory.
*   Behavioral analysis: screen capture API usage, high resource consumption, specific network patterns (if added back), window properties of the overlay.
*   Memory scanning for known cheat patterns or the model data itself. 