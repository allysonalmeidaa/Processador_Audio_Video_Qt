import numpy as np
import os
import sys
import shutil
import tempfile
import librosa
from sklearn.cluster import DBSCAN
from datetime import datetime

# Importe o logger global para registrar tudo que acontece
from logs_tab import adicionar_log

def get_app_dir():
    # Diretório raiz do projeto/pasta de dados do app
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.join(base_dir, "ProcessadorDeAudioVideo")
    if not os.path.exists(app_dir):
        os.makedirs(app_dir, exist_ok=True)
    return app_dir

def resource_path(relative_path):
    """
    Retorna caminho absoluto para recursos (ex: modelos, etc.)
    Sempre relativo ao arquivo atual, compatível Linux/Windows.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)

def ensure_pretrained_in_temp():
    """
    Garante que o modelo Resemblyzer está disponível para uso
    - No modo PyInstaller (frozen), copia para temp (compatível Linux/Windows)
    - No modo desenvolvimento, usa diretório local (compatível Linux/Windows)
    """
    if hasattr(sys, '_MEIPASS'):
        temp_dir = tempfile.gettempdir()
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

def remove_repeticoes(diarization_result, threshold=0.8):
    """
    Remove segmentos repetidos da diarização baseando-se em similaridade de texto e tempo.
    threshold: 0-1, quanto maior, mais agressivo na remoção de repetições
    """
    if not diarization_result or len(diarization_result) <= 1:
        return diarization_result
    
    cleaned_result = []
    previous_segment = None
    
    for current_segment in diarization_result:
        if previous_segment is None:
            cleaned_result.append(current_segment)
            previous_segment = current_segment
            continue
            
        # Verifica sobreposição temporal excessiva
        start_prev, end_prev, speaker_prev = previous_segment
        start_curr, end_curr, speaker_curr = current_segment
        
        # Se for o mesmo speaker e houver sobreposição significativa, verifica repetição
        if (speaker_prev == speaker_curr and 
            start_curr < end_prev and  # Há sobreposição temporal
            (end_curr - start_curr) > 1.0):  # Segmento tem mais de 1 segundo
            
            # Calcula sobreposição temporal
            overlap = min(end_prev, end_curr) - max(start_prev, start_curr)
            overlap_percentage = overlap / (end_curr - start_curr)
            
            # Se mais de 80% de sobreposição, provavelmente é repetição
            if overlap_percentage > threshold:
                adicionar_log(f"Removendo segmento repetido: {start_curr:.1f}s-{end_curr:.1f}s")
                continue
        
        cleaned_result.append(current_segment)
        previous_segment = current_segment
    
    return cleaned_result

def merge_short_segments(diarization_result, min_duration=0.5):
    """
    Funde segmentos muito curtos com segmentos adjacentes do mesmo speaker
    """
    if not diarization_result:
        return diarization_result
    
    merged_result = []
    current_segment = None
    
    for segment in diarization_result:
        start, end, speaker = segment
        duration = end - start
        
        if current_segment is None:
            current_segment = segment
            continue
        
        curr_start, curr_end, curr_speaker = current_segment
        curr_duration = curr_end - curr_start
        
        # Se for o mesmo speaker e o segmento atual for muito curto, merge
        if (speaker == curr_speaker and 
            (duration < min_duration or curr_duration < min_duration)):
            # Merge os segmentos
            current_segment = (min(curr_start, start), max(curr_end, end), speaker)
            adicionar_log(f"Fundindo segmentos curtos: {curr_start:.1f}s-{curr_end:.1f}s + {start:.1f}s-{end:.1f}s")
        else:
            merged_result.append(current_segment)
            current_segment = segment
    
    if current_segment:
        merged_result.append(current_segment)
    
    return merged_result

def smooth_speaker_transitions(diarization_result, gap_threshold=1.0):
    """
    Suaviza transições entre speakers preenchendo gaps pequenos
    """
    if not diarization_result or len(diarization_result) <= 1:
        return diarization_result
    
    smoothed_result = []
    
    for i in range(len(diarization_result)):
        current = diarization_result[i]
        
        if i == 0:
            smoothed_result.append(current)
            continue
        
        previous = smoothed_result[-1]
        prev_start, prev_end, prev_speaker = previous
        curr_start, curr_end, curr_speaker = current
        
        # Calcula gap entre segmentos
        gap = curr_start - prev_end
        
        # Se gap é pequeno e speakers são diferentes, ajusta os limites
        if gap > 0 and gap < gap_threshold and prev_speaker != curr_speaker:
            # Divide o gap igualmente entre os speakers
            midpoint = prev_end + gap / 2
            smoothed_result[-1] = (prev_start, midpoint, prev_speaker)
            smoothed_result.append((midpoint, curr_end, curr_speaker))
            adicionar_log(f"Suavizando transição: gap de {gap:.1f}s entre speakers")
        else:
            smoothed_result.append(current)
    
    return smoothed_result

def diarize_audio(audio_path, window=1.5, overlap=0.75, dbscan_eps=0.6, dbscan_min_samples=3, verbose=True):
    """
    Diariza áudio usando Resemblyzer + DBSCAN com pós-processamento avançado.
    Retorna lista de (start, end, speaker_id).
    """
    adicionar_log(f"Iniciando diarização do áudio: {audio_path}")
    
    try:
        # Tenta importar Resemblyzer (pode falhar em alguns sistemas)
        try:
            from resemblyzer import VoiceEncoder
        except ImportError as e:
            adicionar_log(f"Resemblyzer não disponível: {e}")
            # Fallback: diarização simulada
            wav, sr = librosa.load(audio_path, sr=16000)
            duration = len(wav) / sr
            return [(0.0, duration, "speaker_0")]
        
        # Garante o modelo Resemblyzer
        pretrained_model_path = ensure_pretrained_in_temp()
        if not pretrained_model_path or not os.path.exists(pretrained_model_path):
            adicionar_log(f"Modelo Resemblyzer não encontrado, usando fallback")
            wav, sr = librosa.load(audio_path, sr=16000)
            duration = len(wav) / sr
            return [(0.0, duration, "speaker_0")]

        audio_path = os.path.abspath(audio_path)
        wav, sr = librosa.load(audio_path, sr=16000)
        duration = len(wav) / sr

        adicionar_log(f"Áudio carregado, duração: {duration:.2f}s, sample rate: {sr}")

        # Ajusta parâmetros baseado na duração do áudio
        if duration > 300:  # Áudios longos (>5min)
            window = 2.0
            overlap = 1.0
            dbscan_eps = 0.7
        elif duration > 60:  # Áudios médios (>1min)
            window = 1.8
            overlap = 0.9

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

        # Extrai embeddings em lotes para melhor performance
        embeddings = []
        for i, seg in enumerate(segments):
            try:
                emb = encoder.embed_utterance(seg)
                embeddings.append(emb)
            except Exception as e:
                adicionar_log(f"Erro no segmento {i}: {e}")
                # Preenche com zeros em caso de erro
                embeddings.append(np.zeros(256))

        embeddings = np.array(embeddings)
        adicionar_log("Embeddings extraídos de todos os segmentos.")

        # Clustering com DBSCAN
        clustering = DBSCAN(eps=dbscan_eps, min_samples=dbscan_min_samples).fit(embeddings)
        labels = clustering.labels_

        adicionar_log(f"Clustering DBSCAN realizado. Labels únicos: {set(labels)}")

        # Cria resultado inicial
        diarization_result = []
        for (start, end), label in zip(segment_times, labels):
            speaker = f"speaker_{label}" if label != -1 else "unknown"
            diarization_result.append((start, end, speaker))

        # APLICA PÓS-PROCESSAMENTO PARA MELHORAR QUALIDADE
        adicionar_log("Aplicando pós-processamento...")
        
        # 1. Remove repetições
        diarization_result = remove_repeticoes(diarization_result, threshold=0.7)
        
        # 2. Funde segmentos muito curtos
        diarization_result = merge_short_segments(diarization_result, min_duration=0.8)
        
        # 3. Suaviza transições entre speakers
        diarization_result = smooth_speaker_transitions(diarization_result, gap_threshold=1.2)

        if verbose:
            speakers = set(l for l in labels if l != -1)
            adicionar_log(f"Falantes detectados: {speakers}")
            adicionar_log(f"Segmentos após pós-processamento: {len(diarization_result)}")

        adicionar_log(f"Diarização finalizada para {audio_path}")

        return diarization_result

    except Exception as e:
        adicionar_log(f"Erro crítico na diarização: {str(e)}")
        import traceback
        adicionar_log(f"Traceback: {traceback.format_exc()}")
        
        # Fallback seguro
        try:
            wav, sr = librosa.load(audio_path, sr=16000)
            duration = len(wav) / sr
            return [(0.0, duration, "speaker_0")]
        except:
            return [(0.0, 60.0, "speaker_0")]