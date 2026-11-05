import os
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QScrollArea, QSlider, QLabel, QFrame
)
from PyQt6.QtGui import QIcon
from player_core import MeawZikCore, SearchWorker, AudioWorker

class MeawZikPlayerWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__()
        self.parent_home = parent
        self.setWindowTitle("MeawZik")
        self.resize(850, 550)

        # Inicializa o Core
        self.core = MeawZikCore()
        
        # Estado do Tema (True = Escuro, False = Claro)
        self.is_dark_theme = True
        
        # Referências para workers ativos
        self.search_worker = None
        self.audio_worker = None

        self.init_ui()
        self.aplicar_estilo_tema()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. Barra de Pesquisa + Botão de Alternância de Tema ao lado
        search_layout = QHBoxLayout()
        self.input_pesquisa = QLineEdit()
        self.input_pesquisa.setPlaceholderText("Digite o nome da música ou cole o link do YouTube...")
        self.input_pesquisa.returnPressed.connect(self.executar_pesquisa)
        
        self.btn_pesquisar = QPushButton("Pesquisar")
        self.btn_pesquisar.clicked.connect(self.executar_pesquisa)
        
        # Botão de Tema (Alternar Dark/Light) posicionado ao lado do pesquisar
        self.btn_tema = QPushButton("🌙")
        self.btn_tema.setToolTip("Alternar Tema Claro/Escuro")
        self.btn_tema.setFixedSize(40, 36)
        self.btn_tema.clicked.connect(self.alternar_tema)
        
        search_layout.addWidget(self.input_pesquisa)
        search_layout.addWidget(self.btn_pesquisar)
        search_layout.addWidget(self.btn_tema)
        main_layout.addLayout(search_layout)

        # 2. Área Central (Resultados da Busca e Fila de Reprodução em QScrollArea)
        content_layout = QHBoxLayout()

        # ScrollArea para os Resultados da Pesquisa com distribuição uniforme
        self.scroll_resultados = QScrollArea()
        self.scroll_resultados.setWidgetResizable(True)
        self.scroll_resultados.setStyleSheet("""
            QScrollArea { 
                background-color: #181825; 
                border: 1px solid #313244; 
                border-radius: 6px; 
            }
        """)
        
        self.container_resultados = QWidget()
        self.container_resultados.setStyleSheet("background: transparent;")
        self.layout_container_resultados = QVBoxLayout(self.container_resultados)
        self.layout_container_resultados.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout_container_resultados.setContentsMargins(4, 4, 4, 4)
        self.layout_container_resultados.setSpacing(4)
        
        self.scroll_resultados.setWidget(self.container_resultados)
        
        # Fila de reprodução em QScrollArea com células compactas
        self.scroll_fila = QScrollArea()
        self.scroll_fila.setWidgetResizable(True)
        self.scroll_fila.setStyleSheet("""
            QScrollArea { 
                background-color: #181825; 
                border: 1px solid #313244; 
                border-radius: 6px; 
            }
        """)
        
        self.container_fila = QWidget()
        self.container_fila.setStyleSheet("background: transparent;")
        self.layout_container_fila = QVBoxLayout(self.container_fila)
        self.layout_container_fila.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout_container_fila.setContentsMargins(4, 4, 4, 4)
        self.layout_container_fila.setSpacing(4)
        
        self.scroll_fila.setWidget(self.container_fila)

        content_layout.addWidget(self.scroll_resultados, stretch=1)
        content_layout.addWidget(self.scroll_fila, stretch=1)
        main_layout.addLayout(content_layout)

        # 3. Painel de Controlo de Áudio (Player com Ícones Personalizados)
        player_frame = QFrame()
        player_layout = QVBoxLayout(player_frame)

        # Slider de Progresso e Tempos
        progress_layout = QHBoxLayout()
        self.lbl_tempo_atual = QLabel("00:00")
        self.slider_progresso = QSlider(Qt.Orientation.Horizontal)
        self.slider_progresso.setRange(0, 1000)
        self.lbl_tempo_total = QLabel("00:00")

        progress_layout.addWidget(self.lbl_tempo_atual)
        progress_layout.addWidget(self.slider_progresso)
        progress_layout.addWidget(self.lbl_tempo_total)
        player_layout.addLayout(progress_layout)

        # Botões de Controlo do Player
        controls_layout = QHBoxLayout()
        
        # 1. Bloco esquerdo de balanceamento (mesma largura exata do bloco de volume à direita)
        left_balancer = QWidget()
        left_balancer.setFixedWidth(130)
        
        # 2. Container central para os botões multimédia (com o shuffle na ponta direita)
        center_widget = QWidget()
        center_layout = QHBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(6)
        
        self.btn_repeat = QPushButton()
        self.btn_prev = QPushButton()
        self.btn_play = QPushButton()
        self.btn_next = QPushButton()
        self.btn_shuffle = QPushButton()  # Movido para o fim
        
        for btn in [self.btn_repeat, self.btn_prev, self.btn_play, self.btn_next, self.btn_shuffle]:
            btn.setFixedSize(38, 38)
            center_layout.addWidget(btn)

        # 3. Slider de volume reduzido a 50% e posicionado à direita
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(70)
        self.slider_volume.setMaximumWidth(120)
        self.slider_volume.valueChanged.connect(self.ajustar_volume)

        # Ligações de eventos dos botões
        self.btn_play.clicked.connect(self.alternar_play_pause)
        self.btn_next.clicked.connect(self.proxima_faixa)
        self.btn_prev.clicked.connect(self.faixa_anterior)
        self.btn_repeat.clicked.connect(self.alternar_repeticao)
        self.btn_shuffle.clicked.connect(self.alternar_aleatorio)

        # 4. Bloco direito (Volume)
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("🔊"))
        right_layout.addWidget(self.slider_volume)
        right_widget.setFixedWidth(130)  # Mesma largura do left_balancer para simetria perfeita

        # Montagem final do layout equilibrado
        controls_layout.addWidget(left_balancer)
        controls_layout.addStretch(1)
        controls_layout.addWidget(center_widget)
        controls_layout.addStretch(1)
        controls_layout.addWidget(right_widget)

        player_layout.addLayout(controls_layout)
        main_layout.addWidget(player_frame)

        # Barra de Status
        self.lbl_status = QLabel("Pronto.")
        main_layout.addWidget(self.lbl_status)

        self.atualizar_icones_player()

    def obter_caminho_icone(self, nome_base):
        """Retorna o caminho correto para o ícone .ico dependendo do tema ou pasta específica"""
        if nome_base == "cancelar":
            caminho = os.path.join("icons", "navegation", "cancelar.ico")
            if os.path.exists(caminho):
                return caminho
                
        pasta_tema = "dark_theme" if self.is_dark_theme else "light_theme"
        caminho = os.path.join("icons", pasta_tema, f"{nome_base}.ico")
        if os.path.exists(caminho):
            return caminho
        return ""

    def atualizar_icones_player(self):
        """Atualiza os ícones dos botões do player com base nos ficheiros .ico da pasta icons/"""
        sufixo = "dark" if self.is_dark_theme else "light"
        
        icon_play = self.obter_caminho_icone(f"pause_{sufixo}" if self.core.is_playing_state else f"play_{sufixo}")
        icon_voltar = self.obter_caminho_icone(f"voltar_{sufixo}")
        icon_avancar = self.obter_caminho_icone(f"avançar_{sufixo}")
        icon_repetir = self.obter_caminho_icone(f"repetir_{sufixo}")
        icon_aleatorio = self.obter_caminho_icone(f"aleatório_{sufixo}")

        if icon_play: self.btn_play.setIcon(QIcon(icon_play))
        if icon_voltar: self.btn_prev.setIcon(QIcon(icon_voltar))
        if icon_avancar: self.btn_next.setIcon(QIcon(icon_avancar))
        if icon_repetir: self.btn_repeat.setIcon(QIcon(icon_repetir))
        if icon_aleatorio: self.btn_shuffle.setIcon(QIcon(icon_aleatorio))

    def alternar_tema(self):
        self.is_dark_theme = not self.is_dark_theme
        self.btn_tema.setText("🌙" if self.is_dark_theme else "☀️")
        self.aplicar_estilo_tema()
        self.atualizar_icones_player()
        self.atualizar_ui_fila()

    def aplicar_estilo_tema(self):
        if self.is_dark_theme:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI', sans-serif; }
                QLineEdit { background-color: #313244; border: 1px solid #45475a; border-radius: 6px; padding: 8px; color: #cdd6f4; }
                QPushButton { background-color: #89b4fa; color: #11111b; font-weight: bold; border-radius: 6px; padding: 8px 12px; border: none; }
                QPushButton:hover { background-color: #b4befe; }
                QListWidget { background-color: #181825; border: 1px solid #313244; border-radius: 6px; padding: 4px; color: #cdd6f4; }
                QListWidget::item { background: transparent; border: none; padding: 4px; border-radius: 4px; }
                QListWidget::item:selected { background: #313244; }
                QScrollArea { background-color: #181825; border: 1px solid #313244; border-radius: 6px; }
                QSlider::groove:horizontal { height: 6px; background: #45475a; border-radius: 3px; }
                QSlider::handle:horizontal { background: #89b4fa; width: 14px; margin: -4px 0; border-radius: 7px; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #f5f5f7; color: #1d1d1f; font-family: 'Segoe UI', sans-serif; }
                QLineEdit { background-color: #ffffff; border: 1px solid #d2d2d7; border-radius: 6px; padding: 8px; color: #1d1d1f; }
                QPushButton { background-color: #0071e3; color: #ffffff; font-weight: bold; border-radius: 6px; padding: 8px 12px; border: none; }
                QPushButton:hover { background-color: #0077ed; }
                QListWidget { background-color: #ffffff; border: 1px solid #d2d2d7; border-radius: 6px; padding: 4px; color: #1d1d1f; }
                QListWidget::item { background: transparent; border: none; padding: 4px; border-radius: 4px; }
                QListWidget::item:selected { background: #e8e8ed; }
                QScrollArea { background-color: #ffffff; border: 1px solid #d2d2d7; border-radius: 6px; }
                QSlider::groove:horizontal { height: 6px; background: #d2d2d7; border-radius: 3px; }
                QSlider::handle:horizontal { background: #0071e3; width: 14px; margin: -4px 0; border-radius: 7px; }
            """)

    def executar_pesquisa(self):
        termo = self.input_pesquisa.text().strip()
        if not termo:
            return
        self.lbl_status.setText(f"A pesquisar por '{termo}'...")
        self.search_worker = SearchWorker(termo)
        self.search_worker.sucesso.connect(self.exibir_resultados)
        self.search_worker.erro.connect(lambda err: self.lbl_status.setText(f"Erro na pesquisa: {err}"))
        self.search_worker.start()

    def exibir_resultados(self, resultados):
        while self.layout_container_resultados.count():
            child = self.layout_container_resultados.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        self.core.resultados_pesquisa = resultados[:10]  
        
        cor_bg_hover = "#45475a" if self.is_dark_theme else "#d2d2d7"
        cor_texto = "#cdd6f4" if self.is_dark_theme else "#1d1d1f"
        
        for i, res in enumerate(self.core.resultados_pesquisa):
            linha_widget = QWidget()
            linha_widget.setStyleSheet(
                "QWidget { "
                "    background-color: transparent; "
                "    border-radius: 4px; "
                "} "
                "QWidget:hover { "
                f"    background-color: {cor_bg_hover}; "
                "}"
            )
            
            layout_linha = QHBoxLayout(linha_widget)
            layout_linha.setContentsMargins(8, 3, 8, 3)
            layout_linha.setSpacing(8)
            
            titulo_completo = f"{i+1}. {res['title']}"
            limite_caracteres = 48
            titulo_exibido = titulo_completo if len(titulo_completo) <= limite_caracteres else titulo_completo[:limite_caracteres] + "..."
            
            lbl_titulo = QLabel(titulo_exibido)
            lbl_titulo.setStyleSheet(f"color: {cor_texto}; background: transparent; border: none; font-size: 12px;")
            
            lbl_titulo.setToolTip(titulo_completo)
            linha_widget.setToolTip(titulo_completo)
            
            layout_linha.addWidget(lbl_titulo, stretch=1)
            
            linha_widget.mouseDoubleClickEvent = lambda event, idx=i: self.adicionar_indice_a_fila(idx)
            
            self.layout_container_resultados.addWidget(linha_widget, stretch=1)
            
        self.lbl_status.setText(f"{len(self.core.resultados_pesquisa)} resultados encontrados.")
        
    def adicionar_indice_a_fila(self, indice):
        if 0 <= indice < len(self.core.resultados_pesquisa):
            item = self.core.resultados_pesquisa[indice]
            self.core.adicionar_a_fila(item)
            self.atualizar_ui_fila()
            self.lbl_status.setText(f"Adicionado à fila: {item['title']}")
            
            if len(self.core.fila) == 1:
                self.tocar_indice(0)

    def tocar_indice(self, indice):
        if 0 <= indice < len(self.core.fila):
            self.core.indice_atual = indice
            faixa = self.core.fila[indice]
            self.lbl_status.setText(f"A carregar stream: {faixa['title']}...")
            self.atualizar_ui_fila()
            
            self.audio_worker = AudioWorker(faixa['url'], faixa['title'], self.core.cache_urls)
            self.audio_worker.sucesso.connect(self.iniciar_reproducao_vlc)
            self.audio_worker.erro.connect(lambda err: self.lbl_status.setText(f"Erro ao carregar áudio: {err}"))
            self.audio_worker.start()

    def iniciar_reproducao_vlc(self, audio_url, titulo):
        try:
            media = self.core.vlc_instance.media_new(audio_url)
            self.core.player.set_media(media)
            self.core.player.play()
            self.core.is_playing_state = True
            self.atualizar_icones_player()
            self.lbl_status.setText(f"Reproduzindo: {titulo}")
            self.atualizar_ui_fila()
        except Exception as e:
            self.lbl_status.setText(f"Erro ao reproduzir no VLC: {e}")

    def atualizar_ui_fila(self):
        while self.layout_container_fila.count():
            child = self.layout_container_fila.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        cor_bg_linha = "#313244" if self.is_dark_theme else "#e8e8ed"
        cor_bg_hover = "#45475a" if self.is_dark_theme else "#d2d2d7"
        cor_texto = "#cdd6f4" if self.is_dark_theme else "#1d1d1f"
        
        for i, faixa in enumerate(self.core.fila):
            linha_widget = QWidget()
            
            bg_cor = cor_bg_linha if i == self.core.indice_atual else "transparent"
            # Duplicamos as chavetas {{ e }} para o Python não confundir com variáveis de f-string
            linha_widget.setStyleSheet(
                "QWidget { "
                f"    background-color: {bg_cor}; "
                "    border-radius: 5px; "
                "} "
                "QWidget:hover { "
                f"    background-color: {cor_bg_hover}; "
                "}"
            )
            
            layout_linha = QHBoxLayout(linha_widget)
            layout_linha.setContentsMargins(10, 5, 6, 5)
            layout_linha.setSpacing(8)
            
            prefixo = "▶ " if i == self.core.indice_atual else "  "
            lbl_titulo = QLabel(f"{prefixo}{i+1}. {faixa['title']}")
            lbl_titulo.setStyleSheet(f"color: {cor_texto}; background: transparent; border: none; font-size: 12px;")
            
            btn_remover = QPushButton()
            btn_remover.setFixedSize(22, 22)
            
            caminho_icone_rem = self.obter_caminho_icone("cancelar")
            
            if caminho_icone_rem and os.path.exists(caminho_icone_rem):
                btn_remover.setIcon(QIcon(caminho_icone_rem))
                btn_remover.setStyleSheet(
                    "QPushButton { "
                    "    background-color: transparent; "
                    "    border: none; "
                    "    border-radius: 4px; "
                    "} "
                    "QPushButton:hover { "
                    "    background-color: #f38ba8; "
                    "}"
                )
            else:
                btn_remover.setText("X")
                btn_remover.setStyleSheet(
                    "QPushButton { "
                    "    background-color: #f38ba8; "
                    "    color: #1e1e2e; "
                    "    border: none; "
                    "    font-weight: bold; "
                    "    font-size: 10px; "
                    "    border-radius: 4px; "
                    "} "
                    "QPushButton:hover { "
                    "    background-color: #eba0ac; "
                    "}"
                )
                
            btn_remover.clicked.connect(lambda checked, idx=i: self.remover_item_fila(idx))
            
            layout_linha.addWidget(lbl_titulo, stretch=1)
            layout_linha.addWidget(btn_remover, stretch=0, alignment=Qt.AlignmentFlag.AlignVCenter)
            
            linha_widget.mouseDoubleClickEvent = lambda event, idx=i: self.tocar_indice(idx)
            self.layout_container_fila.addWidget(linha_widget)

    def remover_item_fila(self, indice):
        faixa = self.core.remover_da_fila(indice)
        if faixa:
            self.atualizar_ui_fila()
            self.lbl_status.setText(f"'{faixa['title']}' removida da fila.")
            if not self.core.fila:
                self.core.parar()
                self.atualizar_icones_player()    

    def alternar_play_pause(self):
        if not self.core.fila:
            return
        tocando = self.core.alternar_play_pause()
        self.atualizar_icones_player()

    def alternar_aleatorio(self):
        ativo = self.core.alternar_shuffle()
        self.lbl_status.setText(f"Modo Aleatório: {'Ativado' if ativo else 'Desativado'}")

    def proxima_faixa(self):
        if self.core.indice_atual + 1 < len(self.core.fila):
            self.tocar_indice(self.core.indice_atual + 1)

    def faixa_anterior(self):
        if self.core.indice_atual - 1 >= 0:
            self.tocar_indice(self.core.indice_atual - 1)

    def alternar_repeticao(self):
        repetir = self.core.alternar_repeat()
        self.lbl_status.setText(f"Modo Repetição: {'Ativado' if repetir else 'Desativado'}")

    def ajustar_volume(self, val):
        self.core.definir_volume(val)

    def closeEvent(self, event):
        try:
            self.core.parar()
        except Exception:
            pass
        if self.parent_home:
            self.parent_home.deiconify()
        event.accept()