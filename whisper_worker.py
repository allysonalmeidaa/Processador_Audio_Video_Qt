import sys
import os
import json
import traceback
 
# === CONFIGURAÇÃO CRÍTICA PARA PYINSTALLER ===
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
 
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
 
def transcrever_com_diarizacao(caminho_arquivo, modelo, idioma):
    """Função principal de transcrição"""
    try:
        print(f"[WHISPER] Iniciando transcrição: {caminho_arquivo}", file=sys.stderr)
        # Verificar se arquivo existe
        if not os.path.exists(caminho_arquivo):
            return {
                "success": False,
                "error": f"Arquivo não encontrado: {caminho_arquivo}"
            }
        # Configurações de ambiente para melhor performance
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
        import whisper
        import torch
        print(f"[WHISPER] Importou whisper e torch", file=sys.stderr)
        # Configurar dispositivo
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[WHISPER] Usando dispositivo: {device}", file=sys.stderr)
        # Carregar modelo Whisper
        model = whisper.load_model(modelo).to(device)
        print(f"[WHISPER] Modelo carregado: {modelo}", file=sys.stderr)
        # Configurar argumentos de transcrição
        transcribe_args = {}
        if idioma and idioma != "auto":
            transcribe_args["language"] = idioma
        print(f"[WHISPER] Iniciando transcrição...", file=sys.stderr)
        # Fazer transcrição
        result = model.transcribe(caminho_arquivo, **transcribe_args, verbose=False)
        print(f"[WHISPER] Transcrição concluída", file=sys.stderr)
        # Fallback sem diarização para simplificar
        segments_combinados = [{
            "speaker": "Speaker_1",
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"]
        } for seg in result["segments"]]
        return {
            "success": True,
            "text": result["text"],
            "language": result.get("language", "unknown"),
            "diarization": segments_combinados,
            "segments": result["segments"]
        }
    except ImportError as e:
        # Erro de importação de bibliotecas
        error_msg = f"Erro ao importar bibliotecas: {str(e)}"
        print(f"[WHISPER] {error_msg}", file=sys.stderr)
        return {
            "success": False,
            "error": error_msg,
            "traceback": traceback.format_exc()
        }
    except Exception as e:
        # Erro geral
        error_msg = f"Erro na transcrição: {str(e)}"
        print(f"[WHISPER] {error_msg}", file=sys.stderr)
        return {
            "success": False,
            "error": error_msg,
            "traceback": traceback.format_exc()
        }
 
# Função de diarização simplificada (fallback)
def real_diarize_audio(audio_path):
    """Fallback para diarização simulada"""
    try:
        # Tentar importar resemblyzer se disponível
        try:
            from diarizacao_resemblyzer import diarize_audio
            return diarize_audio(audio_path, verbose=False)
        except ImportError:
            # Fallback para diarização simulada
            import librosa
            duration = librosa.get_duration(path=audio_path)
            return [(0.0, duration, "Speaker_1")]
    except:
        return [(0.0, 60.0, "Speaker_1")]
 
# Função para combinar transcrição com diarização
def combinar_transcricao_diarizacao(segments, diarization):
    """Combina resultados da transcrição com diarização"""
    segments_combinados = []
    # Ordenar segmentos por tempo
    segments.sort(key=lambda x: x["start"])
    diarization.sort(key=lambda x: x[0])
    for diar_start, diar_end, speaker in diarization:
        best_match = None
        best_overlap = 0
        # Encontrar segmento de transcrição que melhor se sobrepõe
        for segment in segments:
            whisper_start = segment["start"]
            whisper_end = segment["end"]
            # Calcular sobreposição
            overlap_start = max(whisper_start, diar_start)
            overlap_end = min(whisper_end, diar_end)
            overlap_duration = max(0, overlap_end - overlap_start)
            if overlap_duration > best_overlap:
                best_overlap = overlap_duration
                best_match = segment
        # Se encontrou uma boa correspondência, adicionar ao resultado
        if best_match and best_overlap > 0.5:
            speaker_label = f"Speaker {speaker.split('_')[-1]}" if speaker != "unknown" else "Speaker desconhecido"
            segments_combinados.append({
                "speaker": speaker_label,
                "start": diar_start,
                "end": diar_end,
                "text": best_match["text"].strip()
            })
    return segments_combinados
 
# === EXECUÇÃO COMO SCRIPT (APENAS PARA DESENVOLVIMENTO) ===
if __name__ == "__main__" and not getattr(sys, 'frozen', False):
    # Só executa como script se não estiver empacotado
    try:
        input_data = sys.stdin.read().strip()
        if not input_data:
            raise ValueError("Nenhum dado de entrada recebido")
        dados = json.loads(input_data)
        # Executar transcrição
        resultado = transcrever_com_diarizacao(
            dados["caminho_arquivo"],
            dados["modelo"],
            dados["idioma"]
        )
        # Escrever resultado
        sys.stdout.write(json.dumps(resultado, ensure_ascii=False))
        sys.stdout.flush()
    except json.JSONDecodeError as e:
        error_result = json.dumps({
            "success": False,
            "error": f"Erro ao decodificar JSON: {str(e)}"
        })
        sys.stdout.write(error_result)
        sys.stdout.flush()
    except Exception as e:
        error_result = json.dumps({
            "success": False,
            "error": f"Erro principal: {str(e)}",
            "traceback": traceback.format_exc()
        })
        sys.stdout.write(error_result)
        sys.stdout.flush()