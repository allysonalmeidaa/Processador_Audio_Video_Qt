import os
import sys
import shutil
from PyQt6.QtWidgets import QMessageBox

# Importe o logger global para registrar tudo que acontece
from logs_tab import adicionar_log

def get_app_dir():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.join(base_dir, "ProcessadorDeAudioVideo")
    if not os.path.exists(app_dir):
        os.makedirs(app_dir, exist_ok=True)
    return app_dir

def garantir_ffmpeg(window_parent=None, log_callback=None):
    """
    Garante que o FFmpeg esteja disponível. Se não estiver, tenta baixar para a pasta do app.
    Retorna o caminho do executável ffmpeg.
    """
    ffmpeg_bin = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    pasta_app = get_app_dir()
    ffmpeg_path = os.path.join(pasta_app, ffmpeg_bin)

    # 1. Verifica se já existe na pasta do app
    if os.path.exists(ffmpeg_path):
        adicionar_log(f"FFmpeg encontrado na pasta do app: {ffmpeg_path}")
        return ffmpeg_path

    # 2. Verifica no PATH do sistema
    ffmpeg_global = shutil.which(ffmpeg_bin)
    if ffmpeg_global:
        adicionar_log(f"FFmpeg encontrado no PATH do sistema: {ffmpeg_global}")
        return ffmpeg_global

    # 3. Tenta baixar o ffmpeg para a pasta do app (Windows)
    if os.name == "nt":
        url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        zip_path = os.path.join(pasta_app, "ffmpeg.zip")
        try:
            import requests, zipfile
            msg = "Baixando FFmpeg..."
            if log_callback:
                log_callback(msg)
            adicionar_log(msg)
            r = requests.get(url, stream=True)
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    if member.endswith(ffmpeg_bin):
                        zip_ref.extract(member, pasta_app)
                        shutil.move(os.path.join(pasta_app, member), ffmpeg_path)
                        break
            os.remove(zip_path)
            if os.path.exists(ffmpeg_path):
                adicionar_log(f"FFmpeg baixado e instalado com sucesso em: {ffmpeg_path}")
                return ffmpeg_path
            else:
                adicionar_log("FFmpeg baixado mas não encontrado após extração.")
        except Exception as e:
            msg = f"Falha ao baixar FFmpeg: {e}\nBaixe manualmente e coloque em {pasta_app}"
            adicionar_log(msg)
            # Corrigido: sempre passar um QWidget ou None como parent!
            QMessageBox.critical(window_parent if window_parent else None, "Erro FFmpeg", msg)
            return None

    # 4. Se não conseguir, avisa
    msg = f"FFmpeg não encontrado. Baixe e coloque em: {pasta_app}"
    adicionar_log(msg)
    QMessageBox.critical(window_parent if window_parent else None, "Erro FFmpeg", msg)
    return None