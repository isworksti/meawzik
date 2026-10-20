import tkinter as tk
import customtkinter as ctk
import keyboard
from player_core import MeawZikCore

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class MeawZikApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Meaw-Zik - Player Minimalista")
        self.geometry("600x450")
        self.resizable(False, False)

        self.core = MeawZikCore()

        # --- INTERFACE ---
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=20, pady=15)

        self.url_entry = ctk.CTkEntry(self.top_frame, placeholder_text="Cole o link ou digite o nome de uma música/artista/playlist...", width=430)
        self.url_entry.pack(side="left", padx=(0, 10))
        self.url_entry.bind("<Return>", lambda e: self.buscar_ou_carregar())

        self.load_btn = ctk.CTkButton(self.top_frame, text="Buscar / Carregar", width=120, command=self.buscar_ou_carregar)
        self.load_btn.pack(side="right")

        self.list_frame = ctk.CTkFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        mode = ctk.get_appearance_mode()
        self.playlist_box = tk.Listbox(
            self.list_frame, 
            bg="#2b2b2b" if mode == "Dark" else "#f0f0f0",
            fg="white" if mode == "Dark" else "black",
            selectbackground="#1f6aa5", borderwidth=0, highlightthickness=0, font=("Arial", 10)
        )
        self.playlist_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.playlist_box.bind('<Double-1>', self.ao_clicar_duplo)

        self.status_label = ctk.CTkLabel(self, text="Status: Pronto", font=("Arial", 11), text_color="gray")
        self.status_label.pack(padx=20, anchor="w")

        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.pack(fill="x", padx=20, pady=(5, 15))

        ctk.CTkButton(self.control_frame, text="⏮ Anterior", width=100, command=self.musica_anterior).pack(side="left")
        self.play_pause_btn = ctk.CTkButton(self.control_frame, text="▶ Play", width=120, command=self.alternar_play_pause)
        self.play_pause_btn.pack(side="left", padx=10)
        ctk.CTkButton(self.control_frame, text="Próxima ⏭", width=100, command=self.proxima_musica).pack(side="left")
        ctk.CTkButton(self.control_frame, text="⏹ Parar", width=100, fg_color="#b33939", hover_color="#8b2626", command=self.parar_musica).pack(side="right")

        self.configurar_teclas()
        self.monitorar_reproducao()

    def configurar_teclas(self):
        try:
            keyboard.add_hotkey('play/pause media', lambda: self.after(0, self.alternar_play_pause))
            keyboard.add_hotkey('next track', lambda: self.after(0, self.proxima_musica))
            keyboard.add_hotkey('previous track', lambda: self.after(0, self.musica_anterior))
        except Exception as e:
            print(f"[!] Atalhos globais indisponíveis: {e}")

    def atualizar_status(self, texto):
        self.after(0, lambda: self.status_label.configure(text=texto))

    def buscar_ou_carregar(self, alvo=None):
        termo = alvo or self.url_entry.get().strip()
        if not termo:
            return
        
        msg = "Analisando link..." if termo.startswith("http") else f"Pesquisando por '{termo}'..."
        self.atualizar_status(f"Status: {msg}")
        self.load_btn.configure(state="disabled")
        
        self.core.carregar_midia(termo, self.sucesso_carga, self.erro_carga)

    def sucesso_carga(self, nova_fila):
        def ui_callback():
            self.playlist_box.delete(0, tk.END)
            for i, f in enumerate(nova_fila):
                self.playlist_box.insert(tk.END, f"{i+1}. {f['title']}")
            
            txt = f"Status: Pronto ({len(nova_fila)} itens válidos)" if nova_fila else "Status: Nenhum resultado encontrado."
            self.atualizar_status(txt)
            self.load_btn.configure(state="normal")
        self.after(0, ui_callback)

    def erro_carga(self, msg):
        self.atualizar_status(f"Status: Erro ao carregar ({msg})")
        self.after(0, lambda: self.load_btn.configure(state="normal"))

    def tocar(self, indice):
        if 0 <= indice < len(self.core.fila):
            self.atualizar_status("Status: Obtendo áudio...")
            self.core.tocar_faixa(indice, self.sucesso_streaming, self.erro_streaming)

    def sucesso_streaming(self, titulo, indice):
        def ui_callback():
            self.atualizar_status(f"Tocando: {titulo}")
            self.play_pause_btn.configure(text="⏸ Pausar")
            self.playlist_box.selection_clear(0, tk.END)
            self.playlist_box.selection_set(indice)
            self.playlist_box.see(indice)
        self.after(0, ui_callback)

    def erro_streaming(self, _):
        self.atualizar_status("Status: Vídeo indisponível, pulando...")
        self.after(1000, self.proxima_musica)

    def ao_clicar_duplo(self, event):
        sel = self.playlist_box.curselection()
        if not sel:
            return
        
        faixa = self.core.fila[sel[0]]
        if "list=" in faixa['url'] or "playlist" in faixa['url']:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, faixa['url'])
            self.buscar_ou_carregar(faixa['url'])
        else:
            self.tocar(sel[0])

    def alternar_play_pause(self):
        if not self.core.fila:
            return
        
        tocando = self.core.alternar_play_pause()
        if tocando:
            self.play_pause_btn.configure(text="⏸ Pausar")
            self.atualizar_status("Status: Reproduzindo")
        else:
            if self.core.indice_atual == -1:
                self.tocar(0)
            else:
                self.play_pause_btn.configure(text="▶ Play")
                self.atualizar_status("Status: Pausado")

    def proxima_musica(self):
        if self.core.fila and self.core.indice_atual < len(self.core.fila) - 1:
            self.tocar(self.core.indice_atual + 1)

    def musica_anterior(self):
        if self.core.fila and self.core.indice_atual > 0:
            self.tocar(self.core.indice_atual - 1)

    def parar_musica(self):
        self.core.parar()
        self.play_pause_btn.configure(text="▶ Play")
        self.atualizar_status("Status: Parado")

    def monitorar_reproducao(self):
        if self.core.verificar_fim_musica():
            if self.core.indice_atual < len(self.core.fila) - 1:
                self.proxima_musica()
            else:
                self.core.is_playing_state = False
                self.play_pause_btn.configure(text="▶ Play")
                self.atualizar_status("Status: Fila finalizada")
        self.after(1000, self.monitorar_reproducao)

if __name__ == "__main__":
    app = MeawZikApp()
    app.mainloop()