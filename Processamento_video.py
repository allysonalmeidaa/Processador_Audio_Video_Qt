import os
import sys
import subprocess
import yt_dlp
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox

from erros_usuario import registrar_erro_usuario
from ffmpeg_utils import garantir_ffmpeg

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def log_erro(msg):
    app_dir = get_app_dir()
    log_path = os.path.join(app_dir, "erros.log")
    if "DEBUG" not in msg:
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
        except Exception as e:
            print(f"[LOG ERROR] Falha ao salvar log: {e}")

def criar_diretorio_saida():
    app_dir = get_app_dir()
    diretorio_saida = os.path.join(app_dir, "saida_audio")
    if not os.path.exists(diretorio_saida):
        os.makedirs(diretorio_saida, exist_ok=True)
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

def processar_video_local(caminho_origem, caminho_saida, nome_base, parent_widget=None):
    try:
        caminho_origem = caminho_origem.strip('"\'')
        if not os.path.exists(caminho_origem):
            msg = f"Erro: Arquivo não encontrado: {caminho_origem}"
            log_erro(msg)
            registrar_erro_usuario("Conversão", "Arquivo de entrada não encontrado. Verifique o caminho informado.")
            return None

        destino = os.path.join(caminho_saida, f"video_{nome_base}.mp4")
        if os.path.exists(destino):
            try:
                os.remove(destino)
            except Exception as e:
                log_erro(f"Erro ao remover arquivo existente: {e}")
                registrar_erro_usuario("Conversão", f"Erro ao remover arquivo existente: {e}")
                return None

        ffmpeg_cmd = garantir_ffmpeg(window_parent=parent_widget)
        if not ffmpeg_cmd:
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

        processo = subprocess.run(
            comando,
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if processo.returncode == 0 and os.path.exists(destino):
            return destino
        else:
            msg = f"Erro ao processar vídeo: {processo.stderr}"
            log_erro(msg)
            registrar_erro_usuario("Conversão", "Falha ao converter vídeo. Verifique se o FFmpeg está instalado corretamente.")
            return None

    except Exception as e:
        msg = f"Erro ao processar arquivo local: {str(e)}"
        log_erro(msg)
        registrar_erro_usuario("Conversão", "Erro inesperado ao processar arquivo local.")
        return None

def baixar_do_youtube(url, caminho_saida, parent_widget=None):
    try:
        print(f"[DEBUG] Baixar YouTube: url={url}, saida={caminho_saida}")
        if not os.path.exists(caminho_saida):
            os.makedirs(caminho_saida, exist_ok=True)
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
            print(f"[DEBUG] Caminho baixado: {caminho_video}")
            titulo = info.get('title') or 'youtube'
            nome_base = titulo.replace(" ", "_")
            caminho_final = os.path.join(os.path.dirname(caminho_video), f"video_{nome_base}.mp4")
            if os.path.exists(caminho_final):
                try:
                    os.remove(caminho_final)
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

def extrair_audio(caminho_video, caminho_saida, nome_base, parent_widget=None):
    try:
        caminho_audio = os.path.join(caminho_saida, f"audio_{nome_base}.mp3")
        if os.path.exists(caminho_audio):
            try:
                os.remove(caminho_audio)
            except Exception as e:
                log_erro(f"Erro ao remover arquivo existente: {e}")
                registrar_erro_usuario("Conversão", f"Erro ao remover arquivo existente: {e}")
                return None

        ffmpeg_cmd = garantir_ffmpeg(window_parent=parent_widget)
        if not ffmpeg_cmd:
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
        processo = subprocess.run(
            comando,
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if processo.returncode == 0 and os.path.exists(caminho_audio):
            if os.path.getsize(caminho_audio) > 0:
                return caminho_audio
            else:
                msg = "Erro: Arquivo de áudio gerado está vazio"
                log_erro(msg)
                registrar_erro_usuario("Conversão", "O arquivo de áudio gerado está vazio. Verifique o arquivo de entrada.")
                return None
        else:
            msg = f"Erro ao extrair áudio: {processo.stderr}"
            log_erro(msg)
            registrar_erro_usuario("Conversão", "Falha ao extrair áudio. Verifique o FFmpeg e o arquivo de entrada.")
            return None

    except Exception as e:
        msg = f"Erro ao extrair áudio: {str(e)}"
        log_erro(msg)
        registrar_erro_usuario("Conversão", "Erro inesperado ao extrair áudio.")
        return None

def converter_para_telefonia(caminho_audio, caminho_saida, nome_base, parent_widget=None):
    try:
        caminho_telefonia = os.path.join(caminho_saida, f"telefonia_{nome_base}.wav")
        if os.path.exists(caminho_telefonia):
            try:
                os.remove(caminho_telefonia)
            except Exception as e:
                log_erro(f"Erro ao remover arquivo existente: {e}")
                registrar_erro_usuario("Conversão", f"Erro ao remover arquivo existente: {e}")
                return None

        ffmpeg_cmd = garantir_ffmpeg(window_parent=parent_widget)
        if not ffmpeg_cmd:
            return None

        comando = [
            ffmpeg_cmd,
            '-i', caminho_audio,
            '-ar', '8000',
            '-ac', '1',
            '-acodec', 'pcm_s16le',
            '-af', 'volume=3.0,highpass=f=300,lowpass=f=3400',
            '-y',
            caminho_telefonia
        ]
        processo = subprocess.run(
            comando,
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if processo.returncode == 0 and os.path.exists(caminho_telefonia):
            if os.path.getsize(caminho_telefonia) > 0:
                return caminho_telefonia
            else:
                msg = "Erro: Arquivo de áudio telefônico gerado está vazio"
                log_erro(msg)
                registrar_erro_usuario("Conversão", "Arquivo de áudio telefônico gerado está vazio.")
                return None
        else:
            msg = f"Erro na conversão telefônica: {processo.stderr}"
            log_erro(msg)
            registrar_erro_usuario("Conversão", "Falha na conversão telefônica. Verifique o arquivo de entrada e o FFmpeg.")
            return None
    except Exception as e:
        msg = f"Erro na conversão telefônica: {str(e)}"
        log_erro(msg)
        registrar_erro_usuario("Conversão", "Erro inesperado na conversão telefônica.")
        return None

def converter_para_alta_qualidade(caminho_audio, caminho_saida, nome_base, parent_widget=None):
    try:
        caminho_hq = os.path.join(caminho_saida, f"hq_{nome_base}.flac")
        if os.path.exists(caminho_hq):
            try:
                os.remove(caminho_hq)
            except Exception as e:
                log_erro(f"Erro ao remover arquivo existente: {e}")
                registrar_erro_usuario("Conversão", f"Erro ao remover arquivo existente: {e}")
                return None

        ffmpeg_cmd = garantir_ffmpeg(window_parent=parent_widget)
        if not ffmpeg_cmd:
            return None

        comando = [
            ffmpeg_cmd,
            '-i', caminho_audio,
            '-c:a', 'flac',
            '-ar', '96000',
            '-bits_per_raw_sample', '24',
            '-y',
            caminho_hq
        ]
        processo = subprocess.run(
            comando,
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if processo.returncode == 0 and os.path.exists(caminho_hq):
            return caminho_hq
        else:
            log_erro(f"Erro na conversão HQ: {processo.stderr}")
            registrar_erro_usuario("Conversão", "Falha na conversão para alta qualidade (FLAC).")
            return None
    except Exception as e:
        msg = f"Erro na conversão HQ: {str(e)}"
        log_erro(msg)
        registrar_erro_usuario("Conversão", "Erro inesperado na conversão HQ.")
        return None

def converter_para_podcast(caminho_audio, caminho_saida, nome_base, parent_widget=None):
    try:
        caminho_podcast = os.path.join(caminho_saida, f"podcast_{nome_base}.m4a")
        if os.path.exists(caminho_podcast):
            try:
                os.remove(caminho_podcast)
            except Exception as e:
                log_erro(f"Erro ao remover arquivo existente: {e}")
                registrar_erro_usuario("Conversão", f"Erro ao remover arquivo existente: {e}")
                return None

        ffmpeg_cmd = garantir_ffmpeg(window_parent=parent_widget)
        if not ffmpeg_cmd:
            return None

        comando = [
            ffmpeg_cmd,
            '-i', caminho_audio,
            '-c:a', 'aac',
            '-b:a', '192k',
            '-ar', '44100',
            '-af', 'loudnorm',
            '-y',
            caminho_podcast
        ]
        processo = subprocess.run(
            comando,
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if processo.returncode == 0 and os.path.exists(caminho_podcast):
            return caminho_podcast
        else:
            log_erro(f"Erro na conversão podcast: {processo.stderr}")
            registrar_erro_usuario("Conversão", "Falha na conversão para podcast (M4A).")
            return None
    except Exception as e:
        msg = f"Erro na conversão podcast: {str(e)}"
        log_erro(msg)
        registrar_erro_usuario("Conversão", "Erro inesperado na conversão podcast.")
        return None

def converter_para_streaming(caminho_audio, caminho_saida, nome_base, parent_widget=None):
    try:
        caminho_stream = os.path.join(caminho_saida, f"stream_{nome_base}.ogg")
        if os.path.exists(caminho_stream):
            try:
                os.remove(caminho_stream)
            except Exception as e:
                log_erro(f"Erro ao remover arquivo existente: {e}")
                registrar_erro_usuario("Conversão", f"Erro ao remover arquivo existente: {e}")
                return None

        ffmpeg_cmd = garantir_ffmpeg(window_parent=parent_widget)
        if not ffmpeg_cmd:
            return None

        comando = [
            ffmpeg_cmd,
            '-i', caminho_audio,
            '-c:a', 'libvorbis',
            '-q:a', '6',
            '-ar', '48000',
            '-y',
            caminho_stream
        ]
        processo = subprocess.run(
            comando,
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if processo.returncode == 0 and os.path.exists(caminho_stream):
            return caminho_stream
        else:
            log_erro(f"Erro na conversão streaming: {processo.stderr}")
            registrar_erro_usuario("Conversão", "Falha na conversão para streaming (OGG).")
            return None
    except Exception as e:
        msg = f"Erro na conversão streaming: {str(e)}"
        log_erro(msg)
        registrar_erro_usuario("Conversão", "Erro inesperado na conversão streaming.")
        return None

def converter_para_radio(caminho_audio, caminho_saida, nome_base, parent_widget=None):
    try:
        caminho_radio = os.path.join(caminho_saida, f"radio_{nome_base}.wav")
        if os.path.exists(caminho_radio):
            try:
                os.remove(caminho_radio)
            except Exception as e:
                log_erro(f"Erro ao remover arquivo existente: {e}")
                registrar_erro_usuario("Conversão", f"Erro ao remover arquivo existente: {e}")
                return None

        ffmpeg_cmd = garantir_ffmpeg(window_parent=parent_widget)
        if not ffmpeg_cmd:
            return None

        comando = [
            ffmpeg_cmd,
            '-i', caminho_audio,
            '-ar', '44100',
            '-ac', '2',
            '-acodec', 'pcm_s16le',
            '-af', 'acompressor=threshold=-16dB:ratio=4,volume=2',
            '-y',
            caminho_radio
        ]
        processo = subprocess.run(
            comando,
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if processo.returncode == 0 and os.path.exists(caminho_radio):
            return caminho_radio
        else:
            log_erro(f"Erro na conversão rádio: {processo.stderr}")
            registrar_erro_usuario("Conversão", "Falha na conversão para rádio (WAV).")
            return None
    except Exception as e:
        msg = f"Erro na conversão rádio: {str(e)}"
        log_erro(msg)
        registrar_erro_usuario("Conversão", "Erro inesperado na conversão rádio.")
        return None

def converter_para_whatsapp(caminho_audio, caminho_saida, nome_base, parent_widget=None):
    try:
        caminho_whatsapp = os.path.join(caminho_saida, f"whatsapp_{nome_base}.ogg")
        if os.path.exists(caminho_whatsapp):
            try:
                os.remove(caminho_whatsapp)
            except Exception as e:
                log_erro(f"Erro ao remover arquivo existente: {e}")
                registrar_erro_usuario("Conversão", f"Erro ao remover arquivo existente: {e}")
                return None

        ffmpeg_cmd = garantir_ffmpeg(window_parent=parent_widget)
        if not ffmpeg_cmd:
            return None

        comando = [
            ffmpeg_cmd,
            '-i', caminho_audio,
            '-c:a', 'libopus',
            '-b:a', '128k',
            '-ar', '48000',
            '-af', 'volume=1.5',
            '-y',
            caminho_whatsapp
        ]
        processo = subprocess.run(
            comando,
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if processo.returncode == 0 and os.path.exists(caminho_whatsapp):
            return caminho_whatsapp
        else:
            log_erro(f"Erro na conversão WhatsApp: {processo.stderr}")
            registrar_erro_usuario("Conversão", "Falha na conversão para WhatsApp (OGG/OPUS).")
            return None
    except Exception as e:
        msg = f"Erro na conversão WhatsApp: {str(e)}"
        log_erro(msg)
        registrar_erro_usuario("Conversão", "Erro inesperado na conversão WhatsApp.")
        return None

def processar_video(origem, diretorio_saida, formatos_selecionados, parent_widget=None):
    ffmpeg_cmd = garantir_ffmpeg(window_parent=parent_widget)
    if not ffmpeg_cmd:
        return None, None

    try:
        subprocess.run([ffmpeg_cmd, '-version'], capture_output=True, check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    except Exception:
        msg = "Erro: FFmpeg não está instalado ou não está acessível!"
        log_erro(msg)
        registrar_erro_usuario("Conversão", "FFmpeg não está instalado ou acessível no sistema.")
        if parent_widget:
            QMessageBox.critical(parent_widget, "Erro FFmpeg", msg)
        else:
            print(msg)
        return None, None

    if verifica_arquivo_local(origem):
        nome_base = nome_base_entrada(origem)
        caminho_video = processar_video_local(origem, diretorio_saida, nome_base, parent_widget=parent_widget)
    elif verifica_url(origem):
        caminho_video, nome_base = baixar_do_youtube(origem, diretorio_saida, parent_widget=parent_widget)
        if not nome_base:
            nome_base = "video"
    else:
        msg = "Erro: Fonte inválida. Forneça uma URL válida ou caminho de arquivo local."
        log_erro(msg)
        registrar_erro_usuario("Conversão", "Fonte inválida. Forneça uma URL ou arquivo local válido.")
        if parent_widget:
            QMessageBox.critical(parent_widget, "Erro", msg)
        else:
            print(msg)
        return None, None

    if not caminho_video:
        return None, None

    caminho_audio = extrair_audio(caminho_video, diretorio_saida, nome_base, parent_widget=parent_widget)
    if not caminho_audio:
        return caminho_video, None

    arquivos_gerados = [caminho_video, caminho_audio]

    if '1' in formatos_selecionados:
        caminho_telefonia = converter_para_telefonia(caminho_audio, diretorio_saida, nome_base, parent_widget=parent_widget)
        if caminho_telefonia:
            arquivos_gerados.append(caminho_telefonia)
    if '2' in formatos_selecionados:
        caminho_hq = converter_para_alta_qualidade(caminho_audio, diretorio_saida, nome_base, parent_widget=parent_widget)
        if caminho_hq:
            arquivos_gerados.append(caminho_hq)
    if '3' in formatos_selecionados:
        caminho_podcast = converter_para_podcast(caminho_audio, diretorio_saida, nome_base, parent_widget=parent_widget)
        if caminho_podcast:
            arquivos_gerados.append(caminho_podcast)
    if '4' in formatos_selecionados:
        caminho_stream = converter_para_streaming(caminho_audio, diretorio_saida, nome_base, parent_widget=parent_widget)
        if caminho_stream:
            arquivos_gerados.append(caminho_stream)
    if '5' in formatos_selecionados:
        caminho_radio = converter_para_radio(caminho_audio, diretorio_saida, nome_base, parent_widget=parent_widget)
        if caminho_radio:
            arquivos_gerados.append(caminho_radio)
    if '6' in formatos_selecionados:
        caminho_whatsapp = converter_para_whatsapp(caminho_audio, diretorio_saida, nome_base, parent_widget=parent_widget)
        if caminho_whatsapp:
            arquivos_gerados.append(caminho_whatsapp)

    return caminho_video, arquivos_gerados

if __name__ == "__main__":
    try:
        print("\nProcessador de Vídeo e Áudio")
        print("============================")
        print("\nEste script pode processar vídeos de diferentes fontes:")
        print("1. YouTube")
        print("2. Arquivos locais")
        
        origem = input("\nDigite a URL do vídeo ou o caminho do arquivo local: ")
        
        print("\nEscolha os formatos de saída desejados:")
        print("1. Padrão Telefonia (WAV 8kHz)")
        print("2. Alta Qualidade (FLAC 96kHz)")
        print("3. Podcast (M4A)")
        print("4. Streaming (OGG)")
        print("5. Rádio FM (WAV)")
        print("6. WhatsApp (OGG/OPUS)")
        
        formatos = input("\nDigite os números dos formatos desejados (separados por vírgula): ").split(',')
        formatos = [f.strip() for f in formatos]
        
        diretorio_saida = criar_diretorio_saida()
        caminho_video, arquivos_gerados = processar_video(origem, diretorio_saida, formatos)
        
        if arquivos_gerados:
            print("\nProcessamento concluído com sucesso!")
            print("\nArquivos gerados:")
            for i, caminho_arquivo in enumerate(arquivos_gerados, 1):
                print(f"{i}. {os.path.basename(caminho_arquivo)}")
        else:
            print("\nErro: Nenhum arquivo foi gerado.")
            
    except KeyboardInterrupt:
        print("\nProcessamento interrompido pelo usuário.")
    except Exception as e:
        log_erro(f"Erro inesperado: {str(e)}")
        registrar_erro_usuario("Conversão", "Erro inesperado no processamento geral.")
        print(f"\nErro inesperado: {str(e)}")
    finally:
        input("\nPressione Enter para sair...")