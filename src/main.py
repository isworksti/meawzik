import os
import sys
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

# Importação atualizada para a estrutura modular dentro da pasta group
from group.group_controller import MeawZikGroupWindow
from player_core import MeawZikCore

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def resource_path(relative_path):
    """ Obtém o caminho absoluto para os recursos no PyInstaller ou desenvolvimento """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class MeawZikPlayerWindow(ctk.CTkToplevel):
    """ Janela principal do Player (Modo Solo) """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Meaw-Zik - Sessão Solo")
        self.geometry("600x450")
        self.resizable(False, False)

        try:
            caminho_ico = resource_path("meawzik.ico")
            if os.path.exists(caminho_ico):
                self.iconbitmap(caminho_ico)
        except Exception as e:
            print(f"[!] Erro ao carregar ícone: {e}")

        self.core = MeawZikCore()

        # --- LAYOUT DO PLAYER ---
        self.top_nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_nav_frame.pack(fill="x", padx=20, pady=(15, 0))

        self.btn_voltar = ctk.CTkButton(
            self.top_nav_frame, text="⬅ Voltar", width=140, 
            fg_color="#555555", hover_color="#444444", command=self.voltar_ao_menu
        )
        self.btn_voltar.pack(side="left")

        # Frame para os controlos de busca (URL / Nome)
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=20, pady=10)

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

    def voltar_ao_menu(self):
        """ Fecha a janela do player e reabre o menu principal """
        self.destroy()
        self.master.deiconify()

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
                self.iconbitmap(caminho_ico)
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

        # Botão Sessão em Grupo
        self.btn_grupo = ctk.CTkButton(self, text="👥 Sessão em Grupo", width=220, height=40, font=("Arial", 14), fg_color="#4b4b4b", hover_color="#333333", command=self.abrir_grupo)
        self.btn_grupo.pack(pady=10)

    def abrir_solo(self):
        self.withdraw()
        player_janela = MeawZikPlayerWindow(self)
        player_janela.protocol("WM_DELETE_WINDOW", lambda: self.fechar_player(player_janela))

    def abrir_grupo(self):
        """ Esconde o menu inicial e abre a janela de sessão em grupo P2P """
        self.withdraw()
        grupo_janela = MeawZikGroupWindow(self)
        grupo_janela.protocol("WM_DELETE_WINDOW", lambda: self.fechar_grupo(grupo_janela))

    def fechar_grupo(self, janela_grupo):
        """ Fecha a janela de grupo e retorna ao menu principal """
        janela_grupo.destroy()
        self.deiconify()

    def fechar_player(self, janela_player):
        janela_player.destroy()
        self.deiconify()

if __name__ == "__main__":
    app = MeawZikHome()
    app.mainloop()