import gc
import torch
import threading

def clear_memory():
    """Limpeza agressiva de memória para PyTorch"""
    try:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.sunchronize()

        import whisper
        if hasattr(whisper, '_models'):
            whisper._models.clear()
    except Exception as e:
        print(f"Erro ao limpar memória: {e}")
