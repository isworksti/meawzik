import uuid
import socket

class GroupModel:
    def __init__(self):
        self.sessao_nome = ""
        self.sessao_chave = ""
        self.ip_local = self.obter_ip_rede()
        self.is_hosting = False
        self.fila = []
        self.indice_atual = -1
        self.ultimos_resultados_pesquisa = []
        self.peer_conectado = False

    def obter_ip_rede(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def gerar_chave_sessao(self, nome):
        self.sessao_nome = nome.strip().upper()
        self.sessao_chave = str(uuid.uuid4())[:8].upper()
        return self.sessao_chave

    def adicionar_faixa_fila(self, faixa):
        if faixa not in self.fila:
            self.fila.append(faixa)
            return True
        return False