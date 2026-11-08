import os

import sys
import vlc
import ctypes
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QScrollArea, QSlider, QLabel, QFrame
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

        caminho_icone_janela = resource_path("logo-meawzik.ico") # ou o nome correto do ficheiro do logotipo
        if os.path.exists(caminho_icone_janela):
            self.setWindowIcon(QIcon(caminho_icone_janela))
        
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
        self.input_pesquisa.setFixedHeight(38) # <--- Define uma altura fixa consistente
        self.input_pesquisa.returnPressed.connect(self.executar_pesquisa)
        
        self.btn_pesquisar = QPushButton("Pesquisar")
        self.btn_pesquisar.setFixedHeight(38) # <--- Mesma altura do input para ficarem nivelados
        self.btn_pesquisar.clicked.connect(self.executar_pesquisa)
        
        # Botão de Tema (Alternar Dark/Light)
        self.btn_tema = QPushButton("🌙")
        self.btn_tema.setToolTip("Alternar Tema Claro/Escuro")
        self.btn_tema.setFixedSize(40, 38) # <--- Mesma altura também para manter a harmonia
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

        # Configuração do QTimer para atualizar a barra de progresso fluidamente
        self.timer_progresso = QTimer(self)
        self.timer_progresso.setInterval(1000)  # Atualiza a cada 500ms
        self.timer_progresso.timeout.connect(self.atualizar_barra_progresso)
        self.slider_progresso.sliderReleased.connect(self.ao_soltar_slider)

        # Botões de Controlo do Player
        controls_layout = QHBoxLayout()
        
        # 1. Bloco esquerdo de balanceamento
        left_balancer = QWidget()
        left_balancer.setFixedWidth(130)
        
        # 2. Container central para os botões multimédia
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
        right_widget.setFixedWidth(130)

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
        """Seleciona e reproduz a faixa clicada diretamente na fila"""
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
                
            # Detetar se a música chegou ao fim de forma robusta
            estado_vlc = self.core.player.get_state()
            if estado_vlc == vlc.State.Ended or (duracao_total > 0 and tempo_atual >= duracao_total - 1000):
                self.timer_progresso.stop()
                if self.core.indice_atual + 1 < len(self.core.fila):
                    self.proxima_faixa()
                else:
                    self.core.parar()
                    self.atualizar_icones_player()

    def ao_soltar_slider(self):
        """Permite saltar para o ponto específico da música ao arrastar o slider (Seek)"""
        if hasattr(self.core, 'player'):
            nova_posicao = self.slider_progresso.value()
            self.core.definir_posicao(nova_posicao)

    def obter_caminho_icone(self, nome_base):
        """Retorna o caminho correto para o ícone .ico utilizando o resource_path"""
        if nome_base == "cancelar":
            caminho = resource_path(os.path.join("icons", "navegation", "cancelar.ico"))
            if os.path.exists(caminho):
                return caminho
                
        # Se for o ícone de tema específico, procura na pasta respetiva ou na raiz de icons
        if nome_base in ["lua_dark", "sol_light"]:
            pasta_tema = "dark_theme" if self.is_dark_theme else "light_theme"
            caminho = resource_path(os.path.join("icons", pasta_tema, f"{nome_base}.ico"))
            if os.path.exists(caminho):
                return caminho

        pasta_tema = "dark_theme" if self.is_dark_theme else "light_theme"
        caminho = resource_path(os.path.join("icons", pasta_tema, f"{nome_base}.ico"))
        if os.path.exists(caminho):
            return caminho
        return ""

    def atualizar_icones_player(self):
        """Atualiza os ícones dos botões do player e do tema com base nos ficheiros .ico"""
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

        # --- ATUALIZAÇÃO DO BOTÃO DE TEMA COM OS NOVOS ÍCONES ---
        nome_icone_tema = "lua_dark" if self.is_dark_theme else "sol_light"
        caminho_tema = self.obter_caminho_icone(nome_icone_tema)
        if caminho_tema:
            self.btn_tema.setIcon(QIcon(caminho_tema))
            self.btn_tema.setText("") # Remove o emoji de texto antigo se houver
        else:
            # Fallback de texto caso o ícone não seja encontrado
            self.btn_tema.setText("🌙" if self.is_dark_theme else "☀️")

    def alternar_tema(self):
        self.is_dark_theme = not self.is_dark_theme
        self.btn_tema.setText("🌙" if self.is_dark_theme else "☀️")
        self.aplicar_estilo_tema()
        self.atualizar_icones_player()
        self.atualizar_ui_fila()

    def aplicar_estilo_tema(self):
        if self.is_dark_theme:
            # Cores para o tema escuro
            bg_scroll = "#181825"
            border_scroll = "#313244"
            
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI', sans-serif; }
                QLineEdit { background-color: #313244; border: 1px solid #45475a; border-radius: 6px; padding: 8px; color: #cdd6f4; }
                QPushButton { background-color: #89b4fa; color: #11111b; font-weight: bold; border-radius: 6px; padding: 8px 12px; border: none; }
                QPushButton:hover { background-color: #b4befe; }
                QScrollArea { background-color: #181825; border: 1px solid #313244; border-radius: 6px; }
                QSlider::groove:horizontal { height: 6px; background: #45475a; border-radius: 3px; }
                QSlider::handle:horizontal { background: #89b4fa; width: 14px; margin: -4px 0; border-radius: 7px; }
            """)
        else:
            # Cores para o tema claro
            bg_scroll = "#ffffff"
            border_scroll = "#d2d2d7"
            
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #f5f5f7; color: #1d1d1f; font-family: 'Segoe UI', sans-serif; }
                QLineEdit { background-color: #ffffff; border: 1px solid #d2d2d7; border-radius: 6px; padding: 8px; color: #1d1d1f; }
                QPushButton { background-color: #0071e3; color: #ffffff; font-weight: bold; border-radius: 6px; padding: 8px 12px; border: none; }
                QPushButton:hover { background-color: #0077ed; }
                QScrollArea { background-color: #ffffff; border: 1px solid #d2d2d7; border-radius: 6px; }
                QSlider::groove:horizontal { height: 6px; background: #d2d2d7; border-radius: 3px; }
                QSlider::handle:horizontal { background: #0071e3; width: 14px; margin: -4px 0; border-radius: 7px; }
            """)

        # Aplica dinamicamente nas ScrollAreas de pesquisa e fila
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
            
            # Inicia o temporizador da barra de progresso
            self.timer_progresso.start()
        except Exception as e:
            self.lbl_status.setText(f"Erro ao reproduzir no VLC: {e}")

    def formatar_tempo_total(self, segundos):
        """Converte segundos totais para um formato legível (ex: 1h 25m ou 14 min)"""
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
        # Limpa o layout atual da fila
        while self.layout_container_fila.count():
            item = self.layout_container_fila.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # --- CABEÇALHO COM O TOTAL DE FAIXAS E DURAÇÃO DA FILA ---
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

        # --- RENDERIZAÇÃO DAS FAIXAS ---
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
            
            # Botão de remover item da fila (pequeno e alinhado à direita)
            btn_remover = QPushButton()
            btn_remover.setFixedSize(24, 24)
            btn_remover.setToolTip("Remover da fila")
            
            # Carrega o ícone de cancelar
            caminho_icone_cancelar = self.obter_caminho_icone("cancelar")
            if caminho_icone_cancelar:
                btn_remover.setIcon(QIcon(caminho_icone_cancelar))
            else:
                btn_remover.setText("✕") # Fallback caso o ícone não seja encontrado
                
            # Estilo discreto para o botão de remover na linha
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
            
            # Ação de clique do botão de remover
            btn_remover.clicked.connect(lambda checked, idx=index: self.remover_item_fila(idx))

            # Adiciona os elementos ao layout horizontal da linha
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

            # Clique duplo ou clique simples na linha para tocar
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
        
        # Controla o timer dependendo se está a tocar ou pausado
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