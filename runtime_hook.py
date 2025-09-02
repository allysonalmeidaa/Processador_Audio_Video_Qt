# runtime_hook.py - Configurações de runtime para o executável
import os
import sys
import warnings
 
# Silenciar warnings
warnings.filterwarnings("ignore")
 
# Configurar paths para recursos
if getattr(sys, 'frozen', False):
    # Modo executável
    base_dir = sys._MEIPASS
else:
    # Modo desenvolvimento
    base_dir = os.path.dirname(os.path.abspath(__file__))
 
# Adicionar paths para bibliotecas
sys.path.insert(0, base_dir)
sys.path.insert(0, os.path.join(base_dir, 'whisper'))
sys.path.insert(0, os.path.join(base_dir, 'resemblyzer'))
 
# Configurar environment variables
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['PYTHONWARNINGS'] = 'ignore'
 
# Configurar para usar CPU apenas
try:
    import torch
    torch.set_num_threads(1)
except:
    pass