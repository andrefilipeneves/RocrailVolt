from flask import render_template, Response, jsonify, request, redirect, url_for
from apps.home import blueprint
from apps.yolo_core import yolo_camera
from apps.rocrail_core import rocrail, LOCO_DEFAULT
from apps.rocrail_plan import parse_plan
from apps.cs3_client import get_cs3
from apps.rc_car_core import rc_car
import json
from pathlib import Path

import time

from apps.yolo_core import yolo_camera
...
@blueprint.route("/yolo-stream")
def yolo_stream():
    return Response(
        yolo_camera(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )




AUTO_MODE = False


#----------------
# API Switch
# ------

@blueprint.route("/api/switch-positions", methods=["GET", "POST"])
def api_switch_positions():
    """
    GET -> devolve switch_positions.json (cria default se não existir)
    POST -> recebe JSON { "SW1": [x,y], ... } e grava em ficheiro
    """
    if request.method == "GET":
        data = load_switch_positions()
        return jsonify(data)

    # POST
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            return jsonify({"status": "error", "error": "JSON inválido"}), 400
        save_switch_positions(data)
        return jsonify({"status": "ok"})
    except Exception as e:
        print("[SWITCH-POS] erro ao gravar:", e)
        return jsonify({"status": "error", "error": str(e)}), 500



# ---------------------------------------------------
# HOME / DASHBOARD PAGES
# ---------------------------------------------------

@blueprint.route("/api/rocrail/switches")
def api_rocrail_switches():
    """
    Devolve a lista de agulhas (switches) do plan.xml.
    """
    plan = parse_plan()
    switches = plan.get("switches", [])
    return jsonify(switches)





@blueprint.route("/api/rocrail/switch", methods=["POST"])
def api_rocrail_switch():
    """
    Controla uma agulha específica.
    Espera JSON: { "id": "SW1", "cmd": "straight" } ou "turnout"
    """
    data = request.json or {}
    sw_id = data.get("id")
    cmd = (data.get("cmd") or "straight").lower()

    if not sw_id:
        return jsonify({"status": "error", "error": "missing id"}), 400

    print(f"[SWITCH] id={sw_id} cmd={cmd}")
    try:
        rocrail.set_switch(sw_id, cmd)
        return jsonify({"status": "ok"})
    except Exception as e:
        print("[SWITCH] erro:", e)
        return jsonify({"status": "error", "error": str(e)}), 500


@blueprint.route("/ai-dashboard")
def ai_dashboard():
    return render_template("home/ai_dashboard.html")


@blueprint.route('/roi-editor')
def roi_editor():
    # Página para desenhar blocos/ROIs em cima do vídeo
    return render_template('home/roi_editor.html')

@blueprint.route("/layout-map")
def layout_map():
    return render_template("home/layout_map.html")

@blueprint.route("/api/rocrail/plan")
def api_rocrail_plan():
    """
    Devolve o resumo do plan.xml (sem cache, lê sempre).
    """
    plan = parse_plan()
    return jsonify(plan)

@blueprint.route("/fleet")
def fleet():
    """
    Página de frota de locomotivas.
    Lê o plan.xml via parse_plan() e envia a lista de locos para o template.
    Mesmo que parse_plan() falhe, devolve uma lista vazia em segurança.
    """
    try:
        plan_data = parse_plan()
    except Exception as e:
        print("[FLEET] Erro em parse_plan():", e)
        plan_data = {"locos": []}

    locos = plan_data.get("locos", []) or []

    return render_template("home/fleet.html", locos=locos)




@blueprint.route("/api/train/function", methods=["POST"])
def api_train_function():
    """
    Liga/desliga função F0, F1, F2... de uma locomotiva.
    Espera JSON: { "loco_id": "ICE1", "fn_no": 0, "state": true }
    """
    data = request.json or {}
    loco_id = data.get("loco_id", LOCO_DEFAULT)
    fn_no = int(data.get("fn_no", 0))
    state = bool(data.get("state", True))

    print(f"[TRAIN-FN] loco={loco_id} fn={fn_no} state={state}")
    try:
        rocrail.set_function(loco_id, fn_no, state)
        return jsonify({"status": "ok"})
    except Exception as e:
        print("[TRAIN-FN] erro:", e)
        return jsonify({"status": "error", "error": str(e)}), 500

@blueprint.route("/api/train/direction", methods=["POST"])
def api_train_direction():
    """
    Define a direção da loco.
    JSON: { "loco_id": "ICE1", "direction": "fwd" } ou "rev"
    """
    data = request.json or {}
    loco_id = data.get("loco_id", LOCO_DEFAULT)
    direction = data.get("direction", "fwd")
    forward = direction != "rev"

    print(f"[TRAIN-DIR] loco={loco_id} forward={forward}")
    try:
        rocrail.set_direction(loco_id, forward)
        return jsonify({"status": "ok"})
    except Exception as e:
        print("[TRAIN-DIR] erro:", e)
        return jsonify({"status": "error", "error": str(e)}), 500

@blueprint.route("/switch-editor")
def switch_editor():
    return render_template("home/switch_editor.html")


# ---------------------------------------------------
# YOLO VIDEO STREAM
# ---------------------------------------------------

@blueprint.route("/video_feed")
def video_feed():
    def generate():
        while True:
            frame = yolo_camera.get_jpeg()
            if frame is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" +
                    frame +
                    b"\r\n"
                )
            else:
                time.sleep(0.05)
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")



# ---------------------------------------------------
# TRAIN CONTROL (ROCRAIL API)
# ---------------------------------------------------

@blueprint.route("/api/train/stop", methods=["POST"])
def api_train_stop():
    data = request.json
    loco_id = data.get("loco_id", LOCO_DEFAULT)
    rocrail.stop_loco(loco_id)
    return jsonify({"status": "ok"})


@blueprint.route("/api/train/go", methods=["POST"])
def api_train_go():
    data = request.json
    loco_id = data.get("loco_id", LOCO_DEFAULT)
    speed = int(data.get("speed", 40))
    rocrail.go_loco(loco_id, speed)
    return jsonify({"status": "ok"})


@blueprint.route("/api/train/preset_speed", methods=["POST"])
def api_train_preset_speed():
    data = request.json
    loco_id = data.get("loco_id", LOCO_DEFAULT)
    preset = data.get("preset", "cruise")

    if preset == "slow":
        speed = 20
    elif preset == "cruise":
        speed = 40
    elif preset == "fast":
        speed = 70
    else:
        speed = 40

    rocrail.go_loco(loco_id, speed)
    return jsonify({"status": "ok", "speed": speed})


@blueprint.route("/api/train/emergency_stop", methods=["POST"])
def api_train_emergency_stop():
    rocrail.stop_loco()
    return jsonify({"status": "ok"})


SWITCH_POS_FILE = Path("static/layouts/switch_positions.json")


def load_switch_positions():
    """
    Lê o ficheiro JSON com as posições visuais das agulhas.
    Se não existir, cria um dict básico a partir do plan.xml.
    """
    if SWITCH_POS_FILE.exists():
        with SWITCH_POS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)

    # Ficheiro não existe ? criar posições simples a partir do plan.xml
    plan = parse_plan()
    switches = plan.get("switches", [])
    positions = {}

    # Usamos x,y do Rocrail se existirem; caso contrário, metemos (50, 50)
    for sw in switches:
        sw_id = sw.get("id")
        if not sw_id:
            continue

        try:
            x = float(sw.get("x") or 50)
            y = float(sw.get("y") or 50)
        except ValueError:
            x, y = 50.0, 50.0

        positions[sw_id] = [x, y]

    save_switch_positions(positions)
    return positions


def save_switch_positions(data):
    SWITCH_POS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SWITCH_POS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------
# RC CAR API
# ---------------------------------------------------

@blueprint.route("/api/car/command", methods=["POST"])
def api_car_command():
    data = request.json
    print("[RC-CAR] Command:", data)
    return jsonify({"status": "ok"})


# ---------------------------------------------------
# YOLO BLOCKS API
# ---------------------------------------------------

@blueprint.route("/api/blocks")
def api_blocks():
    """
    Devolve o estado dos blocos a partir do yolo_camera.
    Vamos tentar usar um método get_blocks_state(), ou um atributo blocks,
    e se não existir devolvemos {} para não rebentar.
    """
    try:
        # se implementaste get_blocks_state() em yolo_core.YOLOCamera
        if hasattr(yolo_camera, "get_blocks_state"):
            return jsonify(yolo_camera.get_blocks_state())

        # fallback: se existir atributo .blocks (dict)
        if hasattr(yolo_camera, "blocks"):
            return jsonify(yolo_camera.blocks)

        # se não houver nada, devolve vazio
        return jsonify({})
    except Exception as e:
        print("[api_blocks] erro a obter blocos:", e)
        return jsonify({})


@blueprint.route("/api/roi/save", methods=["POST"])
def api_roi_save():
    """
    Recebe do browser a lista de ROIs desenhados.
    Por agora só imprime no terminal e devolve ok.
    Depois podemos ligar isto a ficheiros/DB.
    """
    data = request.json or {}
    print("[ROI-SAVE] Recebido:", data)
    return jsonify({"status": "ok"})

# ---------------------------------------------------
# AUTO MODE SWITCH
# ---------------------------------------------------

@blueprint.route("/api/ai/auto_mode", methods=["POST"])
def api_auto_mode():
    global AUTO_MODE
    data = request.json
    AUTO_MODE = bool(data.get("enabled", False))
    print("[AI MODE]", "ENABLED" if AUTO_MODE else "DISABLED")
    return jsonify({"auto_mode": AUTO_MODE})

@blueprint.route("/api/rocrail/tracks")
def api_rocrail_tracks():
    """
    Devolve a lista de elementos gráficos (tracks) do track plan do Rocrail.
    """
    plan = parse_plan()
    return jsonify(plan.get("tracks", []))


# ---------------------------------------------------
# CS3
# ---------------------------------------------------

@blueprint.route("/api/cs3/status")
def api_cs3_status():
    """
    Devolve estado da ligação à CS3.
    """
    client = get_cs3()
    return jsonify(client.get_status())

@blueprint.route("/api/cs3/turnout", methods=["POST"])
def api_cs3_turnout():
    """
    Muda uma agulha diretamente na CS3.
    JSON: { "id": "SW1", "position": "straight" } ou "turnout"
    """
    data = request.json or {}
    turnout_id = data.get("id")
    pos = data.get("position", "straight")

    if not turnout_id:
        return jsonify({"status": "error", "error": "missing id"}), 400

    client = get_cs3()
    try:
        client.set_turnout(turnout_id, pos)
        return jsonify({"status": "ok"})
    except Exception as e:
        print("[CS3] erro em /api/cs3/turnout:", e)
        return jsonify({"status": "error", "error": str(e)}), 500

@blueprint.route("/api/cs3/refresh", methods=["POST"])
def api_cs3_refresh():
    """
    Triggers para pedir lista de locos/turnouts da CS3 (a implementar no cs3_client).
    """
    client = get_cs3()
    client.request_loco_list()
    client.request_turnout_list()
    return jsonify({"status": "ok"})

@blueprint.route("/cs3-status")
def cs3_status():
    return render_template("home/cs3_status.html")

@blueprint.route("/api/rc/status")
def api_rc_status():
    """
    Estado atual do RC car.
    """
    return jsonify(rc_car.get_status())


@blueprint.route("/api/rc/manual", methods=["POST"])
def api_rc_manual():
    """
    Comando manual para o RC car.
    Espera JSON: { "steering": -1..1, "throttle": -1..1 }
    """
    data = request.json or {}
    steering = float(data.get("steering", 0.0))
    throttle = float(data.get("throttle", 0.0))
    rc_car.set_manual_command(steering, throttle)
    return jsonify({"status": "ok"})


@blueprint.route("/api/rc/autopilot", methods=["POST"])
def api_rc_autopilot():
    """
    Ativa/desativa autopilot.
    Espera JSON: { "enabled": true/false }
    """
    data = request.json or {}
    enabled = bool(data.get("enabled", False))
    rc_car.enable_autopilot(enabled)
    return jsonify({"status": "ok", "autopilot": enabled})

## RC CAR

@blueprint.route("/api/rc/emergency_stop", methods=["POST"])
def api_rc_emergency_stop():
    """
    Paragem de emergência.
    """
    rc_car.emergency_stop()
    return jsonify({"status": "ok"})

@blueprint.route("/rc-dashboard")
def rc_dashboard():
    return render_template("home/rc_dashboard.html")

