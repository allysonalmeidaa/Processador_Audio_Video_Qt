import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

def get_ffmpeg_local_path():
    base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    ffmpeg_dir = os.path.join(base_dir, ".cache", "ffmpeg")
    for root, dirs, files in os.walk(ffmpeg_dir):
        if "ffmpeg.exe" in files:
            return os.path.join(root, "ffmpeg.exe")
    return None

def ffmpeg_disponivel():
    try:
        result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except Exception:
        return False

def baixar_ffmpeg(destino_base, progresso_callback=None):
    ffmpeg_dir = os.path.join(destino_base, ".cache", "ffmpeg")
    os.makedirs(ffmpeg_dir, exist_ok=True)
    zip_path = os.path.join(ffmpeg_dir, "ffmpeg.zip")
    try:
        if progresso_callback:
            progresso_callback("Baixando FFMPEG...")
        urllib.request.urlretrieve(FFMPEG_URL, zip_path)
        if progresso_callback:
            progresso_callback("Extraindo FFMPEG...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)
        os.remove(zip_path)
        for root, dirs, files in os.walk(ffmpeg_dir):
            if "ffmpeg.exe" in files:
                exe_path = os.path.join(root, "ffmpeg.exe")
                shutil.copy2(exe_path, ffmpeg_dir)
                break
        return get_ffmpeg_local_path()
    except Exception as e:
        if progresso_callback:
            progresso_callback(f"Falha ao baixar FFMPEG: {e}")
        return None

def garantir_ffmpeg(window_parent=None):
    from PyQt6.QtWidgets import QMessageBox
    import webbrowser
    if ffmpeg_disponivel():
        return "ffmpeg"
    ffmpeg_local = get_ffmpeg_local_path()
    if ffmpeg_local:
        return ffmpeg_local
    base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    def progresso(msg):
        print(msg)
    ffmpeg_baixado = baixar_ffmpeg(base_dir, progresso)
    if ffmpeg_baixado and os.path.exists(ffmpeg_baixado):
        return ffmpeg_baixado
    QMessageBox.critical(
        window_parent, "FFMPEG não encontrado",
        "O FFMPEG não foi encontrado em sua máquina e não foi possível baixá-lo automaticamente.\n"
        "Baixe o FFMPEG manualmente em: https://www.gyan.dev/ffmpeg/builds/\n"
        "Após baixar, extraia e coloque o ffmpeg.exe na mesma pasta do programa ou no PATH do Windows."
    )
    webbrowser.open("https://www.gyan.dev/ffmpeg/builds/")
    return None

def copiar_ffmpeg_para_app_dir():
    """
    Copia o ffmpeg.exe baixado para o diretório do .exe/app, se ainda não estiver lá.
    Isso garante que subprocessos, como Whisper, encontrem o ffmpeg.
    """
    ffmpeg_path = get_ffmpeg_local_path()
    if ffmpeg_path:
        app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        destino = os.path.join(app_dir, "ffmpeg.exe")
        if not os.path.exists(destino):
            try:
                shutil.copy2(ffmpeg_path, destino)
            except Exception as e:
                print(f"[WARN] Falha ao copiar ffmpeg.exe para app_dir: {e}")

def adicionar_ffmpeg_no_path():
    """
    Adiciona o diretório do ffmpeg baixado e o diretório do app ao PATH do processo,
    para garantir que pacotes como whisper encontrem o ffmpeg.
    """
    ffmpeg_path = get_ffmpeg_local_path()
    dirs_to_add = []
    if ffmpeg_path:
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        dirs_to_add.append(ffmpeg_dir)
    app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    dirs_to_add.append(app_dir)
    for dir_ in dirs_to_add:
        if dir_ not in os.environ.get("PATH", ""):
            os.environ["PATH"] = dir_ + os.pathsep + os.environ.get("PATH", "")