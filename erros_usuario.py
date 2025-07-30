import os
import sys
from datetime import datetime

# Importe o logger global para registrar também na aba de logs do programa
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

PASTA_SCRIPT = get_app_dir()
ERRO_PATH = os.path.join(PASTA_SCRIPT, "erros_usuarios.log")

def registrar_erro_usuario(modulo, mensagem):
    """Registra erros do usuário em um arquivo centralizado na pasta do app e na aba de logs."""
    try:
        linha = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {modulo}: {mensagem}"
        with open(ERRO_PATH, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
        # Também registra no log global do programa
        adicionar_log(f"[ERRO USUÁRIO] {linha}")
    except Exception as e:
        print(f"Erro ao registrar erro do usuário: {e}")
        adicionar_log(f"Erro ao registrar erro do usuário: {e}")

def ler_erros():
    """Lê todos os erros registrados do usuário."""
    try:
        if os.path.exists(ERRO_PATH):
            with open(ERRO_PATH, "r", encoding="utf-8") as f:
                return f.readlines()
        return []
    except Exception as e:
        print(f"Erro ao ler erros do usuário: {e}")
        adicionar_log(f"Erro ao ler erros do usuário: {e}")
        return []

def limpar_erros():
    """Limpa o arquivo de erros do usuário."""
    try:
        if os.path.exists(ERRO_PATH):
            os.remove(ERRO_PATH)
            adicionar_log("Arquivo de erros do usuário limpo.")
    except Exception as e:
        print(f"Erro ao limpar erros do usuário: {e}")
        adicionar_log(f"Erro ao limpar erros do usuário: {e}")