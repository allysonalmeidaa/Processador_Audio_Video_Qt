import os
import sys
import json
from datetime import datetime

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def caminho_erros_usuario():
    return os.path.join(get_app_dir(), "erros_usuarios.json")

def registrar_erro_usuario(tipo, mensagem):
    erros = []
    caminho = caminho_erros_usuario()
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                erros = json.load(f)
        except Exception:
            erros = []
    erros.append({
        "data": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "tipo": tipo,
        "mensagem": mensagem
    })
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(erros[-30:], f, ensure_ascii=False, indent=2)

def ler_erros_usuario():
    caminho = caminho_erros_usuario()
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def limpar_erros_usuario():
    caminho = caminho_erros_usuario()
    if os.path.exists(caminho):
        os.remove(caminho)