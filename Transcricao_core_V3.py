import os
import sys
import traceback

from ffmpeg_utils import garantir_ffmpeg, adicionar_ffmpeg_no_path, copiar_ffmpeg_para_app_dir

# --- Garante ffmpeg disponível para Whisper ---
garantir_ffmpeg()           # baixa se não houver
copiar_ffmpeg_para_app_dir()  # põe ffmpeg.exe ao lado do .exe
adicionar_ffmpeg_no_path()    # adiciona ffmpeg ao PATH do processo
# ---------------------------------------------

import whisper
from datetime import timedelta
from diarizacao_resemblyzer import diarize_audio
from erros_usuario import registrar_erro_usuario
from PyQt6.QtCore import QCoreApplication
import subprocess

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

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
        model = whisper.load_model(modelo)
        if not os.path.exists(model_path) or os.path.getsize(model_path) < 1000000:
            raise RuntimeError(
                "Falha ao baixar o modelo Whisper. Verifique sua conexão com a internet, espaço em disco e se não há restrição de firewall/antivírus."
            )
        return model
    except Exception as e:
        print(traceback.format_exc())
        if progresso_callback:
            progresso_callback(100, f"Erro ao baixar/carregar modelo Whisper: {str(e)}")
        raise RuntimeError(f"Erro ao baixar/carregar modelo Whisper: {str(e)}")

def transcrever_com_diarizacao(caminho_arquivo, modelo_escolhido, idioma=None, progresso_callback=None):
    PASTA_SCRIPT = get_app_dir()
    PASTA_TRANSCRICOES = os.path.join(PASTA_SCRIPT, "Transcricoes")
    if not os.path.exists(PASTA_TRANSCRICOES):
        os.makedirs(PASTA_TRANSCRICOES)

    nome_base = os.path.splitext(os.path.basename(caminho_arquivo))[0]
    caminho_audio_temp = None

    try:
        if progresso_callback:
            progresso_callback(5, "Extraindo arquivo")

        ext = os.path.splitext(caminho_arquivo)[1].lower()
        if ext not in ['.wav', '.flac']:
            caminho_audio_temp = os.path.join(PASTA_SCRIPT, f"temp_{nome_base}.wav")
            try:
                ffmpeg_cmd = garantir_ffmpeg()
                if not ffmpeg_cmd:
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
                processo = subprocess.run(
                    comando,
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
                if processo.returncode != 0:
                    registrar_erro_usuario(
                        "Transcrição",
                        "Falha ao extrair áudio do arquivo. Verifique se o arquivo é válido e se o FFmpeg está instalado."
                    )
                    raise RuntimeError("Erro ao extrair áudio com FFmpeg: " + processo.stderr)
                caminho_arquivo_para_diarizacao = caminho_audio_temp
            except Exception as e:
                registrar_erro_usuario(
                    "Transcrição",
                    "Falha ao extrair áudio do arquivo. Verifique se o arquivo é válido e se o FFmpeg está instalado."
                )
                raise RuntimeError("Erro ao extrair áudio com FFmpeg: " + str(e))
        else:
            caminho_arquivo_para_diarizacao = caminho_arquivo

        if progresso_callback:
            progresso_callback(10, "Diarizando falantes")

        diarization = diarize_audio(caminho_arquivo_para_diarizacao, verbose=True)

        if progresso_callback:
            progresso_callback(40, "Diarização concluída")

        if progresso_callback:
            progresso_callback(50, "Verificando modelo Whisper...")

        try:
            modelo = baixar_e_avisa_modelo(modelo_escolhido, progresso_callback)
        except Exception as e:
            registrar_erro_usuario(
                "Transcrição",
                f"Falha ao carregar/baixar modelo Whisper. Erro: {str(e)}"
            )
            if progresso_callback:
                progresso_callback(100, f"Erro ao baixar/carregar modelo Whisper: {str(e)}")
            raise

        kwargs = {}
        if idioma and idioma != "auto":
            kwargs["language"] = idioma

        try:
            resultado = modelo.transcribe(caminho_arquivo_para_diarizacao, **kwargs)
        except Exception as e:
            registrar_erro_usuario(
                "Transcrição",
                "Falha ao transcrever áudio. Possível erro no Whisper ou arquivo corrompido."
            )
            print(traceback.format_exc())
            raise

        if progresso_callback:
            progresso_callback(80, "Transcrição concluída")

        if progresso_callback:
            progresso_callback(85, "Combinando falantes e transcrição")

        speakers_detected = sorted(set([d[2] for d in diarization if d[2] != "unknown"]))
        label_map = {speaker: f"Speaker {i+1}" for i, speaker in enumerate(speakers_detected)}

        segments = []
        for seg_start, seg_end, speaker in diarization:
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

        if idioma != "en":
            if progresso_callback:
                progresso_callback(92, "Traduzindo para o inglês")
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

        if progresso_callback:
            progresso_callback(100, "Processo concluído!")

        if not segments or len(segments) == 0:
            return "Nenhum segmento de fala foi detectado ou todos os segmentos foram filtrados."
        else:
            texto_interface = ""
            for segment in segments:
                texto_interface += f"[{format_timestamp(segment['start'])} -> {format_timestamp(segment['end'])}] {segment['speaker']}: {segment['text']}\n\n"
            return texto_interface

    except Exception as e:
        registrar_erro_usuario("Transcrição", f"Erro inesperado: {str(e)}")
        print(traceback.format_exc())
        raise
    finally:
        if caminho_audio_temp and os.path.exists(caminho_audio_temp):
            try:
                os.remove(caminho_audio_temp)
            except Exception:
                pass