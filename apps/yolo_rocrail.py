import sys
import socket
import time

import cv2
import numpy as np
from ultralytics import YOLO

print("Using Python:", sys.executable)
print("Version:", sys.version)

# =======================
# CONFIGURATION SECTION
# =======================

# 1) Camera source
# Use the SAME source that works in your test scripts
IP_CAM_URL = 0
# For IP camera, use:
# IP_CAM_URL = "rtsp://comboios:comboios2025@192.168.59.38:554/stream2"

# 2) Rocrail connection
ROCRAIL_HOST = "localhost"   # or IP of the PC running Rocrail
ROCRAIL_PORT = 8051          # check in Rocrail service interface

# 3) Loco ID and block actions
# Change LOCO_ID to an actual loco in your Rocrail plan
LOCO_ID = "ICE1"

# What to send to Rocrail when blocks change state
BLOCK_ACTIONS = {
    "BLOCK_A": {
        "occupied": f'<lc id="{LOCO_ID}" cmd="stop"/>',
        "free":     None,
    },
    "BLOCK_B": {
        "occupied": None,
        "free":     None,
    },
    # Add more blocks here if you like
}

# 4) Block zones (ROIs) in IMAGE PIXELS
# These coordinates are for the *resized* image (see DISPLAY_WIDTH below).
# Adjust these to match your camera view.
ROIS = {
    "BLOCK_A": [(100, 80), (260, 80), (260, 150), (100, 150)],
    "BLOCK_B": [(280, 80), (460, 80), (460, 160), (280, 160)],
}

# 5) YOLO model
MODEL_PATH = "yolo11n.pt"  # nano model = small & fast
ACCEPTED_CLASSES = None    # None = accept all classes

# 6) Performance tuning
DISPLAY_WIDTH = 640   # resize frames to this width (keeps aspect ratio)
FRAME_SKIP = 3        # run YOLO every N frames (e.g., 3 = every 3rd frame)


# =======================
# HELPER FUNCTIONS
# =======================

def connect_rocrail(host: str, port: int) -> socket.socket:
    """Open TCP connection to Rocrail server."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    print(f"? Connected to Rocrail at {host}:{port}")
    return s


def send_xml(sock: socket.socket, xml_str: str):
    """Send one XML command to Rocrail (newline-terminated)."""
    msg = xml_str.strip() + "\n"
    print(f"? Rocrail: {msg.strip()}")
    sock.sendall(msg.encode("utf-8"))


def point_in_poly(point, poly) -> bool:
    """Return True if point (x, y) lies inside polygon poly."""
    x, y = point
    poly_arr = np.array(poly, dtype=np.int32)
    return cv2.pointPolygonTest(poly_arr, (x, y), False) >= 0


def resize_keep_aspect(frame, new_width):
    """Resize frame to given width, keep aspect ratio."""
    h, w = frame.shape[:2]
    scale = new_width / float(w)
    new_height = int(h * scale)
    resized = cv2.resize(frame, (new_width, new_height))
    return resized


# =======================
# MAIN
# =======================

def main():
    # Connect to Rocrail
    try:
        rr_sock = connect_rocrail(ROCRAIL_HOST, ROCRAIL_PORT)
    except Exception as e:
        print("? Could not connect to Rocrail:")
        print(e)
        return

    # Open camera
    cap = cv2.VideoCapture(IP_CAM_URL)
    if not cap.isOpened():
        print("? Could not open camera")
        return
    print("? Camera opened")

    # Load YOLO model
    print("? Loading YOLO model...")
    model = YOLO(MODEL_PATH)
    print("? YOLO loaded")

    # Track occupancy state to avoid spamming Rocrail
    block_occupied = {name: False for name in ROIS.keys()}

    # For performance: only run YOLO every N frames
    frame_count = 0
    last_boxes = None  # cache of last YOLO detections

    print("Press ESC in the video window to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("? Failed to grab frame from camera")
            time.sleep(0.05)
            continue

        # Resize frame for faster processing
        small = resize_keep_aspect(frame, DISPLAY_WIDTH)

        frame_count += 1
        run_yolo_now = (frame_count % FRAME_SKIP == 0)

        if run_yolo_now:
            # Run YOLO on the smaller image
            results = model.predict(small, imgsz=DISPLAY_WIDTH, verbose=False)[0]
            last_boxes = results.boxes
        else:
            results = None  # not used, we keep last_boxes

        detections = []

        # Use last_boxes (from latest YOLO run) to draw and compute centers
        if last_boxes is not None:
            for box in last_boxes:
                cls_id = int(box.cls.item())
                if ACCEPTED_CLASSES is not None and cls_id not in ACCEPTED_CLASSES:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                detections.append((cx, cy))

                # Draw box & label on the resized image
                label = model.names.get(cls_id, str(cls_id))
                conf = float(box.conf.item())
                cv2.rectangle(small, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    small,
                    f"{label} {conf:.2f}",
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                )
                cv2.circle(small, (cx, cy), 4, (0, 0, 255), -1)

        # Check each block ROI for occupancy using detection centers
        for block_name, poly in ROIS.items():
            occ_now = any(point_in_poly(pt, poly) for pt in detections)
            occ_before = block_occupied[block_name]

            if occ_now != occ_before:
                block_occupied[block_name] = occ_now
                state_str = "OCCUPIED" if occ_now else "FREE"
                print(f"[{block_name}] ? {state_str}")

                actions = BLOCK_ACTIONS.get(block_name, {})
                xml_cmd = actions.get("occupied" if occ_now else "free")
                if xml_cmd:
                    try:
                        send_xml(rr_sock, xml_cmd)
                    except Exception as e:
                        print("? Error sending to Rocrail:", e)

        # Draw the block ROIs on the resized image
        for block_name, poly in ROIS.items():
            pts = np.array(poly, dtype=np.int32)
            color = (255, 0, 0)
            cv2.polylines(small, [pts], isClosed=True, color=color, thickness=2)
            x_text = poly[0][0]
            y_text = poly[0][1] - 10
            cv2.putText(
                small,
                block_name,
                (x_text, y_text),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

        # Show the window
        cv2.imshow("YOLO + Rocrail Monitor (Fast)", small)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()
    rr_sock.close()
    print("? Exiting YOLO + Rocrail monitor")


if __name__ == "__main__":
    main()
