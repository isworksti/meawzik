import os
import sys
import customtkinter as ctk
from PIL import Image, ImageTk
import vlc

from player_core import MeawZikCore
from player_ui import PlayerUI

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def resource_path(relative_path):
    """ Obtém o caminho absoluto para os recursos no PyInstaller e em desenvolvimento """
    try:
        # Se estiver empacotado pelo PyInstaller
        base_path = sys._MEIPASS
    except Exception:
        # Em desenvolvimento, usa o diretório atual de execução
        base_path = os.path.abspath(".")
    
    caminho = os.path.join(base_path, relative_path)
    
    # Se não encontrar no diretório atual e estivermos a desenvolver, tenta procurar na pasta acima (raiz)
    if not os.path.exists(caminho) and not hasattr(sys, '_MEIPASS'):
        caminho_raiz = os.path.join(os.path.abspath(os.path.join(base_path, "..")), relative_path)
        if os.path.exists(caminho_raiz):
            return caminho_raiz
            
    return caminho

def aplicar_icone(janela):
    """Carrega e define o ícone de forma compatível no Windows"""
    for nome_arquivo in ["logo-meawzik.ico", "logo-meawzik.png", "meawzik.ico", "meawzik.png"]:
        caminho = resource_path(nome_arquivo)
        if os.path.exists(caminho):
            try:
                # Se for um ficheiro .ico, o Windows prefere o iconbitmap (fundamental para a barra de tarefas)
                if caminho.lower().endswith(".ico"):
                    janela.iconbitmap(caminho)
                    break
                else:
                    # Se for PNG, usa o iconphoto
                    img_pil = Image.open(caminho)
                    icone_tk = ImageTk.PhotoImage(img_pil)
                    janela.iconphoto(True, icone_tk)
                    janela._icone_ref = icone_tk 
                    print(f"[+] Ícone PNG aplicado com sucesso via iconphoto: {caminho}")
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
        aplicar_icone(self)
        self.title("MeawZik")
        self.core = MeawZikCore()
        self.atualizando_slider = False
        self.core.definir_volume(70)
        self.iniciar_loop_monitorizacao()
        self.protocol("WM_DELETE_WINDOW", self.ao_fechar_player)

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

    def remover_da_fila(self):
        """Remove a faixa selecionada da fila de reprodução através de duplo clique"""
        try:
            selecao = self.playlist_box.curselection()
            if selecao:
                indice = selecao[0]
                if indice < len(self.core.fila):
                    faixa_removida = self.core.fila[indice]
                    
                    # Se a música que está a tocar atualmente for a que vai ser removida, paramos o player
                    if indice == self.core.indice_atual:
                        self.core.parar()
                        self.atualizar_icone_play_pause(False)
                        self.status_label.configure(text="Reprodução interrompida (faixa removida).")
                    
                    del self.core.fila[indice]
                    
                    if indice < self.core.indice_atual:
                        self.core.indice_atual -= 1
                    
                    self.atualizar_ui_fila()
                    self.status_label.configure(text=f"'{faixa_removida['title']}' removida da fila.")
        except Exception as e:
            print(f"[!] Erro ao remover da fila: {e}")

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

    def ao_fechar_player(self):
        """Interrompe a música imediatamente e fecha o player, regressando à home"""
        try:
            if hasattr(self, 'core') and self.core:
                self.core.parar()
        except Exception as e:
            print(f"[!] Erro ao parar o core ao fechar: {e}")
        
        parent = self.master
        self.destroy()
        if parent:
            parent.deiconify()

    def tocar_da_fila(self):
        selecao = self.playlist_box.curselection()
        if selecao:
            self.core.tocar_faixa(selecao[0], self.ao_iniciar_tocar, self.erro_pesquisa)

    def ao_iniciar_tocar(self, titulo, indice):
        def atualizar():
            try:
                if self.winfo_exists():
                    self.status_label.configure(text=f"Reproduzindo: {titulo}")
                    self.atualizar_icone_play_pause(True) # Atualiza para ícone de Pause
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
        self.atualizar_icone_play_pause(tocando) # Alterna a imagem com base no estado

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
                            self.atualizar_icone_play_pause(False) # Atualiza para ícone de Play quando a fila termina
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
        self.title("MeawZik")
        self.geometry("400x300")
        self.resizable(False, False)

        aplicar_icone(self)

        # Toca o som de abertura "meaw.mp3" ao iniciar o programa
        self.tocar_som_abertura()

        # Carrega a imagem utilizando a função resource_path para funcionar também no executável do PyInstaller
        caminho_logo = resource_path("app_meawzik.png")
        
        # Abre com Pillow e define o tamanho pretendido
        img_pil = Image.open(caminho_logo)
        self.logo_img = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(140, 120))

        # Cria a label usando o parâmetro 'image' em vez de 'text'
        self.label_titulo = ctk.CTkLabel(self, text="", image=self.logo_img)
        self.label_titulo.pack(pady=(30, 10))
        
        self.label_sub = ctk.CTkLabel(self, text="Escolha o modo de reprodução", font=("Segoe UI", 12), text_color="gray")
        self.label_sub.pack(pady=(5, 20))

        self.btn_solo = ctk.CTkButton(self, text="🎧 Sessão Solo", width=220, height=40, font=("Segoe UI", 14), command=self.abrir_solo)
        self.btn_solo.pack(pady=10)

    def tocar_som_abertura(self):
        """Carrega e reproduz o ficheiro meaw.mp3 no arranque"""
        try:
            caminho_audio = resource_path("meaw.mp3")
            if os.path.exists(caminho_audio):
                self.vlc_instancia_som = vlc.Instance('--no-video')
                self.som_player = self.vlc_instancia_som.media_player_new()
                media = self.vlc_instancia_som.media_new(caminho_audio)
                self.som_player.set_media(media)
                self.som_player.play()
            else:
                print(f"[!] Ficheiro de som não encontrado em: {caminho_audio}")
        except Exception as e:
            print(f"[!] Erro ao reproduzir som de abertura: {e}")

    def abrir_solo(self):
        self.withdraw()
        MeawZikPlayerWindow(self)

if __name__ == "__main__":
    app = MeawZikHome()
    app.mainloop()