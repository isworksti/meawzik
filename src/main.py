import os
import sys
import customtkinter as ctk
from PIL import Image, ImageTk

from player_core import MeawZikCore
from player_ui import PlayerUI

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def resource_path(relative_path):
    """ Obtém o caminho absoluto para os recursos no PyInstaller """
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def aplicar_icone(janela):
    """Carrega e define o ícone de forma compatível usando Pillow"""
    for nome_arquivo in ["meawzik.ico", "meawzik.png"]:
        caminho = resource_path(nome_arquivo)
        if os.path.exists(caminho):
            try:
                img_pil = Image.open(caminho)
                icone_tk = ImageTk.PhotoImage(img_pil)
                janela.iconphoto(True, icone_tk)
                janela._icone_ref = icone_tk 
                break
            except Exception as e:
                print(f"[!] Erro ao carregar ícone {nome_arquivo}: {e}")

def formatar_tempo(ms):
    if ms < 0: return "00:00"
    segundos = int(ms / 1000)
    return f"{segundos // 60:02d}:{segundos % 60:02d}"

class MeawZikPlayerWindow(PlayerUI):
    def __init__(self, parent):
        super().__init__(parent, controller=self)
        self.title("MeawZik - Sessão Solo")
        self.core = MeawZikCore()
        self.atualizando_slider = False
        
        aplicar_icone(self)
        self.core.definir_volume(70)
        self.iniciar_loop_monitorizacao()

    def ao_clicar_buscar(self):
        termo = self.url_entry.get().strip()
        if not termo: return
        self.status_label.configure(text=f"Pesquisando por '{termo}'...")
        self.core.pesquisar(termo, self.sucesso_pesquisa, self.erro_pesquisa)

    def sucesso_pesquisa(self, resultados):
        self.after(0, lambda: self._atualizar_ui_pesquisa(resultados))

    def _atualizar_ui_pesquisa(self, resultados):
        # Proteção robusta contra widgets destruídos ou fecho repentino de janela
        try:
            if self.winfo_exists() and hasattr(self, 'search_box') and self.search_box.winfo_exists():
                self.search_box.delete(0, ctk.END)
                for i, item in enumerate(resultados):
                    self.search_box.insert(ctk.END, f"  {i+1}. {item['title']}")
                self.status_label.configure(text=f"{len(resultados)} resultados encontrados.")
        except Exception:
            pass

    def erro_pesquisa(self, erro_msg):
        try:
            if self.winfo_exists():
                self.after(0, lambda: self.status_label.configure(text=f"Erro: {erro_msg}"))
        except Exception:
            pass

    def adicionar_selecionada_pesquisa(self):
        selecao = self.search_box.curselection()
        if selecao:
            indice = selecao[0]
            if indice < len(self.core.resultados_pesquisa):
                faixa = self.core.resultados_pesquisa[indice]
                self.core.adicionar_a_fila(faixa)
                self.atualizar_ui_fila()
                self.status_label.configure(text=f"'{faixa['title']}' adicionada à fila!")
                if len(self.core.fila) == 1:
                    self.core.tocar_faixa(0, self.ao_iniciar_tocar, self.erro_pesquisa)

    def atualizar_ui_fila(self):
        try:
            if self.winfo_exists() and hasattr(self, 'playlist_box') and self.playlist_box.winfo_exists():
                self.playlist_box.delete(0, ctk.END)
                for i, faixa in enumerate(self.core.fila):
                    prefixo = "▶ " if i == self.core.indice_atual else "  "
                    self.playlist_box.insert(ctk.END, f"{prefixo}{i+1}. {faixa['title']}")
                total = len(self.core.fila)
                self.fila_titulo_label.configure(text=f"🎵 Fila de Reprodução ({total} {'item' if total == 1 else 'itens'})")
        except Exception:
            pass

    def tocar_da_fila(self):
        selecao = self.playlist_box.curselection()
        if selecao:
            self.core.tocar_faixa(selecao[0], self.ao_iniciar_tocar, self.erro_pesquisa)

    def ao_iniciar_tocar(self, titulo, indice):
        def atualizar():
            try:
                if self.winfo_exists():
                    self.status_label.configure(text=f"Reproduzindo: {titulo}")
                    self.play_pause_btn.configure(text="||")
                    self.atualizar_ui_fila()
                    self.playlist_box.selection_clear(0, ctk.END)
                    self.playlist_box.selection_set(indice)
                    self.playlist_box.activate(indice)
            except Exception:
                pass
        self.after(0, atualizar)

    def clicar_anterior(self): self.core.anterior(self.ao_iniciar_tocar, self.erro_pesquisa)
    def clicar_proximo(self): self.core.proximo(self.ao_iniciar_tocar, self.erro_pesquisa)

    def alternar_play_pause(self):
        if not self.core.fila: return
        tocando = self.core.alternar_play_pause()
        self.play_pause_btn.configure(text="||" if tocando else ">")

    def ao_ajustar_slider(self, valor):
        if self.atualizando_slider: return
        duracao = self.core.get_duracao()
        if duracao > 0: self.core.definir_posicao((valor / 100.0) * duracao)

    def ao_ajustar_volume(self, valor):
        self.core.definir_volume(valor)

    def iniciar_loop_monitorizacao(self):
        def atualizar():
            try:
                if self.winfo_exists():
                    if self.core.is_playing_state:
                        duracao = self.core.get_duracao()
                        atual = self.core.get_tempo_atual()
                        if duracao > 0:
                            self.tempo_atual_label.configure(text=formatar_tempo(atual))
                            self.tempo_total_label.configure(text=formatar_tempo(duracao))
                            self.atualizando_slider = True
                            self.slider_progresso.set((atual / duracao) * 100)
                            self.atualizando_slider = False
                    if self.core.verificar_fim_musica():
                        if not self.core.proximo(self.ao_iniciar_tocar, self.erro_pesquisa):
                            self.play_pause_btn.configure(text=">")
                    self.after(500, atualizar)
            except Exception:
                pass
        self.after(500, atualizar)
    def clicar_shuffle(self):
        ativo = self.core.alternar_shuffle()
        cor = "#4ea1f3" if ativo else self.btn_bg
        self.btn_shuffle.configure(fg_color=cor)
        self.status_label.configure(text=f"Modo Aleatório: {'Ativado' if ativo else 'Desativado'}")

    def clicar_repeat(self):
        ativo = self.core.alternar_repeat()
        cor = "#4ea1f3" if ativo else self.btn_bg
        self.btn_repeat.configure(fg_color=cor)
        self.status_label.configure(text=f"Modo Repetição: {'Ativado' if ativo else 'Desativado'}")

class MeawZikHome(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MeawZik - Início")
        self.geometry("400x300")
        self.resizable(False, False)

        aplicar_icone(self)

        self.label_titulo = ctk.CTkLabel(self, text="🎵 MeawZik", font=("Segoe UI", 24, "bold"))
        self.label_titulo.pack(pady=(40, 20))

        self.label_sub = ctk.CTkLabel(self, text="Escolha o modo de reprodução", font=("Segoe UI", 12), text_color="gray")
        self.label_sub.pack(pady=(5, 20))

        self.btn_solo = ctk.CTkButton(self, text="🎧 Sessão Solo", width=220, height=40, font=("Segoe UI", 14), command=self.abrir_solo)
        self.btn_solo.pack(pady=10)

    def abrir_solo(self):
        self.withdraw()
        player_janela = MeawZikPlayerWindow(self)
        player_janela.protocol("WM_DELETE_WINDOW", lambda: self.fechar_player(player_janela))

    def fechar_player(self, janela_player):
        janela_player.destroy()
        self.deiconify()

if __name__ == "__main__":
    app = MeawZikHome()
    app.mainloop()