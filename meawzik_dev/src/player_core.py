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
                            resultados.append({'title': e_title, 'url': e_url})
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
            '--network-caching=3000',     # Aumenta o cache de rede para 3 segundos
            '--live-caching=3000',
            '--demux=any'                 # Garante flexibilidade no demuxer
        ]
        self.vlc_instance = vlc.Instance(vlc_args)
        self.player = self.vlc_instance.media_player_new()
        
        self.resultados_pesquisa = []
        self.fila = []
        self.indice_atual = -1
        self.is_playing_state = False
        
        self.is_shuffle = False
        self.is_repeat = False
        self.cache_urls = {}

    def adicionar_a_fila(self, faixa):
        self.fila.append(faixa)
        return len(self.fila) - 1

    def remover_da_fila(self, indice):
        if 0 <= indice < len(self.fila):
            removida = self.fila.pop(indice)
            if indice == self.indice_atual:
                self.parar()
                self.indice_atual = -1
            elif indice < self.indice_atual:
                self.indice_atual -= 1
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