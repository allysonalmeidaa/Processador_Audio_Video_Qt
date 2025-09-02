# tqdm_safe.py
# Substitui o tqdm por uma versão segura que não cria threads
 
import threading
 
class tqdm:
    """Classe segura para substituir o tqdm."""    
    def __init__(self, iterable=None, total=None, desc=None, disable=False, **kwargs):
        self.iterable = iterable
        self.total = total
        self.desc = desc
        self.disable = disable
        self.n = 0
        self._lock = threading.Lock()
 
    def __iter__(self):
        if self.iterable:
            for item in self.iterable:
                yield item
                self.update()
 
    def update(self, n=1):
        with self._lock:
            self.n += n
 
    def set_postfix(self, **kwargs):
        pass
 
    def close(self):
        pass
 
    def __enter__(self):
        # Simula entrada no contexto
        return self
 
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Simula saída do contexto
        self.close()
 
 
# Simula o módulo tqdm.monitor
class monitor:
    """Simulador de monitor para evitar threads."""
    def __init__(self, *args, **kwargs):
        pass
 
    def start(self):
        pass
 
    def refresh(self):
        pass
 
    def atexit_register(self, func, *args, **kwargs):
        pass
 
 
# Garante que o tqdm tenha um atributo monitor
tqdm.monitor = monitor
 
# Exporta a classe tqdm como variável global
__all__ = ['tqdm']