import socket
import threading
import time
from typing import Optional, Dict, Any, List


class CS3Client:
    """
    Cliente simples para Marklin CS3, inspirado no modelo do BTrain (mas em Python).

    NOTA: Este é um esqueleto.
    A CS3 fala CAN sobre TCP/UDP segundo o protocolo CS2/CS3.
    Aqui preparamos a conexão e alguns "hooks" para enviar/receber mensagens.
    """

    def __init__(self,
                 host: str = "192.168.59.36",  # IP da tua CS3
                 port: int = 15731,           # porta típica do protocolo CS2/CS3
                 auto_connect: bool = True):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.lock = threading.Lock()
        self.receiver_thread: Optional[threading.Thread] = None
        self.running = False

        # Estado básico em memória
        self.last_error: Optional[str] = None
        self.last_connect_time: Optional[float] = None
        self.locos: Dict[str, Dict[str, Any]] = {}
        self.turnouts: Dict[str, Dict[str, Any]] = {}

        if auto_connect:
            try:
                self.connect()
            except Exception as e:
                self.last_error = str(e)
                print("[CS3] Erro ao ligar na inicialização:", e)

    # -----------------------
    # LIGAÇÃO BÁSICA
    # -----------------------

    def connect(self):
        """Liga à CS3 via TCP."""
        if self.sock is not None:
            return

        print(f"[CS3] A ligar a {self.host}:{self.port} ...")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((self.host, self.port))
        s.settimeout(None)

        self.sock = s
        self.running = True
        self.last_connect_time = time.time()

        self.receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
        self.receiver_thread.start()

        print("[CS3] Ligação estabelecida.")

        # Aqui, no protocolo real, deveríamos enviar mensagens de "hello"/"login"
        # para registar o cliente. Esse detalhe depende da especificação CS2/CS3.

    def disconnect(self):
        """Desliga da CS3."""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.sock = None
        print("[CS3] Ligação terminada.")

    def _receiver_loop(self):
        """Loop para ler dados da CS3."""
        if self.sock is None:
            return

        s = self.sock
        try:
            while self.running:
                # Aqui depende muito do framing do protocolo CS2/CS3.
                # Normalmente tens frames de tamanho fixo ou com header.
                # Para um esqueleto, vamos ler em blocos e imprimir hex.
                data = s.recv(4096)
                if not data:
                    print("[CS3] Conexão fechada pelo servidor.")
                    self.running = False
                    break

                # Aqui chamaríamos um parser de frames CAN/CS2
                self._handle_raw_data(data)
        except Exception as e:
            self.last_error = str(e)
            print("[CS3] Erro no receiver_loop:", e)
        finally:
            self.sock = None
            self.running = False

    def _handle_raw_data(self, data: bytes):
        """
        Processa dados crus vindos da CS3.
        Aqui deves decodificar frames conforme o protocolo CS2/CS3.
        Por agora, apenas loga em hex.
        """
        # Só debug bruto por enquanto:
        hex_str = data.hex(" ")
        print(f"[CS3] RX: {hex_str[:120]}{'...' if len(hex_str) > 120 else ''}")

        # TODO:
        # - Parsear frames CAN
        # - Atualizar self.locos, self.turnouts, etc.

    def send_raw(self, payload: bytes):
        """Envia bytes crus para a CS3 (CAN frame / CS2 frame)."""
        with self.lock:
            if not self.sock:
                raise RuntimeError("CS3 não ligada")
            self.sock.sendall(payload)
            print("[CS3] TX:", payload.hex(" "))

    # -----------------------
    # OPERAÇÕES DE ALTO NÍVEL
    # -----------------------

    def request_loco_list(self):
        """
        Pedir à CS3 a lista de locomotivas.
        No protocolo real CS2/CS3, isto corresponde a enviar um frame específico.
        TODO: Implementar com base na especificação.
        """
        print("[CS3] request_loco_list() chamado (TODO)")

    def request_turnout_list(self):
        """
        Pedir à CS3 a lista de agulhas / acessórios.
        TODO: Implementar com base na especificação CS2/CS3.
        """
        print("[CS3] request_turnout_list() chamado (TODO)")

    def set_turnout(self, turnout_id: str, position: str):
        """
        Mudar uma agulha na CS3.
        position: "straight" ou "turnout" (ou equivalente CS3).
        Aqui precisas mapear turnout_id -> address/port e construir o frame CAN.
        """
        print(f"[CS3] set_turnout({turnout_id}, {position}) (TODO: enviar comando real)")

    def get_status(self) -> Dict[str, Any]:
        """Resumo de estado para API Flask."""
        return {
            "connected": self.sock is not None and self.running,
            "host": self.host,
            "port": self.port,
            "last_error": self.last_error,
            "last_connect_time": self.last_connect_time,
            "locos_count": len(self.locos),
            "turnouts_count": len(self.turnouts),
        }


# Instância global
cs3 = CS3Client(auto_connect=False)


def get_cs3():
    """Helper para obter o cliente (e ligar se ainda não estiver ligado)."""
    global cs3
    if cs3.sock is None or not cs3.running:
        try:
            cs3.connect()
        except Exception as e:
            cs3.last_error = str(e)
            print("[CS3] Erro ao ligar no get_cs3():", e)
    return cs3
