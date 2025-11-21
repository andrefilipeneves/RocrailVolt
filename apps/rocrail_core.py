import socket
import threading
import time

# Ajusta estes valores para o teu Rocrail
ROCRAIL_HOST = "localhost"   # ou IP do PC onde corre o Rocrail
ROCRAIL_PORT = 8051          # porta de serviço configurada no Rocrail
LOCO_DEFAULT = "ICE1"        # muda para um ID de loco que exista no Rocrail


class RocrailClient:
    def __init__(self, host=ROCRAIL_HOST, port=ROCRAIL_PORT):
        self.host = host
        self.port = port
        self.sock = None
        self.lock = threading.Lock()
        self._connect_thread = threading.Thread(target=self._ensure_connected, daemon=True)
        self._connect_thread.start()

    def _ensure_connected(self):
        """Tenta manter a ligação TCP ao Rocrail sempre aberta."""
        while True:
            if self.sock is None:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect((self.host, self.port))
                    self.sock = s
                    print(f"[Rocrail] Ligado a {self.host}:{self.port}")
                except Exception as e:
                    print(f"[Rocrail] Erro a ligar: {e}, a tentar de novo em 3s...")
                    self.sock = None
                    time.sleep(3)
            time.sleep(1)

    def send_xml(self, xml_str: str):
        """Envia comando XML simples para o Rocrail (terminado com newline)."""
        xml_str = xml_str.strip() + "\n"
        with self.lock:
            if self.sock is None:
                print("[Rocrail] Sem ligação, comando descartado:", xml_str.strip())
                return
            try:
                print("[Rocrail] ?", xml_str.strip())
                self.sock.sendall(xml_str.encode("utf-8"))
            except Exception as e:
                print("[Rocrail] Erro ao enviar:", e)
                self.sock = None  # força reconexão

    def set_switch(self, switch_id: str, cmd: str = "straight"):
        """
        Controla uma agulha (switch) do Rocrail.

        cmd típico:
          - "straight"
          - "turnout"

        Exemplo XML:
          <sw id="W1" cmd="straight"/>
        """
        cmd = cmd.lower()
        if cmd not in ("straight", "turnout"):
            print(f"[Rocrail] Comando de switch inválido: {cmd}")
            return

        xml = f'<sw id="{switch_id}" cmd="{cmd}"/>'
        self.send_xml(xml)

    def toggle_switch(self, switch_id: str):
        """
        Versão simples de toggle: manda sempre 'turnout'.
        (Podemos melhorar depois com leitura de estado real).
        """
        self.set_switch(switch_id, "turnout")


    # Helpers de alto nível
    def stop_loco(self, loco_id=LOCO_DEFAULT):
        self.send_xml(f'<lc id="{loco_id}" cmd="stop"/>')

    def set_speed(self, loco_id=LOCO_DEFAULT, speed=40):
        # speed em percentagem (0-100)
        self.send_xml(f'<lc id="{loco_id}" V="{speed}"/>')

    def go_loco(self, loco_id=LOCO_DEFAULT, speed=40):
        self.set_speed(loco_id, speed)

    def set_direction(self, loco_id: str = LOCO_DEFAULT, forward: bool = True):
        """
        Define a direção da loco.
        forward=True -> frente ; False -> marcha-atrás.
        """
        dir_str = "true" if forward else "false"
        # Rocrail entende 'dir="true/false"' em <lc>
        self.send_xml(f'<lc id="{loco_id}" dir="{dir_str}"/>')

    def set_function(self, loco_id: str, fn_no: int, state: bool = True):
        """
        Liga/desliga função F0, F1, F2...
        Implementação típica: atributo f0="true/false", f1="true/false", etc.
        """
        attr_name = f"f{fn_no}"
        val = "true" if state else "false"
        self.send_xml(f'<lc id="{loco_id}" {attr_name}="{val}"/>')


# Instância global para usar nas routes
rocrail = RocrailClient()
