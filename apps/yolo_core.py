import time
import cv2
from ultralytics import YOLO

# MESMO URL que funciona no teu yolo_cam.py
IP_CAM_URL = "rtsp://comboios:comboios2025@192.168.59.38:554/stream2"

# Modelo YOLO carregado uma vez
_model = None


def get_model():
    global _model
    if _model is None:
        print("[YOLO_CORE] Loading YOLO model (yolo11n.pt)...")
        _model = YOLO("yolo11n.pt")
        print("[YOLO_CORE] YOLO loaded.")
    return _model


def open_camera():
    """
    Tenta abrir a câmara RTSP e devolve o cap.
    Se não conseguir, devolve None.
    """
    print(f"[YOLO_CORE] Opening camera: {IP_CAM_URL}")
    cap = cv2.VideoCapture(IP_CAM_URL, cv2.CAP_FFMPEG)

    if not cap.isOpened():
        print("[YOLO_CORE] ? Could not open camera.")
        cap.release()
        return None

    print("[YOLO_CORE] ? Camera opened.")
    return cap


def yolo_camera():
    """
    Gerador MJPEG usado pelo Flask:
      return Response(yolo_camera(), mimetype="multipart/x-mixed-replace; boundary=frame")
    Faz reconexão automática se a câmara falhar.
    """

    model = get_model()

    cap = open_camera()
    # Se não abriu à primeira, fica num ciclo a tentar
    while cap is None:
        print("[YOLO_CORE] Waiting 5s before retrying camera...")
        time.sleep(5)
        cap = open_camera()

    while True:
        ok, frame = cap.read()

        if not ok or frame is None:
            print("[YOLO_CORE] ? Failed to grab frame. Reopening camera...")
            cap.release()
            time.sleep(2)

            cap = open_camera()
            if cap is None:
                # Se ainda não consegue abrir, espera e tenta outra vez
                time.sleep(5)
                continue
            else:
                # Volta ao loop normal
                continue

        # ------------ YOLO INFERENCE ------------
        results = model.predict(frame, verbose=False)[0]

        # Desenhar caixas no frame
        if results.boxes is not None:
            for box in results.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cls_id = int(box.cls.item())
                conf = float(box.conf.item())
                label = model.names.get(cls_id, str(cls_id))

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                text = f"{label} {conf:.2f}"
                cv2.putText(frame, text, (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (0, 255, 0), 1)

        # ------------ ENCODE -> MJPEG ------------
        ret, buffer = cv2.imencode(".jpg", frame)
        if not ret:
            print("[YOLO_CORE] ? Failed to encode frame to JPEG.")
            continue

        jpg_bytes = buffer.tobytes()

        # Formato MJPEG
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" +
               jpg_bytes +
               b"\r\n")


# Se tiveres também lógica de BLOCO / YOLO para /api/blocks, podes manter aqui em baixo
# (não mexi nessa parte porque ainda não mostraste erro aí).
