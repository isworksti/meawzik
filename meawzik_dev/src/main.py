import sys
import os
import vlc
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QThread
from player_ui import MeawZikPlayerWindow

def main():
    app = QApplication(sys.argv)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    caminho_splash = os.path.join(base_dir, "..", "app_meawzik.png")
    caminho_sfx = os.path.join(base_dir, "..", "sfx", "meaw.mp3")

    splash = None

    # 1. Exibe a Splash Screen centralizada
    if os.path.exists(caminho_splash):
        pixmap_original = QPixmap(caminho_splash)
        pixmap_redimensionado = pixmap_original.scaled(
            600, 400,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        splash = QSplashScreen(pixmap_redimensionado, Qt.WindowType.WindowStaysOnTopHint)
        
        screen_geometry = app.primaryScreen().geometry()
        splash_geometry = splash.geometry()
        x = (screen_geometry.width() - splash_geometry.width()) // 2
        y = (screen_geometry.height() - splash_geometry.height()) // 2
        splash.move(x, y)
        
        splash.show()
        app.processEvents()

    # 2. Toca o som de abertura e aguarda o tempo exato do áudio na splash
    if os.path.exists(caminho_sfx):
        try:
            vlc_instance = vlc.Instance(['--no-video'])
            media = vlc_instance.media_new(caminho_sfx)
            sfx_player = vlc_instance.media_player_new()
            sfx_player.set_media(media)
            sfx_player.play()
            
            # Pausa breve (ex: 800ms) para o som ecoar inteiramente 
            # enquanto o utilizador vê a splashart, antes de carregar a UI pesada
            QThread.msleep(800)
        except Exception as e:
            print(f"Erro ao reproduzir som de abertura: {e}")

    # 3. Inicializa a janela principal do player
    window = MeawZikPlayerWindow()

    # 4. Finaliza a splash screen e revela a interface
    if splash:
        splash.finish(window)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()