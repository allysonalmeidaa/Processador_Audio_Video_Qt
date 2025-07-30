import numpy as np
import os
import sys
import shutil
from resemblyzer import VoiceEncoder
import librosa
from sklearn.cluster import DBSCAN

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

def resource_path(relative_path):
    """Obter caminho absoluto para recursos no PyInstaller e no modo dev."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def ensure_pretrained_in_temp():
    # Descobre o diretório TEMP onde o PyInstaller extrai os arquivos
    if hasattr(sys, '_MEIPASS'):
        temp_dir = os.path.join(os.environ.get("TEMP"), os.path.basename(sys._MEIPASS))
        target_dir = os.path.join(temp_dir, "resemblyzer")
        os.makedirs(target_dir, exist_ok=True)
        src = resource_path("resemblyzer/pretrained.pt")
        dst = os.path.join(target_dir, "pretrained.pt")
        if not os.path.exists(dst):
            shutil.copy(src, dst)
            adicionar_log(f"Modelo Resemblyzer copiado para pasta temporária: {dst}")
        # Força o Resemblyzer a procurar no local correto
        return dst
    else:
        # No modo dev, retorna o caminho já existente
        adicionar_log("Modo dev: usando modelo Resemblyzer local.")
        return resource_path("resemblyzer/pretrained.pt")

def diarize_audio(audio_path, window=1.5, overlap=0.75, dbscan_eps=0.6, dbscan_min_samples=3, verbose=True):
    """
    Diariza áudio usando Resemblyzer + DBSCAN.
    Retorna lista de (start, end, speaker_id).
    Todos os arquivos temporários e recursos são buscados/gerados na pasta do app.
    """
    adicionar_log(f"Iniciando diarização do áudio: {audio_path}")
    # Garante o modelo Resemblyzer na pasta correta
    ensure_pretrained_in_temp()
    audio_path = os.path.abspath(audio_path)
    wav, sr = librosa.load(audio_path, sr=16000)
    duration = len(wav) / sr

    adicionar_log(f"Áudio carregado, duração: {duration:.2f}s, sample rate: {sr}")

    step = window - overlap
    segments = []
    segment_times = []
    for start in np.arange(0, duration - window, step):
        s = int(start * sr)
        e = int((start + window) * sr)
        segments.append(wav[s:e])
        segment_times.append((start, start + window))

    adicionar_log(f"Total de segmentos para diarização: {len(segments)}")

    encoder = VoiceEncoder()
    adicionar_log("Modelo de voz Resemblyzer carregado.")

    embeddings = np.array([encoder.embed_utterance(seg) for seg in segments])
    adicionar_log("Embeddings extraídos de todos os segmentos.")

    clustering = DBSCAN(eps=dbscan_eps, min_samples=dbscan_min_samples).fit(embeddings)
    labels = clustering.labels_

    adicionar_log(f"Clustering DBSCAN realizado. Labels únicos: {set(labels)}")

    diarization_result = []
    for (start, end), label in zip(segment_times, labels):
        speaker = f"speaker_{label}" if label != -1 else "unknown"
        diarization_result.append((start, end, speaker))

    if verbose:
        speakers = set(l for l in labels if l != -1)
        print(f"Falantes detectados: {speakers}")
        print(f"Total de segmentos: {len(diarization_result)}")
        adicionar_log(f"Falantes detectados: {speakers}")
        adicionar_log(f"Total de segmentos: {len(diarization_result)}")

    adicionar_log(f"Diarização finalizada para {audio_path}")

    return diarization_result