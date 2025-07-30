import os
import sys
import traceback

from ffmpeg_utils import garantir_ffmpeg

import whisper
from datetime import timedelta
from diarizacao_resemblyzer import diarize_audio
from erros_usuario import registrar_erro_usuario
from PyQt6.QtCore import QCoreApplication
import subprocess

# Importe a função global de log do programa
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

def format_timestamp(seconds):
    return str(timedelta(seconds=float(seconds))).split('.')[0]

def remove_repeticoes(segments):
    if not segments:
        return segments
    cleaned_segments = []
    previous_segment = None
    for segment in segments:
        if previous_segment is None:
            cleaned_segments.append(segment)
            previous_segment = segment
            continue
        current_text = segment["text"].strip().lower()
        previous_text = previous_segment["text"].strip().lower()
        cleaned_current = ''.join(c for c in current_text if c.isalnum() or c.isspace())
        cleaned_prev = ''.join(c for c in previous_text if c.isalnum() or c.isspace())
        if (abs(len(cleaned_current) - len(cleaned_prev)) > 10 or  
            (cleaned_current not in cleaned_prev and cleaned_prev not in cleaned_current)):
            cleaned_segments.append(segment)
            previous_segment = segment
    return cleaned_segments

def baixar_e_avisa_modelo(modelo, progresso_callback=None):
    try:
        cache_dir = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
        model_path = os.path.join(cache_dir, "whisper", f"{modelo}.pt")
        if not os.path.exists(model_path):
            if progresso_callback:
                progresso_callback(20, f"Baixando o modelo '{modelo}'. Isso pode demorar alguns minutos na primeira vez (internet necessária).")
            QCoreApplication.processEvents()
            adicionar_log(f"Baixando o modelo '{modelo}'.")
        model = whisper.load_model(modelo)
        if not os.path.exists(model_path) or os.path.getsize(model_path) < 1000000:
            adicionar_log(f"Falha ao baixar o modelo Whisper '{modelo}'.")
            raise RuntimeError(
                "Falha ao baixar o modelo Whisper. Verifique sua conexão com a internet, espaço em disco e se não há restrição de firewall/antivírus."
            )
        adicionar_log(f"Modelo '{modelo}' carregado com sucesso.")
        return model
    except Exception as e:
        adicionar_log(f"Erro ao baixar/carregar modelo Whisper: {str(e)}")
        print(traceback.format_exc())
        if progresso_callback:
            progresso_callback(100, f"Erro ao baixar/carregar modelo Whisper: {str(e)}")
        raise RuntimeError(f"Erro ao baixar/carregar modelo Whisper: {str(e)}")

def transcrever_com_diarizacao(caminho_arquivo, modelo_escolhido, idioma=None, progresso_callback=None, checar_cancelamento=None):
    PASTA_SCRIPT = get_app_dir()
    PASTA_TRANSCRICOES = os.path.join(PASTA_SCRIPT, "Transcricoes")
    if not os.path.exists(PASTA_TRANSCRICOES):
        os.makedirs(PASTA_TRANSCRICOES)

    nome_base = os.path.splitext(os.path.basename(caminho_arquivo))[0]
    caminho_audio_temp = None

    try:
        adicionar_log(f"Iniciando transcrição para o arquivo '{caminho_arquivo}'.")
        if progresso_callback:
            progresso_callback(5, "Extraindo arquivo")
        adicionar_log("Extraindo arquivo de áudio/vídeo.")

        if checar_cancelamento and checar_cancelamento():
            adicionar_log("Transcrição cancelada pelo usuário antes da extração.")
            raise Exception("Transcrição cancelada pelo usuário.")

        ext = os.path.splitext(caminho_arquivo)[1].lower()
        if ext not in ['.wav', '.flac']:
            caminho_audio_temp = os.path.join(PASTA_SCRIPT, f"temp_{nome_base}.wav")
            try:
                def log_ffmpeg(msg):
                    if progresso_callback:
                        progresso_callback(2, msg)
                    adicionar_log(f"FFmpeg: {msg}")
                ffmpeg_cmd = garantir_ffmpeg(log_ffmpeg)
                if not ffmpeg_cmd:
                    registrar_erro_usuario(
                        "Transcrição",
                        "FFmpeg não encontrado ou falha ao baixar."
                    )
                    adicionar_log("FFmpeg não encontrado ou falha ao baixar.")
                    raise RuntimeError("FFmpeg não encontrado.")
                comando = [
                    ffmpeg_cmd,
                    '-i', caminho_arquivo,
                    '-acodec', 'pcm_s16le',
                    '-ac', '1',
                    '-ar', '16000',
                    '-y',
                    caminho_audio_temp
                ]
                # ALTERAÇÃO: startupinfo + creationflags para garantir ocultação do CMD
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
                if processo.returncode != 0:
                    registrar_erro_usuario(
                        "Transcrição",
                        "Falha ao extrair áudio do arquivo. Verifique se o arquivo é válido e se o FFmpeg está instalado."
                    )
                    adicionar_log(f"Erro ao extrair áudio com FFmpeg: {processo.stderr}")
                    raise RuntimeError("Erro ao extrair áudio com FFmpeg: " + processo.stderr)
                caminho_arquivo_para_diarizacao = caminho_audio_temp
                adicionar_log(f"Arquivo convertido para WAV temporário: {caminho_audio_temp}")
            except Exception as e:
                registrar_erro_usuario(
                    "Transcrição",
                    "Falha ao extrair áudio do arquivo. Verifique se o arquivo é válido e se o FFmpeg está instalado."
                )
                adicionar_log(f"Erro ao extrair áudio com FFmpeg: {str(e)}")
                raise RuntimeError("Erro ao extrair áudio com FFmpeg: " + str(e))
        else:
            caminho_arquivo_para_diarizacao = caminho_arquivo
            adicionar_log(f"Arquivo já está em formato suportado (WAV/FLAC): {caminho_arquivo}")

        if checar_cancelamento and checar_cancelamento():
            adicionar_log("Transcrição cancelada pelo usuário após extração.")
            raise Exception("Transcrição cancelada pelo usuário.")

        if progresso_callback:
            progresso_callback(10, "Diarizando falantes")
        adicionar_log("Processando diarização de falantes.")

        if checar_cancelamento and checar_cancelamento():
            adicionar_log("Transcrição cancelada pelo usuário antes da diarização.")
            raise Exception("Transcrição cancelada pelo usuário.")

        diarization = diarize_audio(caminho_arquivo_para_diarizacao, verbose=True)
        adicionar_log("Diarização concluída.")

        if progresso_callback:
            progresso_callback(40, "Diarização concluída")

        if checar_cancelamento and checar_cancelamento():
            adicionar_log("Transcrição cancelada pelo usuário após diarização.")
            raise Exception("Transcrição cancelada pelo usuário.")

        if progresso_callback:
            progresso_callback(50, "Verificando modelo Whisper...")
        adicionar_log("Verificando modelo Whisper...")

        if checar_cancelamento and checar_cancelamento():
            adicionar_log("Transcrição cancelada pelo usuário antes do carregamento do modelo Whisper.")
            raise Exception("Transcrição cancelada pelo usuário.")

        try:
            modelo = baixar_e_avisa_modelo(modelo_escolhido, progresso_callback)
        except Exception as e:
            registrar_erro_usuario(
                "Transcrição",
                f"Falha ao carregar/baixar modelo Whisper. Erro: {str(e)}"
            )
            adicionar_log(f"Falha ao carregar/baixar modelo Whisper: {str(e)}")
            if progresso_callback:
                progresso_callback(100, f"Erro ao baixar/carregar modelo Whisper: {str(e)}")
            raise

        if checar_cancelamento and checar_cancelamento():
            adicionar_log("Transcrição cancelada pelo usuário após carregamento do modelo Whisper.")
            raise Exception("Transcrição cancelada pelo usuário.")

        kwargs = {}
        if idioma and idioma != "auto":
            kwargs["language"] = idioma
            adicionar_log(f"Idioma definido para transcrição: {idioma}")

        try:
            adicionar_log("Iniciando transcrição com Whisper.")
            resultado = modelo.transcribe(caminho_arquivo_para_diarizacao, **kwargs)
        except Exception as e:
            registrar_erro_usuario(
                "Transcrição",
                "Falha ao transcrever áudio. Possível erro no Whisper ou arquivo corrompido."
            )
            adicionar_log(f"Falha ao transcrever áudio: {str(e)}")
            print(traceback.format_exc())
            raise

        if progresso_callback:
            progresso_callback(80, "Transcrição concluída")
        adicionar_log("Transcrição concluída.")

        if checar_cancelamento and checar_cancelamento():
            adicionar_log("Transcrição cancelada pelo usuário após transcrição.")
            raise Exception("Transcrição cancelada pelo usuário.")

        if progresso_callback:
            progresso_callback(85, "Combinando falantes e transcrição")
        adicionar_log("Combinando falantes e transcrição.")

        speakers_detected = sorted(set([d[2] for d in diarization if d[2] != "unknown"]))
        label_map = {speaker: f"Speaker {i+1}" for i, speaker in enumerate(speakers_detected)}

        segments = []
        for seg_start, seg_end, speaker in diarization:
            if checar_cancelamento and checar_cancelamento():
                adicionar_log("Transcrição cancelada pelo usuário durante combinação de falantes.")
                raise Exception("Transcrição cancelada pelo usuário.")
            segment_text = ""
            for segment in resultado["segments"]:
                whisper_start = segment["start"]
                whisper_end = segment["end"]
                if (whisper_start <= seg_end and whisper_end >= seg_start):
                    segment_text += " " + segment["text"]
            if segment_text.strip():
                speaker_label = label_map.get(speaker, "Speaker desconhecido") if speaker != "unknown" else "Speaker desconhecido"
                segments.append({
                    "speaker": speaker_label,
                    "start": seg_start,
                    "end": seg_end,
                    "text": segment_text.strip()
                })
        segments = remove_repeticoes(segments)
        adicionar_log(f"Segmentos processados: {len(segments)}")

        if progresso_callback:
            progresso_callback(90, "Salvando transcrição")
        caminho_transcr = os.path.join(PASTA_TRANSCRICOES, f"transcricao_{nome_base}.txt")
        with open(caminho_transcr, "w", encoding="utf-8") as f:
            if not segments or len(segments) == 0:
                mensagem = "AVISO: Nenhum segmento de fala foi detectado ou todos os segmentos foram filtrados.\n"
                f.write(mensagem)
            else:
                for segment in segments:
                    f.write(f"[{format_timestamp(segment['start'])} -> {format_timestamp(segment['end'])}] {segment['speaker']}: {segment['text']}\n\n")
        adicionar_log(f"Transcrição salva em: {caminho_transcr}")

        if idioma != "en":
            if progresso_callback:
                progresso_callback(92, "Traduzindo para o inglês")
            adicionar_log("Traduzindo para o inglês.")

            if checar_cancelamento and checar_cancelamento():
                adicionar_log("Transcrição cancelada pelo usuário durante tradução.")
                raise Exception("Transcrição cancelada pelo usuário.")

            resultado_traduzido = modelo.transcribe(caminho_arquivo_para_diarizacao, task="translate", **kwargs)
            if progresso_callback:
                progresso_callback(95, "Salvando tradução em inglês")
            caminho_trad = os.path.join(PASTA_TRANSCRICOES, f"transcricao_{nome_base}_ingles.txt")
            with open(caminho_trad, "w", encoding="utf-8") as f:
                if not segments or len(segments) == 0:
                    mensagem = "WARNING: No speech segments were detected or all segments were filtered.\n"
                    f.write(mensagem)
                else:
                    for segment in segments:
                        translated_text = ""
                        for trans_segment in resultado_traduzido["segments"]:
                            if (trans_segment["start"] <= segment["end"] and 
                                trans_segment["end"] >= segment["start"]):
                                translated_text += " " + trans_segment["text"]
                        if translated_text.strip():
                            f.write(f"[{format_timestamp(segment['start'])} -> {format_timestamp(segment['end'])}] {segment['speaker']}: {translated_text.strip()}\n\n")
            adicionar_log(f"Tradução em inglês salva em: {caminho_trad}")

        if progresso_callback:
            progresso_callback(100, "Processo concluído!")
        adicionar_log("Processo de transcrição finalizado.")

        if not segments or len(segments) == 0:
            adicionar_log("Nenhum segmento de fala foi detectado ou todos os segmentos foram filtrados.")
            return "Nenhum segmento de fala foi detectado ou todos os segmentos foram filtrados."
        else:
            texto_interface = ""
            for segment in segments:
                texto_interface += f"[{format_timestamp(segment['start'])} -> {format_timestamp(segment['end'])}] {segment['speaker']}: {segment['text']}\n\n"
            adicionar_log("Transcrição de texto pronta para interface.")
            return texto_interface

    except Exception as e:
        registrar_erro_usuario("Transcrição", f"Erro inesperado: {str(e)}")
        adicionar_log(f"Erro inesperado na transcrição: {str(e)}")
        print(traceback.format_exc())
        raise
    finally:
        if caminho_audio_temp and os.path.exists(caminho_audio_temp):
            try:
                os.remove(caminho_audio_temp)
                adicionar_log(f"Arquivo temporário removido: {caminho_audio_temp}")
            except Exception:
                adicionar_log(f"Falha ao remover arquivo temporário: {caminho_audio_temp}")