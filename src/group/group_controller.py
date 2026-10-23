import threading
import asyncio
import tkinter as tk
import customtkinter as ctk

from .group_model import GroupModel
from .group_view import GroupView
from network_core import MeawZikNetwork
from player_core import MeawZikCore

class MeawZikGroupWindow(GroupView):
    def __init__(self, parent):
        self.model = GroupModel()
        super().__init__(parent, self)
        
        self.player_core = MeawZikCore()
        self.network = MeawZikNetwork(port=50000)
        self.network.set_message_callback(self.ao_receber_mensagem_rede)
        self.network.set_peer_connected_callback(self.ao_conectar_peer)
        self.network.set_disconnected_callback(self.ao_host_desconectar)

        self.loop = None
        self.network_thread = None
        self.iniciar_monitor_reproducao()

    def copiar_ip(self):
        self.copiar_texto(self.model.ip_local)

    def copiar_chave(self):
        self.copiar_texto(self.model.sessao_chave)

    def copiar_texto(self, texto):
        if texto:
            self.clipboard_clear()
            self.clipboard_append(texto)
            self.status_label.configure(text=f"Status: '{texto}' copiado para a área de transferência!")

    def voltar_ao_menu_principal(self):
        if self.model.is_hosting:
            self.parar_sessao_host()
        self.voltar_ao_menu_inicial()
        self.destroy()
        self.parent.deiconify()

    def pedir_dados_hospedagem(self):
        dialog = ctk.CTkInputDialog(text="Digite o nome para a sua sessão em grupo:", title="Hospedar Sessão")
        nome = dialog.get_input()
        
        if nome:
            chave = self.model.gerar_chave_sessao(nome)
            self.network.set_expected_key(chave)
            
            # Exibe apenas o nome em maiúsculas, sem a indicação "Sessão:"
            self.label_info_nome.configure(text=f"🏠 {self.model.sessao_nome}")
            self.label_ip_val.configure(text=f"IP: {self.model.ip_local}")
            self.label_key_val.configure(text=f"Chave: {chave}")

            self.ativar_interface_sessao()
            self.hospedar_sessao()

    def hospedar_sessao(self):
        if self.network_thread and self.network_thread.is_alive():
            return

        def run_server():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            try:
                self.loop.run_until_complete(self.network.iniciar_servidor())
            except Exception:
                pass

        self.model.is_hosting = True
        self.network_thread = threading.Thread(target=run_server, daemon=True)
        self.network_thread.start()
        
        self.atualizar_lista_participantes(is_host=True)
        self.status_label.configure(text=f"Status: Hospedando '{self.model.sessao_nome}'. Aguardando peer...")

    def parar_sessao_host(self):
        if self.model.is_hosting:
            self.model.is_hosting = False
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self.network.enviar_comando("HOST_DISCONNECTED"), self.loop)
                self.loop.call_soon_threadsafe(self.loop.stop)
            
            self.network.fechar_todas_conexoes()
            self.status_label.configure(text="Status: Sessão encerrada.")

    def entrar_sessao(self):
        ip_host = self.ip_entry.get().strip()
        chave_digitada = self.key_entry.get().strip()

        if not ip_host or not chave_digitada:
            self.status_label.configure(text="Status: Insira o IP e a Chave de Acesso.")
            return

        def run_client():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            try:
                sucesso = self.loop.run_until_complete(self.network.conectar_a_peer(ip_host, 50000, chave_digitada))
                if sucesso:
                    self.after(0, lambda: self.status_label.configure(text="Status: Conectado com sucesso ao anfitrião!"))
                    self.after(0, self.ativar_interface_sessao)
                    # Esconde temporariamente as credenciais de host para o convidado
                    self.after(0, lambda: self.label_info_nome.configure(text=f"🟢 Conectado ao Host: {ip_host}"))
                    self.after(0, lambda: self.detalhes_compartilhar.pack_forget())
                    self.after(0, lambda: self.atualizar_lista_participantes(is_host=False))
                    self.loop.run_forever()
                else:
                    self.after(0, lambda: self.status_label.configure(text="Status: Falha na conexão (Chave inválida ou Host offline)."))
            except Exception as e:
                print(f"[!] Erro na thread do cliente: {e}")
                self.after(0, lambda: self.status_label.configure(text="Status: Erro de conexão."))

        self.network_thread = threading.Thread(target=run_client, daemon=True)
        self.network_thread.start()
        self.status_label.configure(text=f"Status: A autenticar com {ip_host}...")

    def ao_conectar_peer(self, peer_addr):
        self.after(0, lambda: self.status_label.configure(text=f"Status: Peer {peer_addr[0]} conectado com sucesso!"))
        self.after(0, lambda: self.atualizar_lista_participantes(is_host=True, peer_conectado=True))
        
        if self.loop and self.network_thread and self.network_thread.is_alive():
            payload_estado = {
                "fila": self.model.fila,
                "indice_atual": self.model.indice_atual,
                "is_playing": self.player_core.is_playing_state
            }
            asyncio.run_coroutine_threadsafe(
                self.network.enviar_comando("SYNC_STATE", payload_estado),
                self.loop
            )

    def ao_host_desconectar(self):
        self.after(0, lambda: self.status_label.configure(text="Status: O anfitrião encerrou a sessão."))
        self.after(0, self.voltar_ao_menu_inicial)

    def atualizar_lista_participantes(self, is_host=True, peer_conectado=False):
        def atualizar():
            self.participants_box.delete(0, tk.END)
            if is_host:
                self.participants_box.insert(tk.END, "👑 Host (Você)")
                if peer_conectado:
                    self.participants_box.insert(tk.END, "🎧 Convidado")
            else:
                self.participants_box.insert(tk.END, "👑 Host")
                self.participants_box.insert(tk.END, "🎧 Convidado (Você)")
        self.after(0, atualizar)

    def pesquisar_musica(self):
        termo = self.search_entry.get().strip()
        if termo:
            def ao_sucesso(fila_resultados):
                def atualizar_ui():
                    self.search_box.delete(0, tk.END)
                    self.model.ultimos_resultados_pesquisa = fila_resultados
                    for item in fila_resultados:
                        titulo = item.get('title', 'Desconhecido')
                        self.search_box.insert(tk.END, f"🔍 {titulo}")
                self.after(0, atualizar_ui)

            def ao_erro(erro_msg):
                self.after(0, lambda: self.status_label.configure(text=f"Status: Erro na busca ({erro_msg})"))

            self.status_label.configure(text=f"Status: Pesquisando por '{termo}'...")
            self.player_core.carregar_midia(termo, ao_sucesso, ao_erro)
            self.search_entry.delete(0, tk.END)

    def ao_selecionar_pesquisa(self, event):
        try:
            sel = self.search_box.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx < len(self.model.ultimos_resultados_pesquisa):
                faixa = self.model.ultimos_resultados_pesquisa[idx]
                
                self.adicionar_faixa_na_fila(faixa, tocar_se_necessario=True)
                
                if self.loop and self.network_thread and self.network_thread.is_alive():
                    asyncio.run_coroutine_threadsafe(
                        self.network.enviar_comando("ADD_QUEUE", {"faixa": faixa}),
                        self.loop
                    )
        except Exception as e:
            print(f"[!] Erro ao selecionar da pesquisa: {e}")

    def adicionar_faixa_na_fila(self, faixa, tocar_se_necessario=True):
        def atualizar():
            if self.model.adicionar_faixa_fila(faixa):
                self.playlist_box.insert(tk.END, f"🎵 {faixa.get('title')}")
                if len(self.model.fila) == 1 and tocar_se_necessario:
                    self.reproduzir_indice_fila(0)
        self.after(0, atualizar)

    def ao_selecionar_fila(self, event):
        try:
            sel = self.playlist_box.curselection()
            if not sel:
                return
            idx = sel[0]
            
            if self.loop and self.network_thread and self.network_thread.is_alive():
                asyncio.run_coroutine_threadsafe(
                    self.network.enviar_comando("PLAY_INDEX", {"index": idx}),
                    self.loop
                )
            self.reproduzir_indice_fila(idx)
        except Exception as e:
            print(f"[!] Erro ao selecionar item da fila: {e}")

    def reproduzir_indice_fila(self, idx):
        def executar():
            if 0 <= idx < len(self.model.fila):
                self.model.indice_atual = idx
                faixa = self.model.fila[idx]
                self.player_core.tocar_faixa(
                    idx,
                    lambda t, i: self.after(0, lambda: self.play_pause_btn.configure(text="⏸ Pausar")),
                    lambda e: print(f"[!] Erro ao tocar áudio no player: {e}")
                )
                self.status_label.configure(text=f"Status: Tocando '{faixa.get('title')}'")
        self.after(0, executar)

    def acao_play_pause(self):
        if not self.model.fila:
            return
            
        tocando = self.player_core.alternar_play_pause()
        estado = "play" if tocando else "pause"
        
        if self.loop and self.network_thread and self.network_thread.is_alive():
            # Envia o estado de play/pause
            asyncio.run_coroutine_threadsafe(
                self.network.enviar_comando("TOGGLE_PLAY", {"state": estado}), 
                self.loop
            )
            # Se deu play e há um índice válido, garante que o convidado também reproduz esse índice
            if tocando and self.model.indice_atual != -1:
                asyncio.run_coroutine_threadsafe(
                    self.network.enviar_comando("PLAY_INDEX", {"index": self.model.indice_atual}),
                    self.loop
                )

        self.play_pause_btn.configure(text="⏸ Pausar" if tocando else "▶ Play")

    def acao_proximo(self):
        if not self.model.fila:
            return
        novo_idx = self.model.indice_atual + 1
        if novo_idx < len(self.model.fila):
            if self.loop and self.network_thread and self.network_thread.is_alive():
                asyncio.run_coroutine_threadsafe(
                    self.network.enviar_comando("PLAY_INDEX", {"index": novo_idx}),
                    self.loop
                )
            self.reproduzir_indice_fila(novo_idx)

    def acao_anterior(self):
        if not self.model.fila:
            return
        novo_idx = self.model.indice_atual - 1
        if novo_idx >= 0:
            if self.loop and self.network_thread and self.network_thread.is_alive():
                asyncio.run_coroutine_threadsafe(
                    self.network.enviar_comando("PLAY_INDEX", {"index": novo_idx}),
                    self.loop
                )
            self.reproduzir_indice_fila(novo_idx)

    def iniciar_monitor_reproducao(self):
        def verificar():
            try:
                if self.player_core.verificar_fim_musica():
                    proximo_idx = self.model.indice_atual + 1
                    if proximo_idx < len(self.model.fila):
                        self.reproduzir_indice_fila(proximo_idx)
                    else:
                        self.play_pause_btn.configure(text="▶ Play")
            except Exception:
                pass
            self.after(1000, verificar)

        self.after(1000, verificar)

    def ao_receber_mensagem_rede(self, mensagem):
        print(f"[Rede] Comando recebido na UI: {mensagem}")
        acao = mensagem.get("action")
        payload = mensagem.get("payload", {})
        
        if acao == "TOGGLE_PLAY":
            estado = payload.get("state")
            def aplicar():
                if not self.model.fila:
                    return
                if estado == "play":
                    self.player_core.player.play()
                    self.player_core.is_playing_state = True
                    self.play_pause_btn.configure(text="⏸ Pausar")
                elif estado == "pause":
                    self.player_core.player.pause()
                    self.player_core.is_playing_state = False
                    self.play_pause_btn.configure(text="▶ Play")
            self.after(0, aplicar)

        elif acao == "ADD_QUEUE":
            faixa = payload.get("faixa")
            if faixa:
                self.adicionar_faixa_na_fila(faixa, tocar_se_necessario=True)

        elif acao == "PLAY_INDEX":
            idx = payload.get("index")
            if idx is not None:
                self.reproduzir_indice_fila(idx)

        elif acao == "SYNC_STATE":
            fila_recebida = payload.get("fila", [])
            indice_recebido = payload.get("indice_atual", -1)
            is_playing = payload.get("is_playing", False)
            
            def aplicar_sync():
                self.model.fila = fila_recebida
                self.playlist_box.delete(0, tk.END)
                
                for faixa in self.model.fila:
                    self.playlist_box.insert(tk.END, f"🎵 {faixa.get('title')}")
                
                if 0 <= indice_recebido < len(self.model.fila):
                    self.model.indice_atual = indice_recebido
                    
                    # Seleciona visualmente na Listbox do convidado
                    self.playlist_box.selection_clear(0, tk.END)
                    self.playlist_box.selection_set(indice_recebido)
                    self.playlist_box.activate(indice_recebido)
                    
                    # Se o host estiver a tocar, reproduz o áudio no convidado
                    if is_playing:
                        self.reproduzir_indice_fila(indice_recebido)
                    else:
                        # Apenas carrega a mídia sem disparar o play automático se estivesse pausado
                        faixa = self.model.fila[indice_recebido]
                        self.status_label.configure(text=f"Status: Sincronizado ('{faixa.get('title')}')")
            
            self.after(0, aplicar_sync)