import os
import sys
import subprocess
import yt_dlp
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox

from erros_usuario import registrar_erro_usuario
from ffmpeg_utils import garantir_ffmpeg
from logs_tab import adicionar_log

# --- CENTRALIZAÇÃO DOS ARQUIVOS NA PASTA DO APP ---
def get_app_dir():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.join(base_dir, "ProcessadorDeAudioVideo")
    if not os.path.exists(app_dir):
        os.makedirs(app_dir, exist_ok=True)
    return app_dir

def log_erro(msg):
    app_dir = get_app_dir()
    log_path = os.path.join(app_dir, "erros.log")
    if "DEBUG" not in msg:
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
        except Exception as e:
            print(f"[LOG ERROR] Falha ao salvar log: {e}")
    adicionar_log(msg)

def criar_diretorio_saida():
    app_dir = get_app_dir()
    diretorio_saida = os.path.join(app_dir, "saida_audio")
    if not os.path.exists(diretorio_saida):
        os.makedirs(diretorio_saida, exist_ok=True)
        adicionar_log(f"Diretório de saída criado: {diretorio_saida}")
    return diretorio_saida

def verifica_arquivo_local(caminho):
    caminho = caminho.strip('"\'')
    return os.path.isfile(caminho)

def verifica_url(texto):
    return texto.strip('"\'').startswith(('http://', 'https://', 'www.'))

def nome_base_entrada(origem):
    if os.path.isfile(origem):
        return os.path.splitext(os.path.basename(origem))[0]
    elif verifica_url(origem):
        return None
    else:
        return "arquivo"

def baixar_do_youtube(url, caminho_saida, parent_widget=None):
    try:
        adicionar_log(f"Iniciando download do YouTube: {url}")
        if not os.path.exists(caminho_saida):
            os.makedirs(caminho_saida, exist_ok=True)
            adicionar_log(f"Diretório de saída criado: {caminho_saida}")
        opcoes_ydl = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
            'outtmpl': os.path.join(caminho_saida, "video_%(title)s.%(ext)s"),
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'prefer_ffmpeg': True,
            'verbose': False,
        }
        with yt_dlp.YoutubeDL(opcoes_ydl) as ydl:
            info = ydl.extract_info(url, download=True)
            caminho_video = ydl.prepare_filename(info)
            titulo = info.get('title') or 'youtube'
            nome_base = titulo.replace(" ", "_")
            caminho_final = os.path.join(os.path.dirname(caminho_video), f"video_{nome_base}.mp4")
            if os.path.exists(caminho_final):
                try:
                    os.remove(caminho_final)
                    adicionar_log(f"Arquivo existente removido: {caminho_final}")
                except Exception as e:
                    log_erro(f"Erro ao remover arquivo existente: {e}")
                    registrar_erro_usuario("Conversão", f"Erro ao remover arquivo existente: {e}")
                    return None, None
            if not os.path.exists(caminho_video):
                base_dir = os.path.dirname(caminho_video)
                nome_base_file = os.path.splitext(os.path.basename(caminho_video))[0]
                for ext in ['.mp4', '.webm', '.mkv']:
                    alt_path = os.path.join(base_dir, nome_base_file + ext)
                    if os.path.exists(alt_path):
                        caminho_video = alt_path
                        break
            if caminho_video != caminho_final and os.path.exists(caminho_video):
                os.rename(caminho_video, caminho_final)
                adicionar_log(f"Arquivo baixado renomeado: {caminho_final}")
            adicionar_log(f"Download do YouTube finalizado: {caminho_final}")
            return caminho_final, nome_base
    except Exception as e:
        msg = f"Erro ao baixar do YouTube: {str(e)}"
        log_erro(msg)
        registrar_erro_usuario("Conversão", "Erro ao baixar vídeo do YouTube. Verifique se o link é válido ou tente novamente mais tarde.")
        if parent_widget:
            QMessageBox.critical(parent_widget, "Erro download YouTube", msg)
        else:
            print(msg)
        return None, None

def gerar_mp4(caminho_origem, caminho_saida, nome_base, parent_widget=None):
    try:
        destino = os.path.join(caminho_saida, f"video_{nome_base}.mp4")
        if os.path.exists(destino):
            os.remove(destino)
        ffmpeg_cmd = garantir_ffmpeg(window_parent=parent_widget)
        if not ffmpeg_cmd:
            adicionar_log("FFmpeg não encontrado na geração do MP4.")
            return None
        comando = [
            ffmpeg_cmd,
            '-i', caminho_origem,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-y',
            destino
        ]
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        processo = subprocess.run(
            comando,
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            startupinfo=startupinfo
        )
        if processo.returncode == 0 and os.path.exists(destino):
            adicionar_log(f"MP4 gerado: {destino}")
            return destino
        else:
            adicionar_log(f"Falha ao gerar MP4: {processo.stderr}")
            return None
    except Exception as e:
        adicionar_log(f"Erro ao gerar MP4: {e}")
        return None

def gerar_mp3(caminho_video, caminho_saida, nome_base, parent_widget=None):
    try:
        caminho_audio = os.path.join(caminho_saida, f"audio_{nome_base}.mp3")
        if os.path.exists(caminho_audio):
            os.remove(caminho_audio)
        ffmpeg_cmd = garantir_ffmpeg(window_parent=parent_widget)
        if not ffmpeg_cmd:
            adicionar_log("FFmpeg não encontrado na extração do MP3.")
            return None
        comando = [
            ffmpeg_cmd,
            '-i', caminho_video,
            '-vn',
            '-acodec', 'libmp3lame',
            '-ab', '192k',
            '-ar', '44100',
            '-af', 'volume=2.0',
            '-y',
            caminho_audio
        ]
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        processo = subprocess.run(
            comando,
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            startupinfo=startupinfo
        )
        if processo.returncode == 0 and os.path.exists(caminho_audio):
            adicionar_log(f"MP3 extraído: {caminho_audio}")
            return caminho_audio
        else:
            adicionar_log(f"Falha ao gerar MP3: {processo.stderr}")
            return None
    except Exception as e:
        adicionar_log(f"Erro ao gerar MP3: {e}")
        return None

def converter_generico(cmd_args, output_path, log_success, log_fail, parent_widget=None):
    try:
        if os.path.exists(output_path):
            os.remove(output_path)
            adicionar_log(f"Arquivo existente removido: {output_path}")
        ffmpeg_cmd = garantir_ffmpeg(window_parent=parent_widget)
        if not ffmpeg_cmd:
            adicionar_log("FFmpeg não encontrado na conversão.")
            return None
        comando = [ffmpeg_cmd] + cmd_args + ['-y', output_path]
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        processo = subprocess.run(
            comando, capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            startupinfo=startupinfo
        )
        if processo.returncode == 0 and os.path.exists(output_path):
            adicionar_log(log_success.format(output_path))
            return output_path
        else:
            adicionar_log(log_fail + f": {processo.stderr}")
            return None
    except Exception as e:
        adicionar_log(f"{log_fail}: {e}")
        return None

def converter_para_telefonia(caminho_audio, caminho_saida, nome_base, parent_widget=None):
    output_path = os.path.join(caminho_saida, f"telefonia_{nome_base}.wav")
    cmd_args = [
        '-i', caminho_audio, '-ar', '8000', '-ac', '1', '-acodec', 'pcm_s16le',
        '-af', 'volume=3.0,highpass=f=300,lowpass=f=3400'
    ]
    return converter_generico(cmd_args, output_path,
        "Áudio convertido para telefonia: {}",
        "Falha na conversão telefônica",
        parent_widget)

def converter_para_alta_qualidade(caminho_audio, caminho_saida, nome_base, parent_widget=None):
    output_path = os.path.join(caminho_saida, f"hq_{nome_base}.flac")
    cmd_args = [
        '-i', caminho_audio, '-c:a', 'flac', '-ar', '96000', '-bits_per_raw_sample', '24'
    ]
    return converter_generico(cmd_args, output_path,
        "Áudio convertido para alta qualidade: {}",
        "Falha na conversão para alta qualidade",
        parent_widget)

def converter_para_podcast(caminho_audio, caminho_saida, nome_base, parent_widget=None):
    output_path = os.path.join(caminho_saida, f"podcast_{nome_base}.m4a")
    cmd_args = [
        '-i', caminho_audio, '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-af', 'loudnorm'
    ]
    return converter_generico(cmd_args, output_path,
        "Áudio convertido para podcast: {}",
        "Falha na conversão para podcast",
        parent_widget)

def converter_para_streaming(caminho_audio, caminho_saida, nome_base, parent_widget=None):
    output_path = os.path.join(caminho_saida, f"stream_{nome_base}.ogg")
    cmd_args = [
        '-i', caminho_audio, '-c:a', 'libvorbis', '-q:a', '6', '-ar', '48000'
    ]
    return converter_generico(cmd_args, output_path,
        "Áudio convertido para streaming: {}",
        "Falha na conversão para streaming",
        parent_widget)

def converter_para_radio(caminho_audio, caminho_saida, nome_base, parent_widget=None):
    output_path = os.path.join(caminho_saida, f"radio_{nome_base}.wav")
    cmd_args = [
        '-i', caminho_audio, '-ar', '44100', '-ac', '2', '-acodec', 'pcm_s16le',
        '-af', 'acompressor=threshold=-16dB:ratio=4,volume=2'
    ]
    return converter_generico(cmd_args, output_path,
        "Áudio convertido para rádio: {}",
        "Falha na conversão para rádio",
        parent_widget)

def converter_para_whatsapp(caminho_audio, caminho_saida, nome_base, parent_widget=None):
    output_path = os.path.join(caminho_saida, f"whatsapp_{nome_base}.ogg")
    cmd_args = [
        '-i', caminho_audio, '-c:a', 'libopus', '-b:a', '128k', '-ar', '48000', '-af', 'volume=1.5'
    ]
    return converter_generico(cmd_args, output_path,
        "Áudio convertido para WhatsApp: {}",
        "Falha na conversão para WhatsApp",
        parent_widget)

def processar_video(origem, diretorio_saida, formatos_selecionados, parent_widget=None):
    ffmpeg_cmd = garantir_ffmpeg(window_parent=parent_widget)
    if not ffmpeg_cmd:
        adicionar_log("FFmpeg não encontrado ao iniciar processamento de vídeo.")
        return None, None

    if verifica_arquivo_local(origem):
        nome_base = nome_base_entrada(origem)
        caminho_video = origem
    elif verifica_url(origem):
        caminho_video, nome_base = baixar_do_youtube(origem, diretorio_saida, parent_widget=parent_widget)
        if not caminho_video:
            return None, None
    else:
        adicionar_log("Fonte inválida. Forneça uma URL válida ou caminho de arquivo local.")
        return None, None

    arquivos_gerados = []

    ordem_formatos = [
        "1", # MP4
        "2", # MP3
        "3", # Telefonia
        "4", # Alta Qualidade
        "5", # Podcast
        "6", # Streaming
        "7", # Rádio
        "8"  # WhatsApp
    ]
    for fmt in ordem_formatos:
        if fmt not in formatos_selecionados:
            continue
        if fmt == "1":
            if caminho_video.lower().endswith(".mp4") and os.path.exists(caminho_video):
                arquivos_gerados.append(caminho_video)
                adicionar_log(f"Arquivo MP4 já existe: {caminho_video}")
            else:
                mp4 = gerar_mp4(caminho_video, diretorio_saida, nome_base, parent_widget=parent_widget)
                if mp4:
                    arquivos_gerados.append(mp4)
        elif fmt == "2":
            mp3 = gerar_mp3(caminho_video, diretorio_saida, nome_base, parent_widget=parent_widget)
            if mp3:
                arquivos_gerados.append(mp3)
        else:
            mp3_path = os.path.join(diretorio_saida, f"audio_{nome_base}.mp3")
            if not os.path.exists(mp3_path):
                mp3 = gerar_mp3(caminho_video, diretorio_saida, nome_base, parent_widget=parent_widget)
                if not mp3:
                    continue
            else:
                mp3 = mp3_path
            if fmt == "3":
                p = converter_para_telefonia(mp3, diretorio_saida, nome_base, parent_widget=parent_widget)
            elif fmt == "4":
                p = converter_para_alta_qualidade(mp3, diretorio_saida, nome_base, parent_widget=parent_widget)
            elif fmt == "5":
                p = converter_para_podcast(mp3, diretorio_saida, nome_base, parent_widget=parent_widget)
            elif fmt == "6":
                p = converter_para_streaming(mp3, diretorio_saida, nome_base, parent_widget=parent_widget)
            elif fmt == "7":
                p = converter_para_radio(mp3, diretorio_saida, nome_base, parent_widget=parent_widget)
            elif fmt == "8":
                p = converter_para_whatsapp(mp3, diretorio_saida, nome_base, parent_widget=parent_widget)
            else:
                p = None
            if p:
                arquivos_gerados.append(p)

    if arquivos_gerados:
        adicionar_log(f"Processamento finalizado. Arquivos gerados: {arquivos_gerados}")
    else:
        adicionar_log("Nenhum arquivo foi gerado na conversão.")

    return caminho_video, arquivos_gerados