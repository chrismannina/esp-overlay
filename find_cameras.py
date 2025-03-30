import cv2
import sys
import time

def list_available_cameras(max_test=10):
    """Tries to open camera indices and lists the ones that work."""
    available_indices = []
    print(f"Scanning for available camera devices (indices 0 to {max_test - 1})...")
    for i in range(max_test):
        cap = cv2.VideoCapture(i, cv2.CAP_ANY) # Or just cv2.VideoCapture(i)
        if cap is not None and cap.isOpened():
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            print(f"  Index {i}: Found - Resolution {int(width)}x{int(height)}")
            available_indices.append(i)
            cap.release()
        else:
             # Optional: print(f"  Index {i}: Not available or failed to open.")
             if cap is not None:
                cap.release()
    print("-" * 30)
    if not available_indices:
        print("No camera devices found.")
    else:
        print(f"Available device indices: {available_indices}")
    print("-" * 30)
    return available_indices

def test_camera(index):
    """Opens a specific camera index and displays the feed."""
    print(f"\nAttempting to open camera index {index}...")
    cap = cv2.VideoCapture(index, cv2.CAP_ANY) # Or just cv2.VideoCapture(index)

    if not cap.isOpened():
        print(f"ERROR: Could not open camera index {index}.")
        print("Check if the device is connected, not in use by another app, or try a different index.")
        return

    print("Camera opened successfully.")
    print("Displaying feed. CLICK THE WINDOW, then press 'q' to close.")

    window_title = f"Test Camera Index {index}"
    start_time = time.time()
    frame_count = 0
    fps = 0

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("Error: Failed to grab frame.")
            break

        frame_count += 1
        elapsed_time = time.time() - start_time
        if elapsed_time >= 1.0:
            fps = frame_count / elapsed_time
            start_time = time.time()
            frame_count = 0

        # Display FPS on frame
        cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow(window_title, frame)

        key = cv2.waitKey(10) & 0xFF
        if key != 255:
             print(f"Key pressed: {key} (ASCII: {chr(key) if 32 <= key <= 126 else 'N/A'})")

        if key == ord('q'):
            print("'q' detected, closing window.")
            break

    # Release resources
    cap.release()
    cv2.destroyAllWindows()
    print(f"Closed camera index {index}.")

if __name__ == "__main__":
    available = list_available_cameras()

    if not available:
        sys.exit("No cameras to test.")

    while True:
        try:
            test_index_str = input(f"Enter an index from {available} to test (or 'q' to quit): ")
            if test_index_str.lower() == 'q':
                break
            test_index = int(test_index_str)
            if test_index in available:
                test_camera(test_index)
            else:
                print(f"Invalid index. Please choose from {available}.")
        except ValueError:
            print("Invalid input. Please enter a number or 'q'.")
        except Exception as e:
             print(f"An error occurred: {e}")

    print("Exiting camera test script.") 