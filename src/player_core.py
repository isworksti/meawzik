import threading
import yt_dlp
import vlc

class MeawZikCore:
    def __init__(self):
        self.vlc_instance = vlc.Instance('--no-video')
        self.player = self.vlc_instance.media_player_new()
        
        self.fila = []
        self.indice_atual = -1
        self.is_playing_state = False

    def carregar_midia(self, termo, callback_sucesso, callback_erro):
        """Executa a busca ou extração de link em background usando Thread"""
        threading.Thread(target=self._executar_carregamento, args=(termo, callback_sucesso, callback_erro), daemon=True).start()

    def _executar_carregamento(self, alvo, callback_sucesso, callback_erro):
        if alvo.startswith("http://") or alvo.startswith("https://"):
            url_alvo = alvo
        else:
            url_alvo = f"ytsearch10:{alvo}"

        ydl_opts = {
            'extract_flat': True,
            'ignoreerrors': True,
            'quiet': True,
            'no_warnings': True
        }

        try:
            nova_fila = []
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url_alvo, download=False)

                if 'entries' in info:
                    for entry in info['entries']:
                        if not entry:
                            continue
                        
                        titulo_verif = entry.get('title', '')
                        if titulo_verif in ["[Private video]", "[Deleted video]", "Private video", "Deleted video"]:
                            continue

                        e_url = entry.get('url')
                        e_title = entry.get('title', 'Desconhecido')
                        
                        if not e_url and entry.get('id'):
                            e_id = entry.get('id')
                            if entry.get('_type') == 'playlist' or str(e_id).startswith('PL'):
                                e_url = f"https://www.youtube.com/playlist?list={e_id}"
                            else:
                                e_url = f"https://www.youtube.com/watch?v={e_id}"
                        
                        if e_url:
                            is_playlist = 'list=' in e_url or entry.get('_type') == 'playlist'
                            prefixo = "[Playlist] " if is_playlist and 'ytsearch' in url_alvo else ""
                            
                            count = entry.get('playlist_count') or entry.get('n_entries')
                            sufixo = f" ({count} itens)" if count and count > 0 else ""
                            
                            titulo_completo = f"{prefixo}{e_title}{sufixo}"
                            max_len = 65
                            titulo_exibicao = titulo_completo[:max_len] + "..." if len(titulo_completo) > max_len else titulo_completo

                            nova_fila.append({
                                'title': titulo_exibicao,
                                'url': e_url
                            })
                else:
                    e_title = info.get('title', 'Desconhecido')
                    nova_fila.append({
                        'title': e_title,
                        'url': url_alvo
                    })

            self.fila = nova_fila
            callback_sucesso(self.fila)
                
        except Exception as e:
            callback_erro(str(e))

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
        self.player.stop()
        self.is_playing_state = False

    def verificar_fim_musica(self):
        if self.is_playing_state:
            if self.player.get_state() == vlc.State.Ended:
                return True
        return False