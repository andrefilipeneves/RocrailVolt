from typing import Optional, Dict, Any
import time

try:
    import serial  # backend futuro (Arduino, etc.)
except ImportError:
    serial = None


class RCCarBackendBase:
    """
    Classe base: backend que fala com o hardware.
    Podemos ter:
      - DummyBackend (não envia nada, só loga)
      - SerialBackend (envia comandos num COM para Arduino, p.ex.)
    """

    def set_command(self, steering: float, throttle: float):
        raise NotImplementedError()

    def stop(self):
        self.set_command(0.0, 0.0)

    def get_status(self) -> Dict[str, Any]:
        return {}


class DummyBackend(RCCarBackendBase):
    def set_command(self, steering: float, throttle: float):
        print(f"[RC-DUMMY] steering={steering:.2f} throttle={throttle:.2f}")


class SerialBackend(RCCarBackendBase):
    """
    Exemplo de backend via porta série (para Arduino).
    Protocolo sugerido (por exemplo):
      "S:<steering_float>;T:<throttle_float>\n"
    O Arduino lê isto e converte para PWM no servo/ESC.
    """

    def __init__(self, port: str, baudrate: int = 115200):
        if serial is None:
            raise RuntimeError("pyserial não instalado. Instala com: pip install pyserial")

        self.port_name = port
        self.baudrate = baudrate
        self.ser = serial.Serial(port, baudrate, timeout=0.1)
        time.sleep(2.0)  # tempo para Arduino resetar

    def set_command(self, steering: float, throttle: float):
        # clamp
        s = max(-1.0, min(1.0, steering))
        t = max(-1.0, min(1.0, throttle))
        msg = f"S:{s:.2f};T:{t:.2f}\n"
        self.ser.write(msg.encode("ascii"))
        print("[RC-SERIAL] TX:", msg.strip())

    def get_status(self) -> Dict[str, Any]:
        return {
            "port": self.port_name,
            "baudrate": self.baudrate,
            "is_open": self.ser.is_open,
        }


class RCCarController:
    """
    Controlador de alto nível do RC car.
    Converte comandos normalizados [-1,1] em calls ao backend.
    Também guarda estado de autopilot/manual.
    """

    def __init__(self, backend: RCCarBackendBase):
        self.backend = backend
        self.autopilot_enabled = False
        self.last_command = {"steering": 0.0, "throttle": 0.0}
        self.last_update = None

    def set_manual_command(self, steering: float, throttle: float):
        """
        Comando manual. steering, throttle ? [-1, 1].
        """
        self.autopilot_enabled = False
        self._apply_command(steering, throttle)

    def set_autopilot_command(self, steering: float, throttle: float):
        """
        Comando vindo da IA (YOLO / lane follow).
        Só é aplicado se autopilot_enabled = True.
        """
        if not self.autopilot_enabled:
            return
        self._apply_command(steering, throttle)

    def _apply_command(self, steering: float, throttle: float):
        s = max(-1.0, min(1.0, steering))
        t = max(-1.0, min(1.0, throttle))
        self.backend.set_command(s, t)
        self.last_command = {"steering": s, "throttle": t}
        self.last_update = time.time()

    def enable_autopilot(self, enabled: bool):
        self.autopilot_enabled = bool(enabled)
        if not enabled:
            # quando desligamos autopilot, não mexemos automaticamente nos comandos
            print("[RC] Autopilot OFF")
        else:
            print("[RC] Autopilot ON")

    def emergency_stop(self):
        self.autopilot_enabled = False
        self.backend.stop()
        self.last_command = {"steering": 0.0, "throttle": 0.0}
        self.last_update = time.time()

    def get_status(self) -> Dict[str, Any]:
        return {
            "autopilot": self.autopilot_enabled,
            "last_command": self.last_command,
            "last_update": self.last_update,
            "backend": self.backend.get_status(),
        }


# Instância global com Dummy por agora
_backend = DummyBackend()
rc_car = RCCarController(_backend)


def set_serial_backend(port: str, baudrate: int = 115200):
    """
    Quando tiveres o Arduino ligado, podes trocar backend por SerialBackend.
    Exemplo (mais tarde):
      set_serial_backend("COM5")
    """
    global rc_car, _backend
    _backend = SerialBackend(port, baudrate=baudrate)
    rc_car = RCCarController(_backend)
    print("[RC] Backend trocado para SerialBackend:", port)
