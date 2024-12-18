import cv2
import mediapipe as mp
import numpy as np

# Initialize MediaPipe Face Detection
mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.3)

# Access the default camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Unable to access the camera.")
    exit()

# Set resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Parameters
FRAME_WIDTH, FRAME_HEIGHT = 640, 480
ASPECT_RATIO = FRAME_WIDTH / FRAME_HEIGHT
ZOOM_SMOOTHING = 0.05  # Smooth factor for zoom transitions
TRANSLATE_SMOOTHING = 0.05  # Smooth factor for translation transitions
FS_MIN = 0.1  # Minimum face size to frame ratio
FS_TARGET_RATIO = 0.4  # Target ratio for zoom

# Variables for smooth transitions
smooth_frame_x, smooth_frame_y = 0, 0
smooth_zoom_height = FRAME_HEIGHT

print("Press 'q' to exit the video feed.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Unable to read from the camera.")
        break

    frame = cv2.flip(frame, 1)  # Flip horizontally for a natural mirror effect
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_height, frame_width = frame.shape[:2]

    # Detect faces
    results = face_detection.process(rgb_frame)
    target_frame_x, target_frame_y = smooth_frame_x, smooth_frame_y
    target_zoom_height = smooth_zoom_height

    # Prepare original feed
    original_feed = frame.copy()

    if results.detections:
        detection = results.detections[0]
        bbox = detection.location_data.relative_bounding_box

        # Calculate face center point (fcp) and face size (fs)
        face_center_x = int((bbox.xmin + bbox.width / 2) * frame_width)
        face_center_y = int((bbox.ymin + bbox.height / 2) * frame_height)
        face_size = max(bbox.width * frame_width, bbox.height * frame_height)
        fs_ratio = face_size / min(frame_width, frame_height)

        # Draw bounding box for face
        x_min = int(bbox.xmin * frame_width)
        y_min = int(bbox.ymin * frame_height)
        box_width = int(bbox.width * frame_width)
        box_height = int(bbox.height * frame_height)
        cv2.rectangle(original_feed, (x_min, y_min), (x_min + box_width, y_min + box_height), (0, 255, 0), 2)

        # Adjust zoom height based on face size
        if fs_ratio >= FS_MIN:
            target_zoom_height = int(FRAME_HEIGHT * 0.75)
        else:
            target_zoom_height = int(FRAME_HEIGHT / FS_MIN * fs_ratio)

        # Calculate target zoom width and frame position
        target_zoom_width = int(target_zoom_height * ASPECT_RATIO)
        target_frame_x = max(face_center_x - target_zoom_width // 2, 0)
        target_frame_y = max(face_center_y - target_zoom_height // 2, 0)

        # Ensure the frame stays within bounds
        target_frame_x = min(target_frame_x, frame_width - target_zoom_width)
        target_frame_y = min(target_frame_y, frame_height - target_zoom_height)

        # Dynamically define a smaller center box (10% of current frame size)
        center_box_width = int(target_zoom_width * 0.3)
        center_box_height = int(target_zoom_height * 0.3)
        center_box_x_min = (FRAME_WIDTH - center_box_width) // 2
        center_box_y_min = (FRAME_HEIGHT - center_box_height) // 2
        center_box_x_max = center_box_x_min + center_box_width
        center_box_y_max = center_box_y_min + center_box_height

        # Draw the dynamic center box
        cv2.rectangle(original_feed, (center_box_x_min, center_box_y_min),
                      (center_box_x_max, center_box_y_max), (255, 0, 0), 2)

        # If the face center point is outside the center box, nudge the frame
        if not (center_box_x_min <= face_center_x <= center_box_x_max and
                center_box_y_min <= face_center_y <= center_box_y_max):
            dx = face_center_x - (FRAME_WIDTH // 2)
            dy = face_center_y - (FRAME_HEIGHT // 2)
            target_frame_x += int(TRANSLATE_SMOOTHING * dx)
            target_frame_y += int(TRANSLATE_SMOOTHING * dy)

    # Smooth transitions for zoom and translation
    smooth_zoom_height += ZOOM_SMOOTHING * (target_zoom_height - smooth_zoom_height)
    smooth_frame_x += TRANSLATE_SMOOTHING * (target_frame_x - smooth_frame_x)
    smooth_frame_y += TRANSLATE_SMOOTHING * (target_frame_y - smooth_frame_y)

    # Calculate frame dimensions while maintaining aspect ratio
    smooth_zoom_width = int(smooth_zoom_height * ASPECT_RATIO)
    start_x = max(int(smooth_frame_x), 0)
    start_y = max(int(smooth_frame_y), 0)
    end_x = min(start_x + smooth_zoom_width, frame_width)
    end_y = min(start_y + smooth_zoom_height, frame_height)

    # Ensure all indices are integers
    start_x, start_y, end_x, end_y = map(int, [start_x, start_y, end_x, end_y])

    # Crop and resize the frame
    cropped_frame = frame[start_y:end_y, start_x:end_x]
    output_frame = cv2.resize(cropped_frame, (frame_width, frame_height))

    # Combine original and output feeds side by side
    combined_feed = np.hstack((original_feed, output_frame))

    # Display the combined feed
    cv2.imshow("Original Feed (Left) vs Output Feed (Right)", combined_feed)

    # Exit the loop when 'q' is pressed
    if cv2.waitKey(10) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
