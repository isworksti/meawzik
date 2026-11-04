import os
import sys
import tkinter as tk
import customtkinter as ctk
from PIL import Image

class PlayerUI(ctk.CTkToplevel):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.title("MeawZik")
        self.geometry("640x380")
        self.minsize(640, 360)
        self.resizable(True, True)
        self.controller = controller

        self.is_dark = ctk.get_appearance_mode() == "Dark"
        
        # Carrega os CTkImages para os botões com suporte a Dark/Light
        self._carregar_icones()
        self._aplicar_cores_tema()

        # --- BARRA DE PESQUISA E TEMA ---
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=15, pady=(8, 4))

        self.url_entry = ctk.CTkEntry(self.top_frame, placeholder_text="Pesquisar música...", width=380, height=26)
        self.url_entry.pack(side="left", padx=(0, 8), expand=True, fill="x")
        self.url_entry.bind("<Return>", lambda event: self.controller.ao_clicar_buscar())

        self.load_btn = ctk.CTkButton(self.top_frame, text="Buscar", width=75, height=26, command=self.controller.ao_clicar_buscar)
        self.load_btn.pack(side="left", padx=(0, 8))

        self.theme_btn = ctk.CTkButton(self.top_frame, text="🌓 Tema", width=70, height=26, fg_color="gray", command=self.alternar_tema)
        self.theme_btn.pack(side="right")

        # --- PAINEL DE RESULTADOS DE PESQUISA ---
        self.search_container = ctk.CTkFrame(self, fg_color=self.bg_card, border_width=1, border_color=self.border_color)
        self.search_container.pack(fill="x", padx=15, pady=(0, 3))

        self.search_titulo_label = ctk.CTkLabel(
            self.search_container, text="🔍 Resultados:", font=("Segoe UI", 8, "bold"), text_color=self.text_color
        )
        self.search_titulo_label.pack(anchor="w", padx=8, pady=(3, 1))

        self.search_box = tk.Listbox(
            self.search_container, bg=self.bg_listbox, fg=self.fg_listbox, selectbackground="#316ac5",
            borderwidth=0, highlightthickness=0, font=("Segoe UI", 9), height=5
        )
        self.search_box.pack(fill="x", expand=True, padx=8, pady=(0, 3))
        self.search_box.bind("<Double-Button-1>", lambda event: self.controller.adicionar_selecionada_pesquisa())

        # --- PAINEL DA FILA DE REPRODUÇÃO ---
        self.queue_container = ctk.CTkFrame(self, fg_color=self.bg_card, border_width=1, border_color=self.border_color)
        self.queue_container.pack(fill="x", padx=15, pady=(0, 3))

        self.fila_titulo_label = ctk.CTkLabel(
            self.queue_container, text="🎵 Fila de Reprodução:", font=("Segoe UI", 8, "bold"), text_color=self.text_color_accent
        )
        self.fila_titulo_label.pack(anchor="w", padx=8, pady=(3, 1))

        self.playlist_box = tk.Listbox(
            self.queue_container, bg=self.bg_listbox, fg=self.fg_listbox, selectbackground="#316ac5",
            borderwidth=0, highlightthickness=0, font=("Segoe UI", 9), height=5
        )
        self.playlist_box.pack(fill="x", expand=True, padx=8, pady=(0, 3))
        self.playlist_box.bind("<Double-Button-1>", lambda event: self.controller.remover_da_fila())

        # --- BARRA DE PROGRESSO ---
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=15, pady=(0, 3))

        self.tempo_atual_label = ctk.CTkLabel(self.progress_frame, text="00:00", font=("Segoe UI", 8), text_color=self.text_sub)
        self.tempo_atual_label.pack(side="left", padx=(0, 6))

        self.slider_progresso = ctk.CTkSlider(self.progress_frame, from_=0, to=100, height=10, command=self.controller.ao_ajustar_slider)
        self.slider_progresso.pack(side="left", fill="x", expand=True, padx=3)
        self.slider_progresso.set(0)

        self.tempo_total_label = ctk.CTkLabel(self.progress_frame, text="00:00", font=("Segoe UI", 8), text_color=self.text_sub)
        self.tempo_total_label.pack(side="right", padx=(6, 0))

        # --- BARRA DE CONTROLOS INFERIOR ---
        self.control_panel_frame = ctk.CTkFrame(self, fg_color=self.bg_control_bar, border_width=1, border_color=self.border_color, corner_radius=6)
        self.control_panel_frame.pack(fill="x", padx=15, pady=(0, 3))

        self.control_inner = ctk.CTkFrame(self.control_panel_frame, fg_color="transparent", height=36)
        self.control_inner.pack(fill="x", padx=6, pady=2)
        self.control_inner.pack_propagate(False)

        # 1. Lado esquerdo: Botão Repetir (substituindo o shuffle ou posicionado adequadamente)
        self.left_container = ctk.CTkFrame(self.control_inner, fg_color="transparent")
        self.left_container.pack(side="left", anchor="c")

        self.btn_repeat = ctk.CTkButton(
            self.left_container, text="", image=self.icon_repetir, width=32, height=32, 
            fg_color="transparent", hover_color=self.btn_hover, command=self.controller.clicar_repeat
        )
        self.btn_repeat.pack(side="left", padx=(1, 0))

        # 3. Lado direito: Volume
        self.right_container = ctk.CTkFrame(self.control_inner, fg_color="transparent")
        self.right_container.pack(side="right", anchor="c")

        self.vol_label = ctk.CTkLabel(self.right_container, text="Vol:", font=("Segoe UI", 8), text_color=self.text_sub)
        self.vol_label.pack(side="left", padx=(0, 2))

        self.slider_volume = ctk.CTkSlider(self.right_container, from_=0, to=100, width=50, height=8, command=self.controller.ao_ajustar_volume)
        self.slider_volume.pack(side="left")
        self.slider_volume.set(70)

        # 2. Centro: Botões de Navegação (Voltar, Play/Pause, Avançar) com as imagens
        self.btns_center_frame = ctk.CTkFrame(self.control_inner, fg_color="transparent")
        self.btns_center_frame.place(relx=0.5, rely=0.5, anchor="center")

        self.btn_anterior = ctk.CTkButton(
            self.btns_center_frame, text="", image=self.icon_voltar, width=32, height=32, 
            fg_color="transparent", hover_color=self.btn_hover, command=self.controller.clicar_anterior
        )
        self.btn_anterior.pack(side="left", padx=4)

        self.play_pause_btn = ctk.CTkButton(
            self.btns_center_frame, text="", image=self.icon_play, width=38, height=38, corner_radius=19, 
            fg_color="transparent", hover_color=self.btn_hover, command=self.controller.alternar_play_pause
        )
        self.play_pause_btn.pack(side="left", padx=4)

        self.btn_proximo = ctk.CTkButton(
            self.btns_center_frame, text="", image=self.icon_avancar, width=32, height=32, 
            fg_color="transparent", hover_color=self.btn_hover, command=self.controller.clicar_proximo
        )
        self.btn_proximo.pack(side="left", padx=4)

        # --- STATUS ---
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=15, pady=(0, 4))

        self.status_label = ctk.CTkLabel(self.status_frame, text="Pronto", font=("Segoe UI", 8), text_color=self.text_sub)
        self.status_label.pack(anchor="w")

    def _carregar_icones(self):
        """Carrega os ícones utilizando CTkImage com suporte robusto a caminhos"""
        def get_path(subpasta, nome_arquivo):
            relative_path = os.path.join("Icons", subpasta, nome_arquivo)
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            
            caminho = os.path.join(base_path, relative_path)
            
            # Se não encontrar, tenta procurar na pasta acima (raiz do projeto)
            if not os.path.exists(caminho) and not hasattr(sys, '_MEIPASS'):
                caminho_raiz = os.path.join(os.path.abspath(os.path.join(base_path, "..")), relative_path)
                if os.path.exists(caminho_raiz):
                    return caminho_raiz
            return caminho

        # Carrega os CTkImage passando a versão dark e light para cada ação
        self.icon_play = ctk.CTkImage(
            light_image=Image.open(get_path("light_theme", "play_light.png")),
            dark_image=Image.open(get_path("dark_theme", "play_dark.png")),
            size=(18, 18)
        )
        self.icon_pause = ctk.CTkImage(
            light_image=Image.open(get_path("light_theme", "pause_light.png")),
            dark_image=Image.open(get_path("dark_theme", "pause_dark.png")),
            size=(18, 18)
        )
        self.icon_voltar = ctk.CTkImage(
            light_image=Image.open(get_path("light_theme", "voltar_light.png")),
            dark_image=Image.open(get_path("dark_theme", "voltar_dark.png")),
            size=(16, 16)
        )
        self.icon_avancar = ctk.CTkImage(
            light_image=Image.open(get_path("light_theme", "avançar_light.png")),
            dark_image=Image.open(get_path("dark_theme", "avançar_dark.png")),
            size=(16, 16)
        )
        self.icon_repetir = ctk.CTkImage(
            light_image=Image.open(get_path("light_theme", "repetir_light.png")),
            dark_image=Image.open(get_path("dark_theme", "repetir_dark.png")),
            size=(16, 16)
        )

    def atualizar_icone_play_pause(self, tocando: bool):
        """Alterna a imagem do botão central entre Play e Pause dinamicamente"""
        if tocando:
            self.play_pause_btn.configure(image=self.icon_pause)
        else:
            self.play_pause_btn.configure(image=self.icon_play)

    def _aplicar_cores_tema(self):
        if self.is_dark:
            self.bg_window = "#1a1a1a"
            self.bg_card = "#242424"
            self.border_color = "#383838"
            self.bg_listbox = "#2b2b2b"
            self.fg_listbox = "#ffffff"
            self.text_color = "#cccccc"
            self.text_color_accent = "#4ea1f3"
            self.text_sub = "#aaaaaa"
            self.bg_control_bar = "#262626"
            self.btn_bg = "#333333"
            self.btn_hover = "#444444"
        else:
            self.bg_window = "#eef3f9"
            self.bg_card = "#ffffff"
            self.border_color = "#d0dbe5"
            self.bg_listbox = "#ffffff"
            self.fg_listbox = "#1a1a1a"
            self.text_color = "#4a607a"
            self.text_color_accent = "#1f497d"
            self.text_sub = "#555555"
            self.bg_control_bar = "#dfe8f5"
            self.btn_bg = "#c4d6ec"
            self.btn_hover = "#acccee"

    def alternar_tema(self):
        self.is_dark = not self.is_dark
        ctk.set_appearance_mode("Dark" if self.is_dark else "Light")
        self._aplicar_cores_tema()

        try:
            self.configure(fg_color=self.bg_window)
            self.search_container.configure(fg_color=self.bg_card, border_color=self.border_color)
            self.search_titulo_label.configure(text_color=self.text_color)
            self.search_box.configure(bg=self.bg_listbox, fg=self.fg_listbox)

            self.queue_container.configure(fg_color=self.bg_card, border_color=self.border_color)
            self.fila_titulo_label.configure(text_color=self.text_color_accent)
            self.playlist_box.configure(bg=self.bg_listbox, fg=self.fg_listbox)

            self.tempo_atual_label.configure(text_color=self.text_sub)
            self.tempo_total_label.configure(text_color=self.text_sub)

            self.control_panel_frame.configure(fg_color=self.bg_control_bar, border_color=self.border_color)
            self.btn_repeat.configure(hover_color=self.btn_hover)
            self.btn_anterior.configure(hover_color=self.btn_hover)
            self.btn_proximo.configure(hover_color=self.btn_hover)
            self.vol_label.configure(text_color=self.text_sub)
            self.status_label.configure(text_color=self.text_sub)
        except Exception as e:
            print(f"[!] Aviso ao atualizar cores do tema: {e}")