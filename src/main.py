import os
import sys
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

# Importamos a classe do player
from player_core import MeawZikCore

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def resource_path(relative_path):
    """ Obtém o caminho absoluto para os recursos no PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MeawZikPlayerWindow(ctk.CTkToplevel):
    """ Janela principal do Player (Modo Solo) """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Meaw-Zik - Sessão Solo")
        self.geometry("600x450")
        self.resizable(False, False)

        # Configurar ícone
        try:
            caminho_ico = resource_path("meawzik.ico")
            if os.path.exists(caminho_ico):
                img_pil = Image.open(caminho_ico)
                self.icone_app = ImageTk.PhotoImage(img_pil)
                self.iconphoto(True, self.icone_app)
        except Exception as e:
            print(f"[!] Erro ao carregar ícone: {e}")

        self.core = MeawZikCore()

        # --- LAYOUT DO PLAYER ---
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=20, pady=15)

        self.url_entry = ctk.CTkEntry(self.top_frame, placeholder_text="Cole o link ou digite o nome de uma música...", width=430)
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

        self.status_label = ctk.CTkLabel(self, text="Status: Pronto", font=("Arial", 11), text_color="gray")
        self.status_label.pack(padx=20, anchor="w")

        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.pack(fill="x", padx=20, pady=(5, 15))

        self.play_pause_btn = ctk.CTkButton(self.control_frame, text="▶ Play", width=120, command=self.alternar_play_pause)
        self.play_pause_btn.pack(side="left")

    def ao_clicar_buscar(self):
        termo = self.url_entry.get().strip()
        if not termo:
            return
        self.core.carregar_midia(termo, self.sucesso_carregamento, self.erro_carregamento)

    def sucesso_carregamento(self, nova_fila):
        self.after(0, lambda: self._atualizar_ui_pos_carga(nova_fila))

    def _atualizar_ui_pos_carga(self, nova_fila):
        self.playlist_box.delete(0, tk.END)
        for i, faixa in enumerate(nova_fila):
            self.playlist_box.insert(tk.END, f"{i+1}. {faixa['title']}")

    def erro_carregamento(self, erro_msg):
        pass

    def alternar_play_pause(self):
        if not self.core.fila:
            return
        tocando = self.core.alternar_play_pause()
        if tocando:
            self.play_pause_btn.configure(text="⏸ Pausar")
        else:
            self.play_pause_btn.configure(text="▶ Play")


class MeawZikHome(ctk.CTk):
    """ Ecrã Inicial / Menu Principal """
    def __init__(self):
        super().__init__()

        self.title("Meaw-Zik - Início")
        self.geometry("400x300")
        self.resizable(False, False)

        try:
            caminho_ico = resource_path("meawzik.ico")
            if os.path.exists(caminho_ico):
                img_pil = Image.open(caminho_ico)
                self.icone_app = ImageTk.PhotoImage(img_pil)
                self.iconphoto(True, self.icone_app)
        except Exception as e:
            print(f"[!] Erro ao carregar ícone: {e}")

        # Elementos do Ecrã Inicial
        self.label_titulo = ctk.CTkLabel(self, text="🎵 Meaw-Zik", font=("Arial", 24, "bold"))
        self.label_titulo.pack(pady=(40, 20))

        self.label_sub = ctk.CTkLabel(self, text="Escolha o modo de reprodução", font=("Arial", 12), text_color="gray")
        self.label_sub.pack(pady=(5, 20))

        # Botão Sessão Solo
        self.btn_solo = ctk.CTkButton(self, text="🎧 Sessão Solo", width=220, height=40, font=("Arial", 14), command=self.abrir_solo)
        self.btn_solo.pack(pady=10)

        # Botão Sessão em Grupo (Placeholder)
        self.btn_grupo = ctk.CTkButton(self, text="👥 Sessão em Grupo", width=220, height=40, font=("Arial", 14), fg_color="#4b4b4b", hover_color="#333333", command=self.abrir_grupo)
        self.btn_grupo.pack(pady=10)

    def abrir_solo(self):
        self.withdraw()
        player_janela = MeawZikPlayerWindow(self)
        player_janela.protocol("WM_DELETE_WINDOW", lambda: self.fechar_player(player_janela))

    def abrir_grupo(self):
        print("[*] Funcionalidade de grupo em breve...")

    def fechar_player(self, janela_player):
        janela_player.destroy()
        self.deiconify()

if __name__ == "__main__":
    app = MeawZikHome()
    app.mainloop()