import numpy as np
import os
import sys
import shutil
from resemblyzer import VoiceEncoder
import librosa
from sklearn.cluster import DBSCAN

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
        # Força o Resemblyzer a procurar no local correto
        return dst
    else:
        # No modo dev, retorna o caminho já existente
        return resource_path("resemblyzer/pretrained.pt")

def diarize_audio(audio_path, window=1.5, overlap=0.75, dbscan_eps=0.6, dbscan_min_samples=3, verbose=True):
    """
    Diariza áudio usando Resemblyzer + DBSCAN.
    Retorna lista de (start, end, speaker_id).
    """
    ensure_pretrained_in_temp()
    wav, sr = librosa.load(audio_path, sr=16000)
    duration = len(wav) / sr

    step = window - overlap
    segments = []
    segment_times = []
    for start in np.arange(0, duration - window, step):
        s = int(start * sr)
        e = int((start + window) * sr)
        segments.append(wav[s:e])
        segment_times.append((start, start + window))

    encoder = VoiceEncoder()
    embeddings = np.array([encoder.embed_utterance(seg) for seg in segments])

    clustering = DBSCAN(eps=dbscan_eps, min_samples=dbscan_min_samples).fit(embeddings)
    labels = clustering.labels_

    diarization_result = []
    for (start, end), label in zip(segment_times, labels):
        speaker = f"speaker_{label}" if label != -1 else "unknown"
        diarization_result.append((start, end, speaker))

    if verbose:
        speakers = set(l for l in labels if l != -1)
        print(f"Falantes detectados: {speakers}")
        print(f"Total de segmentos: {len(diarization_result)}")

    return diarization_result
