import threading
import random
import yt_dlp
import vlc

class MeawZikCore:
    def __init__(self):
        self.vlc_instance = vlc.Instance('--no-video')
        self.player = self.vlc_instance.media_player_new()
        
        self.resultados_pesquisa = []
        self.fila = []
        self.indice_atual = -1
        self.is_playing_state = False
        
        # Atributos de controlo devidamente inicializados no __init__
        self.is_shuffle = False
        self.is_repeat = False

    def pesquisar(self, termo, callback_sucesso, callback_erro):
        threading.Thread(target=self._executar_pesquisa, args=(termo, callback_sucesso, callback_erro), daemon=True).start()

    def _executar_pesquisa(self, alvo, callback_sucesso, callback_erro):
        url_alvo = alvo if alvo.startswith("http://") or alvo.startswith("https://") else f"ytsearch10:{alvo}"
        ydl_opts = {'extract_flat': True, 'ignoreerrors': True, 'quiet': True, 'no_warnings': True}

        try:
            resultados = []
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url_alvo, download=False)
                entries = info.get('entries', [info]) if 'entries' in info else [info]

                for entry in entries:
                    if not entry:
                        continue
                    e_url = entry.get('url')
                    e_title = entry.get('title', 'Desconhecido')
                    
                    if not e_url and entry.get('id'):
                        e_id = entry.get('id')
                        e_url = f"https://www.youtube.com/playlist?list={e_id}" if str(e_id).startswith('PL') else f"https://www.youtube.com/watch?v={e_id}"
                    
                    if e_url:
                        resultados.append({'title': e_title, 'url': e_url})

            self.resultados_pesquisa = resultados
            callback_sucesso(resultados)
        except Exception as e:
            callback_erro(str(e))

    def adicionar_a_fila(self, faixa):
        self.fila.append(faixa)
        return len(self.fila) - 1

    def tocar_faixa(self, indice, callback_tocando, callback_erro):
        if 0 <= indice < len(self.fila):
            self.indice_atual = indice
            faixa = self.fila[self.indice_atual]
            threading.Thread(target=self._executar_streaming, args=(faixa['url'], faixa['title'], callback_tocando, callback_erro), daemon=True).start()

    def _executar_streaming(self, video_url, titulo_fallback, callback_tocando, callback_erro):
        try:
            ydl_opts = {'format': 'bestaudio/best', 'quiet': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                audio_url = info['url']
                titulo = info.get('title', titulo_fallback)

            media = self.vlc_instance.media_new(audio_url)
            self.player.set_media(media)
            self.player.play()
            self.is_playing_state = True
            callback_tocando(titulo, self.indice_atual)
        except Exception as e:
            callback_erro(str(e))

    def proximo(self, callback_tocando, callback_erro):
        if not self.fila:
            return False

        if self.is_repeat and self.indice_atual >= len(self.fila) - 1:
            return self.tocar_faixa(self.indice_atual, callback_tocando, callback_erro)

        if self.is_shuffle and len(self.fila) > 1:
            novo_indice = self.indice_atual
            while novo_indice == self.indice_atual:
                novo_indice = random.randint(0, len(self.fila) - 1)
            return self.tocar_faixa(novo_indice, callback_tocando, callback_erro)

        if self.indice_atual + 1 < len(self.fila):
            return self.tocar_faixa(self.indice_atual + 1, callback_tocando, callback_erro)
        
        return False

    def anterior(self, callback_tocando, callback_erro):
        if self.fila and self.indice_atual - 1 >= 0:
            return self.tocar_faixa(self.indice_atual - 1, callback_tocando, callback_erro)
        return False

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

    def parar(self):
        """Interrompe a reprodução de áudio atual no VLC"""
        try:
            if hasattr(self, 'player') and self.player:
                self.player.stop()
            self.is_playing_state = False
        except Exception as e:
            print(f"[!] Erro ao parar o player: {e}")

    def get_tempo_atual(self):
        try: return self.player.get_time()
        except: return 0

    def get_duracao(self):
        try: return self.player.get_length()
        except: return 0

    def definir_posicao(self, posicao_ms):
        try: self.player.set_time(int(posicao_ms))
        except: pass

    def verificar_fim_musica_no_loop(self):
        self.atualizar_icone_play_pause(False)

    def definir_volume(self, volume):
        if self.player:
            vol_int = max(0, min(100, int(volume)))
            self.player.audio_set_volume(vol_int)

    def alternar_shuffle(self):
        self.is_shuffle = not self.is_shuffle
        return self.is_shuffle

    def alternar_repeat(self):
        self.is_repeat = not self.is_repeat
        return self.is_repeat