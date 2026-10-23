import os
import sys
import tkinter as tk
import customtkinter as ctk

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class GroupView(ctk.CTkToplevel):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        
        self.title("Meaw-Zik - Sessão em Grupo")
        self.geometry("860x660")
        self.resizable(False, False)

        try:
            caminho_ico = resource_path("meawzik.ico")
            if os.path.exists(caminho_ico):
                self.iconbitmap(caminho_ico)
        except Exception as e:
            print(f"[!] Erro ao carregar ícone: {e}")

        # --- LAYOUT PRINCIPAL ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        self._criar_menu_inicial()
        self._criar_form_entrar()
        self._criar_sessao_ativa()

        self.voltar_ao_menu_inicial()

    def _criar_menu_inicial(self):
        self.frame_menu_inicial = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        self.btn_voltar = ctk.CTkButton(
            self.frame_menu_inicial, text="← Voltar", width=220, height=38, 
            fg_color="#555555", hover_color="#444444", command=self.controller.voltar_ao_menu_principal
        )
        self.btn_voltar.pack(pady=(0, 15))

        self.btn_host_inicial = ctk.CTkButton(
            self.frame_menu_inicial, text="Hospedar Sessão", width=220, height=40,
            command=self.controller.pedir_dados_hospedagem
        )
        self.btn_host_inicial.pack(pady=(0, 8))

        self.btn_join_inicial = ctk.CTkButton(
            self.frame_menu_inicial, text="Entrar em Sessão", width=220, height=40,
            fg_color="#2b8a3e", hover_color="#2b7033", command=self.mostrar_campos_entrar
        )
        self.btn_join_inicial.pack()

    def _criar_form_entrar(self):
        self.frame_form_entrar = ctk.CTkFrame(self.main_container, fg_color="transparent")

        self.ip_entry = ctk.CTkEntry(self.frame_form_entrar, placeholder_text="IP do Anfitrião (Ex: 192.168.1.10)", width=310, height=35)
        self.ip_entry.pack(pady=(0, 10))

        self.key_entry = ctk.CTkEntry(self.frame_form_entrar, placeholder_text="Chave de Acesso", width=310, height=35, show="*")
        self.key_entry.pack(pady=(0, 12))

        self.botoes_entrar_frame = ctk.CTkFrame(self.frame_form_entrar, fg_color="transparent")
        self.botoes_entrar_frame.pack()

        self.btn_executar_entrar = ctk.CTkButton(
            self.botoes_entrar_frame, text="Conectar", width=145, height=35,
            fg_color="#2b8a3e", hover_color="#2b7033", command=self.controller.entrar_sessao
        )
        self.btn_executar_entrar.pack(side="left", padx=5)

        self.btn_cancelar_entrar = ctk.CTkButton(
            self.botoes_entrar_frame, text="Cancelar", width=145, height=35,
            fg_color="#555555", hover_color="#444444", command=self.voltar_ao_menu_inicial
        )
        self.btn_cancelar_entrar.pack(side="left", padx=5)

    def _criar_sessao_ativa(self):
        self.frame_sessao_ativa = ctk.CTkFrame(self.main_container, fg_color="transparent")

        # Topo com Status e Credenciais (visível especialmente se for Host)
        self.painel_credenciais = ctk.CTkFrame(self.frame_sessao_ativa, fg_color="#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#e6e6e6", corner_radius=6)
        self.painel_credenciais.pack(fill="x", pady=(0, 10), padx=2)

        self.info_topo_inner = ctk.CTkFrame(self.painel_credenciais, fg_color="transparent")
        self.info_topo_inner.pack(fill="x", padx=10, pady=8)

        self.label_info_nome = ctk.CTkLabel(self.info_topo_inner, text="🏠 Sessão: ---", font=("Arial", 12, "bold"), text_color="#1f6aa5")
        self.label_info_nome.pack(side="left", anchor="w")

        self.btn_sair_sessao = ctk.CTkButton(
            self.info_topo_inner, text="Sair / Encerrar", width=100, height=26,
            fg_color="#c92a2a", hover_color="#a61e1e", command=self.voltar_ao_menu_inicial
        )
        self.btn_sair_sessao.pack(side="right")

        # Detalhes de IP e Chave para partilha rápida
        self.detalhes_compartilhar = ctk.CTkFrame(self.painel_credenciais, fg_color="transparent")
        self.detalhes_compartilhar.pack(fill="x", padx=10, pady=(0, 8))

        self.label_ip_val = ctk.CTkLabel(self.detalhes_compartilhar, text="IP: ---", font=("Arial", 11))
        self.label_ip_val.pack(side="left", padx=(0, 5))
        self.ip_val_copiar = ctk.CTkButton(self.detalhes_compartilhar, text="Copiar IP 📋", width=80, height=24, fg_color="#333333", hover_color="#444444", command=self.controller.copiar_ip)
        self.ip_val_copiar.pack(side="left", padx=(0, 15))

        self.label_key_val = ctk.CTkLabel(self.detalhes_compartilhar, text="Chave: ---", font=("Arial", 11))
        self.label_key_val.pack(side="left", padx=(0, 5))
        self.key_val_copiar = ctk.CTkButton(self.detalhes_compartilhar, text="Copiar Chave 📋", width=95, height=24, fg_color="#333333", hover_color="#444444", command=self.controller.copiar_chave)
        self.key_val_copiar.pack(side="left")

        # Layout Dividido: Esquerda (Músicas/Fila) e Direita (Participantes)
        self.content_split_frame = ctk.CTkFrame(self.frame_sessao_ativa, fg_color="transparent")
        self.content_split_frame.pack(fill="both", expand=True, pady=(0, 5))

        # Painel Esquerdo
        self.left_panel = ctk.CTkFrame(self.content_split_frame, fg_color="transparent")
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.search_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.search_frame.pack(fill="x", pady=(0, 8))

        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Pesquisar músicas...", height=35)
        self.search_entry.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.btn_search = ctk.CTkButton(self.search_frame, text="Pesquisar", width=90, height=35, command=self.controller.pesquisar_musica)
        self.btn_search.pack(side="right")

        self.label_res = ctk.CTkLabel(self.left_panel, text="Resultados da Pesquisa:", font=("Arial", 10, "bold"))
        self.label_res.pack(anchor="w", pady=(0, 2))
        
        self.search_box = tk.Listbox(
            self.left_panel, height=5,
            bg="#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0",
            fg="white" if ctk.get_appearance_mode() == "Dark" else "black",
            selectbackground="#1f6aa5", borderwidth=0, highlightthickness=0, font=("Arial", 9)
        )
        self.search_box.pack(fill="x", pady=(0, 8))
        self.search_box.bind("<Double-Button-1>", self.controller.ao_selecionar_pesquisa)

        self.label_fila = ctk.CTkLabel(self.left_panel, text="📜 Fila de Reprodução:", font=("Arial", 10, "bold"))
        self.label_fila.pack(anchor="w", pady=(0, 2))

        self.playlist_box = tk.Listbox(
            self.left_panel, height=7,
            bg="#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0",
            fg="white" if ctk.get_appearance_mode() == "Dark" else "black",
            selectbackground="#2b8a3e", borderwidth=0, highlightthickness=0, font=("Arial", 9)
        )
        self.playlist_box.pack(fill="both", expand=True, pady=(0, 5))
        self.playlist_box.bind("<Double-Button-1>", self.controller.ao_selecionar_fila)

        # Painel Direito (Participantes)
        self.right_panel = ctk.CTkFrame(self.content_split_frame, width=180)
        self.right_panel.pack(side="right", fill="y", padx=(0, 0))

        self.label_part = ctk.CTkLabel(self.right_panel, text="👥 Participantes", font=("Arial", 11, "bold"))
        self.label_part.pack(pady=(8, 5))

        self.participants_box = tk.Listbox(
            self.right_panel, width=22,
            bg="#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0",
            fg="white" if ctk.get_appearance_mode() == "Dark" else "black",
            selectbackground="#555555", borderwidth=0, highlightthickness=0, font=("Arial", 9)
        )
        self.participants_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Controles
        self.control_frame = ctk.CTkFrame(self.frame_sessao_ativa, fg_color="transparent")
        self.control_frame.pack(fill="x", pady=(5, 0))

        self.prev_btn = ctk.CTkButton(self.control_frame, text="⏮ Anterior", width=110, height=35, command=self.controller.acao_anterior)
        self.prev_btn.pack(side="left", padx=(0, 5))

        self.play_pause_btn = ctk.CTkButton(self.control_frame, text="▶ Play", width=140, height=35, command=self.controller.acao_play_pause)
        self.play_pause_btn.pack(side="left", expand=True, fill="x", padx=5)

        self.next_btn = ctk.CTkButton(self.control_frame, text="Próximo ⏭", width=110, height=35, command=self.controller.acao_proximo)
        self.next_btn.pack(side="right", padx=(5, 0))

        self.status_label = ctk.CTkLabel(self, text="Status: Desconectado", font=("Arial", 11), text_color="gray")
        self.status_label.pack(side="bottom", anchor="w", padx=20, pady=10)

    def mostrar_campos_entrar(self):
        self.frame_menu_inicial.pack_forget()
        self.frame_form_entrar.pack(expand=True)
        self.status_label.configure(text="Status: Insira o IP e a Chave de Acesso.")

    def voltar_ao_menu_inicial(self):
        self.frame_form_entrar.pack_forget()
        self.frame_sessao_ativa.pack_forget()
        self.frame_menu_inicial.pack(expand=True)
        self.status_label.configure(text="Status: Desconectado")

    def ativar_interface_sessao(self):
        self.frame_menu_inicial.pack_forget()
        self.frame_form_entrar.pack_forget()
        self.frame_sessao_ativa.pack(fill="both", expand=True)