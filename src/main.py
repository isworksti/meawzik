import tkinter as tk
import customtkinter as ctk
import keyboard
from player_core import MeawZikCore

# Configuração inicial do tema do CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class MeawZikApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Meaw-Zik - Player Minimalista")
        self.geometry("600x450")
        self.resizable(False, False)

      
        self.iconbitmap("src/meawzik.ico")

        
        self.core = MeawZikCore()

        

        
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=20, pady=15)

        self.url_entry = ctk.CTkEntry(self.top_frame, placeholder_text="Cole o link ou digite o nome de uma música/artista/playlist...", width=430)
        self.url_entry.pack(side="left", padx=(0, 10))
        self.url_entry.bind("<Return>", lambda event: self.ao_clicar_buscar())

        self.load_btn = ctk.CTkButton(self.top_frame, text="Buscar / Carregar", width=120, command=self.ao_clicar_buscar)
        self.load_btn.pack(side="right")

        
        self.list_frame = ctk.CTkFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self.playlist_box = tk.Listbox(
            self.list_frame, 
            bg="#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0",
            fg="white" if ctk.get_appearance_mode() == "Dark" else "black",
            selectbackground="#1f6aa5",
            borderwidth=0,
            highlightthickness=0,
            font=("Arial", 10)
        )
        self.playlist_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.playlist_box.bind('<Double-1>', self.ao_clicar_musica_duplo)

    
        self.status_label = ctk.CTkLabel(self, text="Status: Pronto", font=("Arial", 11), text_color="gray")
        self.status_label.pack(padx=20, anchor="w")

        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.pack(fill="x", padx=20, pady=(5, 15))

        self.prev_btn = ctk.CTkButton(self.control_frame, text="⏮ Anterior", width=100, command=self.musica_anterior)
        self.prev_btn.pack(side="left")

        self.play_pause_btn = ctk.CTkButton(self.control_frame, text="▶ Play", width=120, command=self.alternar_play_pause)
        self.play_pause_btn.pack(side="left", padx=10)

        self.next_btn = ctk.CTkButton(self.control_frame, text="Próxima ⏭", width=100, command=self.proxima_musica)
        self.next_btn.pack(side="left")

        self.stop_btn = ctk.CTkButton(self.control_frame, text="⏹ Parar", width=100, fg_color="#b33939", hover_color="#8b2626", command=self.parar_musica)
        self.stop_btn.pack(side="right")

    
        self.configurar_teclas_midia()

        
        self.monitorar_reproducao()

    def configurar_teclas_midia(self):
        try:
            keyboard.add_hotkey('play/pause media', lambda: self.after(0, self.alternar_play_pause))
            keyboard.add_hotkey('next track', lambda: self.after(0, self.proxima_musica))
            keyboard.add_hotkey('previous track', lambda: self.after(0, self.musica_anterior))
        except Exception as e:
            print(f"[!] Aviso: Não foi possível registrar as teclas de mídia globais ({e})")

    def ao_clicar_buscar(self):
        termo = self.url_entry.get().strip()
        if not termo:
            return
        
        if termo.startswith("http://") or termo.startswith("https://"):
            self.status_label.configure(text="Status: Analisando link do YouTube...")
        else:
            self.status_label.configure(text=f"Status: Pesquisando por '{termo}'...")

        self.load_btn.configure(state="disabled")
        self.core.carregar_midia(termo, self.sucesso_carregamento, self.erro_carregamento)

    def sucesso_carregamento(self, nova_fila):
        self.after(0, lambda: self._atualizar_ui_pos_carga(nova_fila))

    def _atualizar_ui_pos_carga(self, nova_fila):
        self.playlist_box.delete(0, tk.END)
        for i, faixa in enumerate(nova_fila):
            self.playlist_box.insert(tk.END, f"{i+1}. {faixa['title']}")
        
        if nova_fila:
            self.status_label.configure(text=f"Status: Pronto ({len(nova_fila)} itens válidos)")
        else:
            self.status_label.configure(text="Status: Nenhum resultado encontrado.")
        
        self.load_btn.configure(state="normal")

    def erro_carregamento(self, erro_msg):
        self.after(0, lambda: self._tratar_erro_ui(erro_msg))

    def _tratar_erro_ui(self, erro_msg):
        self.status_label.configure(text=f"Status: Erro ao carregar ({erro_msg})")
        self.load_btn.configure(state="normal")

    def tocar_faixa_ui(self, indice):
        if 0 <= indice < len(self.core.fila):
            self.status_label.configure(text="Status: Obtendo áudio...")
            self.core.tocar_faixa(indice, self.sucesso_streaming, self.erro_streaming)

    def sucesso_streaming(self, titulo, indice):
        self.after(0, lambda: self.status_label.configure(text=f"Tocando: {titulo}"))
        self.after(0, lambda: self.play_pause_btn.configure(text="⏸ Pausar"))
        self.after(0, lambda: self.destacar_item_lista(indice))

    def erro_streaming(self, erro_msg):
        self.after(0, lambda: self.status_label.configure(text="Status: Vídeo indisponível, pulando..."))
        self.after(1000, self.proxima_musica)

    def destacar_item_lista(self, indice):
        self.playlist_box.selection_clear(0, tk.END)
        self.playlist_box.selection_set(indice)
        self.playlist_box.see(indice)

    def ao_clicar_musica_duplo(self, event):
        selecao = self.playlist_box.curselection()
        if not selecao:
            return
        
        indice = selecao[0]
        faixa = self.core.fila[indice]
        url = faixa['url']

        if "list=" in url or "playlist" in url:
            self.status_label.configure(text="Status: Carregando conteúdo da playlist...")
            self.load_btn.configure(state="disabled")
            
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url)
            
            self.core.carregar_midia(url, self.sucesso_carregamento, self.erro_carregamento)
        else:
            self.tocar_faixa_ui(indice)

    def alternar_play_pause(self):
        if not self.core.fila:
            return
        
        tocando = self.core.alternar_play_pause()
        if tocando:
            self.play_pause_btn.configure(text="⏸ Pausar")
            self.status_label.configure(text="Status: Reproduzindo")
        else:
            if self.core.indice_atual == -1 and self.core.fila:
                self.tocar_faixa_ui(0)
            else:
                self.play_pause_btn.configure(text="▶ Play")
                self.status_label.configure(text="Status: Pausado")

    def proxima_musica(self):
        if self.core.fila and self.core.indice_atual < len(self.core.fila) - 1:
            self.tocar_faixa_ui(self.core.indice_atual + 1)

    def musica_anterior(self):
        if self.core.fila and self.core.indice_atual > 0:
            self.tocar_faixa_ui(self.core.indice_atual - 1)

    def parar_musica(self):
        self.core.parar()
        self.play_pause_btn.configure(text="▶ Play")
        self.status_label.configure(text="Status: Parado")

    def monitorar_reproducao(self):
        if self.core.verificar_fim_musica():
            if self.core.indice_atual < len(self.core.fila) - 1:
                self.proxima_musica()
            else:
                self.core.is_playing_state = False
                self.play_pause_btn.configure(text="▶ Play")
                self.status_label.configure(text="Status: Fila finalizada")
        
        self.after(1000, self.monitorar_reproducao)

if __name__ == "__main__":
    app = MeawZikApp()
    app.mainloop()