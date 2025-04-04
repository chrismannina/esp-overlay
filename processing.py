# processing.py
import onnxruntime as ort
import numpy as np
import time
import threading
from queue import Queue, Empty
from utils import logger
import cv2 # Needed for preprocessing/NMS if not handled by model directly

class AIProcessor:
    """Handles AI model inference in a separate thread."""
    def __init__(self, frame_queue, results_queue, config):
        self.frame_queue = frame_queue
        self.results_queue = results_queue
        self.config = config['ai']
        self.use_gpu = config.get('use_gpu', False)

        self._stop_event = threading.Event()
        self._processing_thread = None

        self.session = None
        self.input_name = None
        self.input_shape = None # Expected input shape (batch, height, width, channels)

        self._load_model()

    def _load_model(self):
        """Loads the ONNX model and prepares the inference session."""
        model_path = self.config['model_path']
        logger.info(f"Loading ONNX model from: {model_path}")
        try:
            providers = ort.get_available_providers()
            logger.info(f"Available ONNX Runtime providers: {providers}")
            provider_options = []
            chosen_provider = 'CPUExecutionProvider'
            if self.use_gpu:
                if 'CUDAExecutionProvider' in providers:
                    chosen_provider = 'CUDAExecutionProvider'
                    # Potential: Add provider options like GPU ID here if needed
                    # provider_options = [{'device_id': 0}]
                elif 'DmlExecutionProvider' in providers:
                    chosen_provider = 'DmlExecutionProvider'
                else:
                    logger.warning("GPU requested, but neither CUDA nor DirectML provider found. Falling back to CPU.")
            else:
                 logger.info("Using CPU provider for ONNX Runtime.")

            logger.info(f"Using ONNX Runtime provider: {chosen_provider}")
            self.session = ort.InferenceSession(model_path, providers=[chosen_provider], provider_options=provider_options)

            # Get model input details
            input_meta = self.session.get_inputs()[0]
            self.input_name = input_meta.name
            self.input_shape = input_meta.shape # e.g., [1, 3, 640, 640]
            logger.info(f"Model loaded. Input name: {self.input_name}, Expected input shape: {self.input_shape}")

            # Basic check for typical YOLO input shape (adjust if your model differs)
            if len(self.input_shape) != 4 or self.input_shape[0] != 1:
                 logger.warning("Model input shape might not be standard BHWC or BCHW. Ensure preprocessing matches.")

        except Exception as e:
            logger.error(f"Failed to load ONNX model or create session: {e}", exc_info=True)
            self.session = None # Ensure session is None if loading failed

    def _preprocess(self, frame):
        """Prepares a frame for the ONNX model. Assumes YOLOv5 style preprocessing."""
        if self.input_shape is None:
            logger.error("Cannot preprocess: Model input shape not determined.")
            return None

        # Assuming input shape is [batch, channels, height, width]
        model_height = self.input_shape[2]
        model_width = self.input_shape[3]

        # 1. Resize and Pad
        img = frame.copy()
        img_height, img_width = img.shape[:2]
        # Calculate scale ratio and padding
        r = min(model_height / img_height, model_width / img_width)
        new_unpad_w, new_unpad_h = int(round(img_width * r)), int(round(img_height * r))
        dw, dh = (model_width - new_unpad_w) / 2, (model_height - new_unpad_h) / 2

        if (img_width, img_height) != (new_unpad_w, new_unpad_h):
            img = cv2.resize(img, (new_unpad_w, new_unpad_h), interpolation=cv2.INTER_LINEAR)

        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))

        # 2. BGR to RGB and HWC to CHW
        img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB, HWC to CHW
        img = np.ascontiguousarray(img)

        # 3. Normalize to [0, 1] and Convert to float16 (as expected by model)
        img = img.astype(np.float16) / 255.0

        # 4. Add Batch Dimension
        img = np.expand_dims(img, axis=0)

        return img, r, (dw, dh) # Return preprocessed image and scaling info

    def _postprocess(self, outputs, scale_ratio, pad_offset, frame_shape):
        """Processes the raw model output. Assumes YOLOv5 output format."""
        # Output format typically [batch, num_detections, xywh + confidence + num_classes]
        # Example shape: [1, 25200, 85] for COCO (80 classes + 5)
        predictions = outputs[0][0] # Get predictions for the first (only) image in the batch

        # Filter by confidence
        conf_thres = self.config['confidence_threshold']
        candidates = predictions[predictions[:, 4] > conf_thres]

        if not candidates.shape[0]:
            return []

        # Filter by class if specified
        classes_to_detect = self.config.get('classes_to_detect')
        if classes_to_detect is not None and len(classes_to_detect) > 0:
            class_probs = candidates[:, 5:]
            class_indices = np.argmax(class_probs, axis=1)
            class_scores = np.max(class_probs, axis=1)

            mask = np.isin(class_indices, classes_to_detect)
            candidates = candidates[mask]
            class_indices = class_indices[mask]
            class_scores = class_scores[mask]

            if not candidates.shape[0]:
                return []
            # Overwrite confidence with class-specific score
            candidates[:, 4] = class_scores
        else:
            # Use the objectness score and find the best class
            class_probs = candidates[:, 5:]
            class_indices = np.argmax(class_probs, axis=1)
            class_scores = np.max(class_probs, axis=1)
            # Combine objectness and class score? Or just use objectness? Stick to objectness for now.
            # candidates[:, 4] = candidates[:, 4] * class_scores # Combined score

        # Convert xywh to xyxy
        boxes_xywh = candidates[:, :4]
        boxes_xyxy = np.zeros_like(boxes_xywh)
        boxes_xyxy[:, 0] = boxes_xywh[:, 0] - boxes_xywh[:, 2] / 2  # x_center - width/2 = x1
        boxes_xyxy[:, 1] = boxes_xywh[:, 1] - boxes_xywh[:, 3] / 2  # y_center - height/2 = y1
        boxes_xyxy[:, 2] = boxes_xywh[:, 0] + boxes_xywh[:, 2] / 2  # x_center + width/2 = x2
        boxes_xyxy[:, 3] = boxes_xywh[:, 1] + boxes_xywh[:, 3] / 2  # y_center + height/2 = y2

        # Adjust coordinates from model input size back to original frame size
        # 1. Remove padding
        pad_w, pad_h = pad_offset
        boxes_xyxy[:, [0, 2]] -= pad_w
        boxes_xyxy[:, [1, 3]] -= pad_h
        # 2. Rescale to original size
        boxes_xyxy /= scale_ratio

        # Clip boxes to frame dimensions
        frame_h, frame_w = frame_shape[:2]
        boxes_xyxy[:, [0, 2]] = np.clip(boxes_xyxy[:, [0, 2]], 0, frame_w)
        boxes_xyxy[:, [1, 3]] = np.clip(boxes_xyxy[:, [1, 3]], 0, frame_h)

        # Perform Non-Maximum Suppression (NMS)
        confidences = candidates[:, 4]
        nms_thres = self.config['nms_threshold']

        # Use cv2.dnn.NMSBoxes for simplicity
        # Convert boxes to required format (x, y, w, h)
        boxes_for_nms = np.zeros_like(boxes_xyxy)
        boxes_for_nms[:, 0] = boxes_xyxy[:, 0]
        boxes_for_nms[:, 1] = boxes_xyxy[:, 1]
        boxes_for_nms[:, 2] = boxes_xyxy[:, 2] - boxes_xyxy[:, 0]
        boxes_for_nms[:, 3] = boxes_xyxy[:, 3] - boxes_xyxy[:, 1]

        indices = cv2.dnn.NMSBoxes(boxes_for_nms.tolist(), confidences.tolist(), conf_thres, nms_thres)

        detections = []
        if len(indices) > 0:
             # If indices is a flat array (possible with OpenCV NMS), flatten it
            if isinstance(indices, np.ndarray): indices = indices.flatten()

            for i in indices:
                box = boxes_xyxy[i].astype(int).tolist() # Convert to int list [x1, y1, x2, y2]
                confidence = float(confidences[i])
                class_id = int(class_indices[i])
                detections.append({
                    'bbox': box,          # [x_min, y_min, x_max, y_max]
                    'confidence': confidence,
                    'class_id': class_id
                    # Add other info like 'label' if you have a class map
                })
        return detections


    def _processing_loop(self):
        """Continuously fetches frames, preprocesses, infers, and postprocesses."""
        if not self.session:
            logger.error("Processing loop cannot start: ONNX session not initialized.")
            return

        logger.info("AI processing thread started.")
        while not self._stop_event.is_set():
            try:
                # Get the latest frame from the queue (block briefly if empty)
                timestamp, frame = self.frame_queue.get(timeout=0.1)
            except Empty:
                continue # No frame available, loop again
            except Exception as e:
                logger.error(f"Error getting frame from queue: {e}")
                time.sleep(0.1)
                continue

            if frame is None:
                 logger.warning("Received None frame in processing loop.")
                 continue

            start_time = time.perf_counter()

            # 1. Preprocess
            processed_frame, scale_ratio, pad_offset = self._preprocess(frame)
            if processed_frame is None:
                 continue # Skip frame if preprocessing fails

            preprocess_end_time = time.perf_counter()

            # 2. Inference
            try:
                outputs = self.session.run(None, {self.input_name: processed_frame})
            except Exception as e:
                logger.error(f"ONNX Runtime inference failed: {e}", exc_info=True)
                continue # Skip frame if inference fails

            inference_end_time = time.perf_counter()

            # 3. Postprocess
            detections = self._postprocess(outputs, scale_ratio, pad_offset, frame.shape)
            postprocess_end_time = time.perf_counter()

            # Timing logs (optional)
            t_preprocess = (preprocess_end_time - start_time) * 1000
            t_inference = (inference_end_time - preprocess_end_time) * 1000
            t_postprocess = (postprocess_end_time - inference_end_time) * 1000
            t_total = (postprocess_end_time - start_time) * 1000
            logger.debug(f"Processing Time: Total={t_total:.1f}ms (Pre={t_preprocess:.1f} + Infer={t_inference:.1f} + Post={t_postprocess:.1f}), Detections: {len(detections)}")

            # 4. Put results into the output queue
            # Combine original frame and detections
            result_data = {
                'timestamp': timestamp,
                'frame': frame, # Pass the original frame along
                'detections': detections
            }
            try:
                self.results_queue.put(result_data, timeout=0.1)
            except Full:
                # If results queue is full, maybe the display loop is stuck?
                # Log a warning, maybe drop older results?
                logger.warning("Results queue is full. Display might be lagging.")
                try:
                     self.results_queue.get_nowait() # Drop oldest result
                     self.results_queue.put_nowait(result_data)
                except Exception as e_inner:
                     logger.warning(f"Error managing full results queue: {e_inner}")
            except Exception as e:
                 logger.error(f"Error putting results in queue: {e}")


        logger.info("AI processing thread finished.")


    def start(self):
        """Starts the processing thread."""
        if self._processing_thread is not None:
            logger.warning("Processing thread already running.")
            return
        if not self.session:
            logger.error("Cannot start processing thread: Model not loaded.")
            return

        logger.info("Starting AI processing thread...")
        self._stop_event.clear()
        self._processing_thread = threading.Thread(target=self._processing_loop, name="AIProcessorThread")
        self._processing_thread.daemon = True
        self._processing_thread.start()

    def stop(self):
        """Signals the processing thread to stop."""
        if self._processing_thread is None:
            logger.warning("Processing thread not running.")
            return
        logger.info("Stopping AI processing thread...")
        self._stop_event.set()
        self._processing_thread.join(timeout=2)
        if self._processing_thread.is_alive():
             logger.warning("AI Processing thread did not stop gracefully.")
        self._processing_thread = None
        logger.info("AI processing thread stopped.") 