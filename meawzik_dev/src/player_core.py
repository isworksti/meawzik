import json
import os
import random
import vlc
import yt_dlp
from PyQt6.QtCore import QThread, pyqtSignal

# --- WORKER PARA PESQUISA (yt-dlp) ---
class SearchWorker(QThread):
    sucesso = pyqtSignal(list)
    erro = pyqtSignal(str)
    
    def __init__(self, termo):
        super().__init__()
        self.termo = termo

    def run(self):
        url_alvo = self.termo if self.termo.startswith(("http://", "https://")) else f"ytsearch10:{self.termo}"
        ydl_opts = {'extract_flat': True, 'ignoreerrors': True, 'quiet': True, 'no_warnings': True}
        try:
            resultados = []
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url_alvo, download=False)
                entries = info.get('entries', [info]) if 'entries' in info else [info]
                for entry in entries:
                    if entry:
                        e_url = entry.get('url')
                        e_title = entry.get('title', 'Desconhecido')
                        
                        if not e_url and entry.get('id'):
                            e_id = entry.get('id')
                            e_url = f"https://www.youtube.com/watch?v={e_id}"
                            
                        if e_url:
                            # --- CAPTURA DA DURAÇÃO NO SÍTIO CORRETO ---
                            duracao_segundos = entry.get('duration', 0)
                            resultados.append({
                                'title': e_title, 
                                'url': e_url,
                                'duration': duracao_segundos # Guarda a duração em segundos
                            })
                            
            self.sucesso.emit(resultados)
        except Exception as e:
            self.erro.emit(str(e))


# --- WORKER PARA EXTRAÇÃO DE ÁUDIO E STREAMING ---
class AudioWorker(QThread):
    sucesso = pyqtSignal(str, str, dict) # audio_url, titulo, http_headers
    erro = pyqtSignal(str)

    def __init__(self, video_url, titulo_fallback, cache_dict):
        super().__init__()
        self.video_url = video_url
        self.titulo_fallback = titulo_fallback
        self.cache_dict = cache_dict

    def run(self):
        try:
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best',  # Prefere m4a/aac que o VLC reproduz de forma estável
                'quiet': True, 
                'no_warnings': True,
                'http_headers': {
                    'User-Agent': user_agent
                }
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.video_url, download=False)
                audio_url = info['url']
                titulo = info.get('title', self.titulo_fallback)
                
                headers_info = {'user-agent': user_agent}
                self.sucesso.emit(audio_url, titulo, headers_info)
        except Exception as e:
            self.erro.emit(str(e))


# --- CLASSE PRINCIPAL DO CORE ---
class MeawZikCore:
    def __init__(self):
        # Otimizações de rede estáveis e compatíveis com o VLC
        vlc_args = [
            '--no-video', 
            '--network-caching=3000',      # Aumenta o cache de rede para 3 segundos
            '--live-caching=3000',
            '--demux=any'                  # Garante flexibilidade no demuxer
        ]
        self.vlc_instance = vlc.Instance(vlc_args)
        self.player = self.vlc_instance.media_player_new()
        
        self.resultados_pesquisa = []
        self.indice_atual = -1
        self.is_playing_state = False
        
        self.is_shuffle = False
        self.is_repeat = False
        self.cache_urls = {}

        self.playlists = []  # Lista de dicionários: [{'nome': 'Playlist (1)', 'faixas': [...]}]
        self.playlist_ativa_indice = 0
        
        # Carrega o histórico salvo em JSON e inicializa se estiver vazio
        self.carregar_playlists_json()
        self.inicializar_playlists_iniciais()

    def guardar_playlists_json(self):
        """Salva todas as playlists num ficheiro JSON local"""
        try:
            dados = {
                'playlist_ativa_indice': self.playlist_ativa_indice,
                'playlists': self.playlists
            }
            with open('playlists.json', 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Erro ao guardar playlists: {e}")

    def carregar_playlists_json(self):
        """Carrega as playlists do ficheiro JSON se ele existir"""
        if os.path.exists('playlists.json'):
            try:
                with open('playlists.json', 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    self.playlists = dados.get('playlists', [])
                    self.playlist_ativa_indice = dados.get('playlist_ativa_indice', 0)
            except Exception as e:
                print(f"Erro ao carregar playlists: {e}")

    def inicializar_playlists_iniciais(self):
        """Garante que ao abrir o programa exista pelo menos uma playlist padrão"""
        if not self.playlists:
            self.criar_nova_playlist()

    def criar_nova_playlist(self):
        """Cria uma nova playlist com o próximo número sequencial disponivel"""
        numero = len(self.playlists) + 1
        nome = f"Playlist ({numero})"
        nova_pl = {
            'nome': nome,
            'faixas': []
        }
        self.playlists.append(nova_pl)
        self.playlist_ativa_indice = len(self.playlists) - 1
        self.guardar_playlists_json()
        return nova_pl

    @property
    def fila(self):
        """Atalho retrocompatível para a fila da playlist atualmente ativa"""
        if not self.playlists:
            self.criar_nova_playlist()
        return self.playlists[self.playlist_ativa_indice]['faixas']

    @fila.setter
    def fila(self, nova_lista):
        if self.playlists:
            self.playlists[self.playlist_ativa_indice]['faixas'] = nova_lista
            self.guardar_playlists_json()

    def adicionar_a_fila(self, faixa):
        self.fila.append(faixa)
        self.guardar_playlists_json()
        return len(self.fila) - 1

    def remover_da_fila(self, indice):
        if 0 <= indice < len(self.fila):
            removida = self.fila.pop(indice)
            if indice == self.indice_atual:
                self.parar()
                self.indice_atual = -1
            elif indice < self.indice_atual:
                self.indice_atual -= 1
            self.guardar_playlists_json()
            return removida
        return None

    def parar(self):
        try:
            if self.player:
                self.player.stop()
            self.is_playing_state = False
        except Exception:
            pass

    def alternar_play_pause(self):
        if not self.fila:
            return False
        if self.player.is_playing():
            self.player.pause()
            self.is_playing_state = False
            return False
        else:
            self.player.play()
            self.is_playing_state = True
            return True

    def definir_volume(self, volume):
        if self.player:
            self.player.audio_set_volume(max(0, min(100, int(volume))))

    def get_tempo_atual(self):
        try: return self.player.get_time()
        except: return 0

    def get_duracao(self):
        try: return self.player.get_length()
        except: return 0

    def definir_posicao(self, posicao_ms):
        try: self.player.set_time(int(posicao_ms))
        except: pass

    def verificar_fim_musica(self):
        if self.is_playing_state and self.player.get_state() == vlc.State.Ended:
            return True
        return False

    def alternar_shuffle(self):
        self.is_shuffle = not self.is_shuffle
        return self.is_shuffle

    def alternar_repeat(self):
        self.is_repeat = not self.is_repeat
        return self.is_repeat

    def selecionar_playlist(self, indice):
        """Seleciona uma playlist existente pelo seu índice"""
        if 0 <= indice < len(self.playlists):
            self.playlist_ativa_indice = indice
            self.guardar_playlists_json()
            return True
        return False

    def obter_todas_playlists(self):
        """Retorna o resumo de todas as playlists criadas"""
        return [{'indice': i, 'nome': p['nome'], 'total_faixas': len(p['faixas'])} for i, p in enumerate(self.playlists)]