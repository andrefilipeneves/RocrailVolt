import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List


# ?? MUITO IMPORTANTE:
# Mete aqui o caminho REAL do teu plan.xml do Rocrail.
ROCRAIL_PLAN_PATH = Path(
    r"C:\Users\andre\Downloads\Rocrail-Windows-WIN64\bin\plan.xml"
    # ajusta se o teu workspace for outro
)


def parse_plan() -> Dict[str, Any]:
    """
    Lê o plan.xml do Rocrail e devolve:
    {
      "blocks": [...],
      "locos": [...],
      "switches": [...],
      "sensors": [...],
      "tracks": [...],
    }
    """

    path = ROCRAIL_PLAN_PATH
    print("[rocrail_plan] A LER:", path)

    if not path.exists():
        print("[rocrail_plan] FICHEIRO NAO ENCONTRADO!")
        return {
            "blocks": [],
            "locos": [],
            "switches": [],
            "sensors": [],
            "tracks": [],
        }

    tree = ET.parse(path)
    root = tree.getroot()

    blocks: List[Dict[str, Any]] = []
    locos: List[Dict[str, Any]] = []
    switches: List[Dict[str, Any]] = []
    sensors: List[Dict[str, Any]] = []
    tracks: List[Dict[str, Any]] = []

    # ---------- BLOCS ----------
    for b in root.findall(".//block"):
        blocks.append({
            "id": b.get("id"),
            "desc": b.get("desc"),
            "type": b.get("type"),
            "x": b.get("x"),
            "y": b.get("y"),
            "z": b.get("z"),
        })

    # ---------- LOCOS ----------
    # Rocrail costuma usar <loc> para locomotivas; nalguns casos existe <lc>.
    loco_elements = root.findall(".//loc")
    loco_elements += root.findall(".//lc")

    print(f"[rocrail_plan] Encontradas {len(loco_elements)} tags de loco (<loc> ou <lc>)")

    for lc in loco_elements:
        loco_id = lc.get("id")
        addr = lc.get("addr")
        desc = lc.get("desc")
        protoc = lc.get("prot")
        image = lc.get("image")
        max_speed = lc.get("V_max")

        functions: List[Dict[str, Any]] = []
        for fn in lc.findall("fn"):
            functions.append({
                "no": fn.get("no"),
                "text": fn.get("text"),
                "icon": fn.get("icon"),
                "type": fn.get("type"),
                "state": fn.get("state"),
            })

        locos.append({
            "id": loco_id,
            "addr": addr,
            "desc": desc,
            "protocol": protoc,
            "image": image,
            "max_speed": max_speed,
            "functions": functions,
        })

    # ---------- SWITCHES (AGULHAS) ----------
    for sw in root.findall(".//switch"):
        switches.append({
            "id": sw.get("id"),
            "addr": sw.get("addr"),
            "port": sw.get("port"),
            "desc": sw.get("desc"),
            "type": sw.get("type"),
            "state": sw.get("state"),
            "x": sw.get("x"),
            "y": sw.get("y"),
        })

    # ---------- SENSORES ----------
    for sn in root.findall(".//sensor"):
        sensors.append({
            "id": sn.get("id"),
            "addr": sn.get("addr"),
            "port": sn.get("port"),
            "desc": sn.get("desc"),
            "type": sn.get("type"),
        })

    # ---------- TRACKS (elementos gráficos de via) ----------
    for trk in root.findall(".//track"):
        tracks.append({
            "id": trk.get("id"),
            "type": trk.get("type"),
            "blockid": trk.get("blockid"),
            "x": trk.get("x"),
            "y": trk.get("y"),
            "z": trk.get("z"),
            "angle": trk.get("angle"),
        })

    plan: Dict[str, Any] = {
        "blocks": blocks,
        "locos": locos,
        "switches": switches,
        "sensors": sensors,
        "tracks": tracks,
    }

    print(
        f"[rocrail_plan] Resumo: "
        f"{len(blocks)} blocos, "
        f"{len(locos)} locos, "
        f"{len(switches)} switches, "
        f"{len(sensors)} sensores, "
        f"{len(tracks)} tracks"
    )

    return plan
