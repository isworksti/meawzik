import os
import sys
import vlc
import ctypes
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QScrollArea, QSlider, QLabel, QFrame, QInputDialog, QMessageBox
)
from PyQt6.QtGui import QIcon
from player_core import MeawZikCore, SearchWorker, AudioWorker


def resource_path(relative_path):
    """ Obtém o caminho absoluto para os recursos, compatível com o desenvolvimento e com o PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MeawZikPlayerWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__()
        self.parent_home = parent
        self.setWindowTitle("MeawZik")
        self.resize(850, 550)

        # Inicializa o Core
        self.core = MeawZikCore()

        caminho_icone_janela = resource_path("logo-meawzik.ico")
        if os.path.exists(caminho_icone_janela):
            self.setWindowIcon(QIcon(caminho_icone_janela))
        
        # Estado do Tema (True = Escuro, False = Claro)
        self.is_dark_theme = True
        self.a_ver_historico = False
        
        # Referências para workers ativos
        self.search_worker = None
        self.audio_worker = None

        self.init_ui()
        self.aplicar_estilo_tema()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. Barra de Pesquisa + Botão PLAYLISTS + Botão Pesquisar + Tema
        search_layout = QHBoxLayout()
        
        self.input_pesquisa = QLineEdit()
        self.input_pesquisa.setPlaceholderText("Digite o nome da música ou cole o link do YouTube...")
        self.input_pesquisa.setFixedHeight(38)
        self.input_pesquisa.returnPressed.connect(self.executar_pesquisa)
        
        self.btn_playlists = QPushButton("PLAYLISTS")
        self.btn_playlists.setFixedHeight(38)
        self.btn_playlists.setFixedWidth(90)
        self.btn_playlists.setToolTip("Ver histórico de playlists criadas")
        self.btn_playlists.clicked.connect(self.alternar_visao_playlists)

        self.btn_pesquisar = QPushButton("Pesquisar")
        self.btn_pesquisar.setFixedHeight(38)
        self.btn_pesquisar.clicked.connect(self.executar_pesquisa)
        
        # Botão de Tema (Alternar Dark/Light)
        self.btn_tema = QPushButton()
        self.btn_tema.setToolTip("Alternar Tema Claro/Escuro")
        self.btn_tema.setFixedSize(40, 38)
        self.btn_tema.clicked.connect(self.alternar_tema)
        
        search_layout.addWidget(self.input_pesquisa)
        search_layout.addWidget(self.btn_playlists)
        search_layout.addWidget(self.btn_pesquisar)
        search_layout.addWidget(self.btn_tema)
        main_layout.addLayout(search_layout)

        # 2. Área Central (Resultados da Busca e Fila de Reprodução)
        content_layout = QHBoxLayout()

        # ScrollArea para os Resultados da Pesquisa
        self.scroll_resultados = QScrollArea()
        self.scroll_resultados.setWidgetResizable(True)
        
        self.container_resultados = QWidget()
        self.container_resultados.setStyleSheet("background: transparent;")
        self.layout_container_resultados = QVBoxLayout(self.container_resultados)
        self.layout_container_resultados.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout_container_resultados.setContentsMargins(4, 4, 4, 4)
        self.layout_container_resultados.setSpacing(4)
        self.scroll_resultados.setWidget(self.container_resultados)
        
        # Fila de reprodução em QScrollArea
        self.scroll_fila = QScrollArea()
        self.scroll_fila.setWidgetResizable(True)
        
        self.container_fila = QWidget()
        self.container_fila.setStyleSheet("background: transparent;")
        self.layout_container_fila = QVBoxLayout(self.container_fila)
        self.layout_container_fila.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout_container_fila.setContentsMargins(4, 4, 4, 4)
        self.layout_container_fila.setSpacing(4)
        self.scroll_fila.setWidget(self.container_fila)

        # Coluna da Fila com Cabeçalho de Playlist e Botão de Nova Playlist (+)
        coluna_fila_layout = QVBoxLayout()
        
        topo_fila_layout = QHBoxLayout()
        self.lbl_titulo_playlist = QLabel("PLAYLIST \"X\"")
        self.lbl_titulo_playlist.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_titulo_playlist.setToolTip("Duplo clique para renomear a playlist")
        self.lbl_titulo_playlist.mouseDoubleClickEvent = self.ativar_edicao_nome_playlist
        
        self.btn_nova_playlist = QPushButton("+")
        self.btn_nova_playlist.setFixedSize(28, 28)
        self.btn_nova_playlist.setToolTip("Criar nova playlist")
        self.btn_nova_playlist.clicked.connect(self.acao_criar_nova_playlist)
        
        topo_fila_layout.addWidget(self.lbl_titulo_playlist, stretch=1)
        topo_fila_layout.addWidget(self.btn_nova_playlist, stretch=0)
        
        coluna_fila_layout.addLayout(topo_fila_layout)
        coluna_fila_layout.addWidget(self.scroll_fila)

        content_layout.addWidget(self.scroll_resultados, stretch=1)
        content_layout.addLayout(coluna_fila_layout, stretch=1)
        main_layout.addLayout(content_layout)

        # 3. Painel de Controlo de Áudio
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

        self.timer_progresso = QTimer(self)
        self.timer_progresso.setInterval(1000)
        self.timer_progresso.timeout.connect(self.atualizar_barra_progresso)
        self.slider_progresso.sliderReleased.connect(self.ao_soltar_slider)

        # Botões de Controlo do Player
        controls_layout = QHBoxLayout()
        
        left_balancer = QWidget()
        left_balancer.setFixedWidth(130)
        
        center_widget = QWidget()
        center_layout = QHBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(6)
        
        self.btn_repeat = QPushButton()
        self.btn_prev = QPushButton()
        self.btn_play = QPushButton()
        self.btn_next = QPushButton()
        self.btn_shuffle = QPushButton()
        
        for btn in [self.btn_repeat, self.btn_prev, self.btn_play, self.btn_next, self.btn_shuffle]:
            btn.setFixedSize(38, 38)
            center_layout.addWidget(btn)

        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(70)
        self.slider_volume.setMaximumWidth(120)
        self.slider_volume.valueChanged.connect(self.ajustar_volume)

        self.btn_play.clicked.connect(self.alternar_play_pause)
        self.btn_next.clicked.connect(self.proxima_faixa)
        self.btn_prev.clicked.connect(self.faixa_anterior)
        self.btn_repeat.clicked.connect(self.alternar_repeticao)
        self.btn_shuffle.clicked.connect(self.alternar_aleatorio)

        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("🔊"))
        right_layout.addWidget(self.slider_volume)
        right_widget.setFixedWidth(130)

        controls_layout.addWidget(left_balancer)
        controls_layout.addStretch(1)
        controls_layout.addWidget(center_widget)
        controls_layout.addStretch(1)
        controls_layout.addWidget(right_widget)

        player_layout.addLayout(controls_layout)
        main_layout.addWidget(player_frame)

        self.lbl_status = QLabel("Pronto.")
        main_layout.addWidget(self.lbl_status)

        self.atualizar_icones_player()
        self.atualizar_ui_fila()

    def formatar_tempo(self, ms):
        """Converte milissegundos para o formato MM:SS"""
        if ms < 0:
            return "00:00"
        segundos = (ms // 1000) % 60
        minutos = (ms // 1000) // 60
        return f"{minutos:02d}:{segundos:02d}"

    def formatar_tempo_segundos(self, segundos):
        """Converte segundos totais para o formato MM:SS"""
        try:
            segundos = int(segundos)
            m = segundos // 60
            s = segundos % 60
            return f"{m:02d}:{s:02d}"
        except:
            return "00:00"

    def selecionar_e_tocar_fila(self, indice):
        self.tocar_indice(indice)

    def atualizar_barra_progresso(self):
        if hasattr(self.core, 'player') and self.core.is_playing_state:
            tempo_atual = self.core.get_tempo_atual()
            duracao_total = self.core.get_duracao()
            
            if duracao_total > 0:
                self.slider_progresso.blockSignals(True)
                self.slider_progresso.setMaximum(duracao_total)
                self.slider_progresso.setValue(tempo_atual)
                self.slider_progresso.blockSignals(False)
                
                self.lbl_tempo_atual.setText(self.formatar_tempo(tempo_atual))
                self.lbl_tempo_total.setText(self.formatar_tempo(duracao_total))
                
                volume_atual_usuario = self.slider_volume.value()
                tempo_restante = duracao_total - tempo_atual

                # 1. FADE-IN INICIAL (Primeiros 10 segundos da música)
                if tempo_atual < 10000:
                    fator = tempo_atual / 10000.0
                    vol_fade = int(volume_atual_usuario * fator)
                    self.core.definir_volume_temporario(vol_fade)
                    
                # 2. DISPARAR O CROSSFADE REAL (Aos exatos 10 segundos para o fim)
                elif 10000 >= tempo_restante > 0 and self.core.indice_atual + 1 < len(self.core.fila):
                    proxima_faixa = self.core.fila[self.core.indice_atual + 1]
                    
                    # Se o player secundário ainda não estiver a tocar a próxima faixa, disparamos via worker
                    if not hasattr(self, 'crossfade_em_andamento') or not self.crossfade_em_andamento:
                        self.crossfade_em_andamento = True
                        # Busca o link da próxima faixa e inicia no player secundário
                        self.audio_worker_cross = AudioWorker(proxima_faixa['url'], proxima_faixa['title'], self.core.cache_urls)
                        self.audio_worker_cross.sucesso.connect(lambda url: self.core.iniciar_crossfade_secundario(url))
                        self.audio_worker_cross.start()

                    # Fator de progresso dos últimos 10 segundos (de 1.0 descendo até 0.0)
                    fator_fade_out = tempo_restante / 10000.0
                    fator_fade_in = 1.0 - fator_fade_out

                    # Música atual desce o volume (Fade-Out)
                    vol_atual = int(volume_atual_usuario * fator_fade_out)
                    self.core.definir_volume_temporario(vol_atual)

                    # Próxima música sobe o volume em simultâneo (Fade-In)
                    vol_proxima = int(volume_atual_usuario * fator_fade_in)
                    self.core.definir_volume_secundario(vol_proxima)
                else:
                    self.core.definir_volume_temporario(volume_atual_usuario)
                
            # Fim da faixa atual -> Conclui a transição de vez
            estado_vlc = self.core.player.get_state()
            if estado_vlc == vlc.State.Ended or (duracao_total > 0 and tempo_atual >= duracao_total - 1000):
                self.timer_progresso.stop()
                
                # Reseta a flag de crossfade
                if hasattr(self, 'crossfade_em_andamento'):
                    self.crossfade_em_andamento = False

                if self.core.indice_atual + 1 < len(self.core.fila):
                    # Promove o player secundário a principal e avança o índice interno
                    self.core.concluir_crossfade_troca()
                    self.core.indice_atual += 1
                    self.core.definir_volume(self.slider_volume.value())
                    self.atualizar_ui_fila()
                    self.lbl_status.setText(f"Reproduzindo: {self.core.fila[self.core.indice_atual]['title']}")
                    self.timer_progresso.start()
                else:
                    self.core.parar()
                    self.atualizar_icones_player()

    def ao_soltar_slider(self):
        if hasattr(self.core, 'player'):
            nova_posicao = self.slider_progresso.value()
            self.core.definir_posicao(nova_posicao)

    def acao_criar_nova_playlist(self):
        nova_pl = self.core.criar_nova_playlist()
        self.a_ver_historico = False
        self.btn_playlists.setText("PLAYLISTS")
        self.atualizar_ui_fila()
        self.lbl_status.setText(f"Criada e selecionada: {nova_pl['nome']}")

    def ativar_edicao_nome_playlist(self, event):
        """Permite editar o nome da playlist atual ao dar duplo clique no título"""
        if not self.core.playlists:
            return
            
        playlist_atual = self.core.playlists[self.core.playlist_ativa_indice]
        nome_atual = playlist_atual['nome']
        
        novo_nome, ok = QInputDialog.getText(
            self, 
            "Renomear Playlist", 
            "Introduza o novo nome da playlist:", 
            QLineEdit.EchoMode.Normal, 
            nome_atual
        )
        
        if ok and novo_nome.strip():
            novo_nome_limpo = novo_nome.strip()
            self.core.playlists[self.core.playlist_ativa_indice]['nome'] = novo_nome_limpo
            self.core.guardar_playlists_json()
            
            self.atualizar_ui_fila()
            self.lbl_status.setText(f"Playlist renomeada para: {novo_nome_limpo}")

    def alternar_visao_playlists(self):
        """Alterna entre ver a fila da playlist atual e o histórico de playlists gravadas"""
        self.a_ver_historico = not self.a_ver_historico
        if self.a_ver_historico:
            self.btn_playlists.setText("FILA")
            self.exibir_historico_playlists()
        else:
            self.btn_playlists.setText("PLAYLISTS")
            self.lbl_titulo_playlist.setText("PLAYLISTS")
            self.atualizar_ui_fila()

    def exibir_historico_playlists(self):
        """Renderiza o histórico de playlists na área da direita com indicador visual e contraste ajustado"""
        while self.layout_container_fila.count():
            item = self.layout_container_fila.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if hasattr(self, 'lbl_titulo_playlist'):
            self.lbl_titulo_playlist.setText("PLAYLISTS")
            cor_titulo = "#ffffff" if self.is_dark_theme else "#000000"
            self.lbl_titulo_playlist.setStyleSheet(f"font-weight: bold; color: {cor_titulo}; font-size: 12px; background: transparent;")

        playlists = self.core.obter_todas_playlists()
        
        for p in playlists:
            linha_widget = QWidget()
            linha_layout = QHBoxLayout(linha_widget)
            linha_layout.setContentsMargins(8, 6, 8, 6)

            is_ativa = (p['indice'] == self.core.playlist_ativa_indice)
            
            # ---> CORREÇÃO DO SINGULAR/PLURAL AQUI <---
            total_f = p['total_faixas']
            texto_faixas = "1 faixa" if total_f == 1 else f"{total_f} faixas"
            
            lbl_nome = QLabel(f"{p['nome']} ({texto_faixas})")
            # ------------------------------------------
            
            # Ajuste de cores e opacidade/contraste dependendo se está ativa ou inativa
            if is_ativa:
                cor_texto_item = "#ffffff" if self.is_dark_theme else "#000000"
                lbl_nome.setStyleSheet(f"font-weight: bold; color: {cor_texto_item}; background: transparent; border: none; font-size: 12px;")
            else:
                cor_inativa = "#a6adc8" if self.is_dark_theme else "#6e6e73"
                lbl_nome.setStyleSheet(f"font-weight: normal; color: {cor_inativa}; background: transparent; border: none; font-size: 12px;")

            # Botão de excluir
            btn_excluir_hist = QPushButton()
            btn_excluir_hist.setFixedSize(24, 24)
            btn_excluir_hist.setToolTip("Excluir esta playlist")
            
            caminho_icone_cancelar = self.obter_caminho_icone("cancelar")
            if caminho_icone_cancelar:
                btn_excluir_hist.setIcon(QIcon(caminho_icone_cancelar))
            else:
                btn_excluir_hist.setText("✕")
                
            btn_excluir_hist.setStyleSheet("""
                QPushButton { background-color: transparent; border: none; border-radius: 4px; }
                QPushButton:hover { background-color: rgba(255, 0, 0, 0.2); }
            """)
            btn_excluir_hist.clicked.connect(lambda checked, idx=p['indice']: self.solicitar_exclusao_playlist(idx))

            linha_layout.addWidget(lbl_nome, stretch=1)
            linha_layout.addWidget(btn_excluir_hist, stretch=0)

            # Estilização do fundo e do marcador visual (borda lateral esquerda destacada na ativa)
            if self.is_dark_theme:
                bg_cor = "#313244" if is_ativa else "transparent"
                hover_cor = "#45475a"
                borda_lateral = "border-left: 4px solid #89b4fa;" if is_ativa else "border-left: 4px solid transparent;"
            else:
                bg_cor = "#e2e2e6" if is_ativa else "transparent"
                hover_cor = "#eaeaea"
                borda_lateral = "border-left: 4px solid #0071e3;" if is_ativa else "border-left: 4px solid transparent;"

            linha_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {bg_cor};
                    border-radius: 4px;
                    {borda_lateral}
                }}
                QWidget:hover {{
                    background-color: {hover_cor};
                }}
            """)

            linha_widget.mousePressEvent = lambda event, idx=p['indice']: self.selecionar_playlist_historico(idx)
            self.layout_container_fila.addWidget(linha_widget)

    def selecionar_playlist_historico(self, indice):
        self.core.selecionar_playlist(indice)
        self.a_ver_historico = False
        self.btn_playlists.setText("PLAYLISTS")
        self.atualizar_ui_fila()
        pl_nome = self.core.playlists[indice]['nome']
        self.lbl_status.setText(f"Playlist selecionada: {pl_nome}")

    def solicitar_exclusao_playlist(self, indice):
        """Solicita confirmação e exclui a playlist selecionada do histórico"""
        if 0 <= indice < len(self.core.playlists):
            playlist_alvo = self.core.playlists[indice]
            nome = playlist_alvo['nome']
            
            # Caixa de diálogo de confirmação de segurança
            resposta = QMessageBox.question(
                self,
                "Confirmar Exclusão",
                f"Tem certeza de que deseja excluir permanentemente a playlist '{nome}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if resposta == QMessageBox.StandardButton.Yes:
                sucesso, mensagem = self.core.excluir_playlist(indice)
                if sucesso:
                    # Se estavamos a ver o histórico, atualiza a view do histórico
                    if self.a_ver_historico:
                        self.exibir_historico_playlists()
                    else:
                        self.atualizar_ui_fila()
                    self.lbl_status.setText(mensagem)
                else:
                    QMessageBox.warning(self, "Aviso", mensagem)

    def obter_caminho_icone(self, nome_base):
        """Retorna o caminho correto para o ícone .ico utilizando o resource_path"""
        if nome_base == "cancelar":
            caminho = resource_path(os.path.join("icons", "navegation", "cancelar.ico"))
            if os.path.exists(caminho):
                return caminho
                
        sufixo = "dark" if self.is_dark_theme else "light"
        
        if nome_base == "adicionar":
            nome_arquivo = f"adicionar_{sufixo}.ico"
        elif nome_base in ["lua_dark", "sol_light"]:
            nome_arquivo = f"{nome_base}.ico"
        else:
            nome_arquivo = f"{nome_base}.ico"

        pasta_tema = "dark_theme" if self.is_dark_theme else "light_theme"
        caminho = resource_path(os.path.join("icons", pasta_tema, nome_arquivo))
        if os.path.exists(caminho):
            return caminho
            
        return ""

    def atualizar_icones_player(self):
        sufixo = "dark" if self.is_dark_theme else "light"
        
        icon_play = self.obter_caminho_icone(f"pause_{sufixo}" if self.core.is_playing_state else f"play_{sufixo}")
        icon_voltar = self.obter_caminho_icone(f"voltar_{sufixo}")
        icon_avancar = self.obter_caminho_icone(f"avançar_{sufixo}")
        icon_repetir = self.obter_caminho_icone(f"repetir_{sufixo}")
        icon_aleatorio = self.obter_caminho_icone(f"aleatório_{sufixo}")
        
        icon_adicionar = self.obter_caminho_icone("adicionar")

        if icon_play: self.btn_play.setIcon(QIcon(icon_play))
        if icon_voltar: self.btn_prev.setIcon(QIcon(icon_voltar))
        if icon_avancar: self.btn_next.setIcon(QIcon(icon_avancar))
        if icon_repetir: self.btn_repeat.setIcon(QIcon(icon_repetir))
        if icon_aleatorio: self.btn_shuffle.setIcon(QIcon(icon_aleatorio))
        
        if icon_adicionar and hasattr(self, 'btn_nova_playlist'):
            self.btn_nova_playlist.setIcon(QIcon(icon_adicionar))
            self.btn_nova_playlist.setText("")  
        elif hasattr(self, 'btn_nova_playlist'):
            self.btn_nova_playlist.setText("+") 

        nome_icone_tema = "lua_dark" if self.is_dark_theme else "sol_light"
        caminho_tema = self.obter_caminho_icone(nome_icone_tema)
        if caminho_tema:
            self.btn_tema.setIcon(QIcon(caminho_tema))
            self.btn_tema.setText("")
        else:
            self.btn_tema.setText("🌙" if self.is_dark_theme else "☀️")

    def alternar_tema(self):
        self.is_dark_theme = not self.is_dark_theme
        self.aplicar_estilo_tema()
        self.atualizar_icones_player()
        self.atualizar_ui_fila()

    def aplicar_estilo_tema(self):
        if self.is_dark_theme:
            bg_scroll = "#181825"
            border_scroll = "#313244"
            cor_titulo = "#ffffff"  # Branco para o tema escuro
            
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI', sans-serif; }
                QLineEdit { background-color: #313244; border: 1px solid #45475a; border-radius: 6px; padding: 8px; color: #cdd6f4; }
                QPushButton { background-color: #89b4fa; color: #ffffff; font-weight: bold; border-radius: 6px; padding: 8px 12px; border: none; }
                QPushButton:hover { background-color: #b4befe; }
                QScrollArea { background-color: #181825; border: 1px solid #313244; border-radius: 6px; }
                QSlider::groove:horizontal { height: 6px; background: #45475a; border-radius: 3px; }
                QSlider::handle:horizontal { background: #89b4fa; width: 14px; margin: -4px 0; border-radius: 7px; }
            """)
        else:
            bg_scroll = "#e8e8ed"
            border_scroll = "#c5c5cb"
            cor_titulo = "#000000"  # Preto para o tema claro
            
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #f2f2f7; color: #1d1d1f; font-family: 'Segoe UI', sans-serif; }
                QLineEdit { background-color: #ffffff; border: 1px solid #c5c5cb; border-radius: 6px; padding: 8px; color: #1d1d1f; }
                QPushButton { background-color: #0071e3; color: #000000; font-weight: bold; border-radius: 6px; padding: 8px 12px; border: none; }
                QPushButton:hover { background-color: #0077ed; }
                QScrollArea { background-color: #e8e8ed; border: 1px solid #c5c5cb; border-radius: 6px; }
                QSlider::groove:horizontal { height: 6px; background: #c5c5cb; border-radius: 3px; }
                QSlider::handle:horizontal { background: #0071e3; width: 14px; margin: -4px 0; border-radius: 7px; }
            """)

        if hasattr(self, 'lbl_titulo_playlist'):
            self.lbl_titulo_playlist.setStyleSheet(f"font-weight: bold; color: {cor_titulo}; font-size: 12px; background: transparent;")

        estilo_scroll = f"QScrollArea {{ background-color: {bg_scroll}; border: 1px solid {border_scroll}; border-radius: 6px; }}"
        if hasattr(self, 'scroll_resultados'):
            self.scroll_resultados.setStyleSheet(estilo_scroll)
        if hasattr(self, 'scroll_fila'):
            self.scroll_fila.setStyleSheet(estilo_scroll)

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
            
            self.timer_progresso.start()
        except Exception as e:
            self.lbl_status.setText(f"Erro ao reproduzir no VLC: {e}")

    def formatar_tempo_total(self, segundos):
        try:
            segundos = int(segundos)
            horas = segundos // 3600
            minutos = (segundos % 3600) // 60
            if horas > 0:
                return f"{horas}h {minutos:02d}m"
            else:
                return f"{minutos} min"
        except:
            return "0 min"

    def atualizar_ui_fila(self):
        if getattr(self, 'a_ver_historico', False):
            return

        while self.layout_container_fila.count():
            item = self.layout_container_fila.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if hasattr(self, 'lbl_titulo_playlist') and self.core.playlists:
            pl_ativa = self.core.playlists[self.core.playlist_ativa_indice]
            self.lbl_titulo_playlist.setText(pl_ativa['nome'].upper())
            cor_titulo = "#ffffff" if self.is_dark_theme else "#000000"
            self.lbl_titulo_playlist.setStyleSheet(f"font-weight: bold; color: {cor_titulo}; font-size: 12px; background: transparent;")

        if self.core.fila:
            total_segundos = sum(faixa.get('duration', 0) for faixa in self.core.fila)
            texto_total = self.formatar_tempo_total(total_segundos)
            qtd_faixas = len(self.core.fila)
            
            lbl_info = QLabel(f"Fila: {qtd_faixas} {'faixa' if qtd_faixas == 1 else 'faixas'}  •  Total: {texto_total}")
            lbl_info.setStyleSheet("""
                color: #89b4fa; 
                font-weight: bold; 
                font-size: 11px; 
                padding: 6px 8px; 
                background-color: transparent;
                border-bottom: 1px solid #313244;
                margin-bottom: 4px;
            """)
            self.layout_container_fila.addWidget(lbl_info)

        for index, faixa in enumerate(self.core.fila):
            linha_widget = QWidget()
            linha_layout = QHBoxLayout(linha_widget)
            linha_layout.setContentsMargins(8, 4, 4, 4)
            linha_layout.setSpacing(10)

            prefixo = "▶ " if index == self.core.indice_atual else f"{index + 1}. "
            titulo_texto = f"{prefixo}{faixa.get('title', 'Desconhecido')}"

            lbl_titulo = QLabel(titulo_texto)
            lbl_titulo.setWordWrap(True)
            
            segundos_duracao = faixa.get('duration', 0)
            texto_duracao = self.formatar_tempo_segundos(segundos_duracao)
            
            lbl_duracao = QLabel(texto_duracao)
            lbl_duracao.setStyleSheet("color: #a6adc8; font-size: 11px;")
            
            btn_remover = QPushButton()
            btn_remover.setFixedSize(24, 24)
            btn_remover.setToolTip("Remover da fila")
            
            caminho_icone_cancelar = self.obter_caminho_icone("cancelar")
            if caminho_icone_cancelar:
                btn_remover.setIcon(QIcon(caminho_icone_cancelar))
            else:
                btn_remover.setText("✕")
                
            btn_remover.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
            """)
            
            btn_remover.clicked.connect(lambda checked, idx=index: self.remover_item_fila(idx))

            linha_layout.addWidget(lbl_titulo, stretch=1)
            linha_layout.addWidget(lbl_duracao, stretch=0)
            linha_layout.addWidget(btn_remover, stretch=0)

            is_atual = (index == self.core.indice_atual)
            if self.is_dark_theme:
                bg_cor = "#313244" if is_atual else "transparent"
                hover_cor = "#45475a"
            else:
                bg_cor = "#e2e2e6" if is_atual else "transparent"
                hover_cor = "#eaeaea"

            linha_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {bg_cor};
                    border-radius: 4px;
                }}
                QWidget:hover {{
                    background-color: {hover_cor};
                }}
            """)

            linha_widget.mousePressEvent = lambda event, idx=index: self.selecionar_e_tocar_fila(idx)
            self.layout_container_fila.addWidget(linha_widget)

    def remover_item_fila(self, indice):
        faixa = self.core.remover_da_fila(indice)
        if faixa:
            self.atualizar_ui_fila()
            self.lbl_status.setText(f"'{faixa['title']}' removida da fila.")
            if not self.core.fila:
                self.timer_progresso.stop()
                self.core.parar()
                self.atualizar_icones_player()    

    def alternar_play_pause(self):
        if not self.core.fila:
            return
        tocando = self.core.alternar_play_pause()
        self.atualizar_icones_player()
        
        if tocando:
            self.timer_progresso.start()
        else:
            self.timer_progresso.stop()

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
            self.timer_progresso.stop()
            self.core.parar()
        except Exception:
            pass
        if self.parent_home:
            self.parent_home.deiconify()
        event.accept()