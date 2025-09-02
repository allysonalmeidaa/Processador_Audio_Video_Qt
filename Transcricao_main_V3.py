import sys
import os
 
try: 
    from safe_import import safe_import
    import builtins
    original_import = builtins.__import__
    builtins.__import__ = safe_import
    # Função para restaurar o import normal
    def restaurar_import_normal():
        builtins.__import__ = original_import
        print("Import normal restaurado")
    # Restaurar após a UI carregar
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(2000, restaurar_import_normal)
except Exception as e:
    print(f"Safe import não disponível: {e}")

# === CONFIGURAÇÃO CRÍTICA PARA PYINSTALLER ===
if getattr(sys, 'frozen', False):
    # Executável PyInstaller
    BASE_DIR = os.path.dirname(sys.executable)
    os.chdir(BASE_DIR)  # MUDA o diretório de trabalho
else:
    # Script Python normal
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
 
# Função para obter caminhos absolutos
def resource_path(relative_path):
    return os.path.join(BASE_DIR, relative_path)
 
# Adiciona o diretório base ao sys.path
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
 
# Tenta carregar o tqdm_safe.py
try:
    import tqdm_safe
    sys.modules['tqdm'] = tqdm_safe
    sys.modules['tqdm.auto'] = tqdm_safe
    sys.modules['tqdm.std'] = tqdm_safe
    print("✅ tqdm substituído por versão segura")
except Exception as e:
    print(f"⚠ Falha ao substituir tqdm: {e}")
 
import faulthandler
faulthandler.enable()
 
import json
import logging
from datetime import datetime
 
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QLabel, QComboBox, QPushButton, QMessageBox, QSpinBox, QFormLayout, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, QSharedMemory
from PyQt6.QtGui import QIcon

transcricao_tab_global = None

def set_transcricao_tab_instance(tab):
    global transcricao_tab_global
    transcricao_tab_global = tab 
 
# === SUBSTITUA a função check_single_instance() por esta versão melhorada ===
 
def check_single_instance():
    """Verificação de instância única mais confiável"""
    import tempfile
    import time
    import atexit

    lock_file = os.path.join(tempfile.gettempdir(), "processador_audio_video.lock")

    if os.path.exists(lock_file):
        try:
            file_age = time.time() - os.path.getmtime(lock_file)
            if file_age > 30:
                os.unlink(lock_file)
                print("Removido lock file antigo")
        except:
            pass
    try:
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))

        def remove_lock():
            try: 
                if os.path.exists(lock_file):
                    os.unlink(lock_file)
            except: 
                pass
        atexit.register(remove_lock)
        return True
    except (IOError, OSError):
        print("Outra instância já está em execução!")
        print("Feche a instância anterior antes de abrir uma nova.")
        print("Se não houver uma instância, execute: rm -f /tmp/processador_audio_video.lock")
        return False

if not check_single_instance():
    resposta = input("Deseja forçar a abertura? (s/N): ").lower().strip()
    if resposta != 's':
        sys.exit(1)
    else:
        print("Abertura forçada - pode causar conflitos!")

# === CONFIGURAÇÃO DE PATHS CORRETA ===
APP_FOLDER_NAME = "ProcessadorDeAudioVideo"
CONFIG_PATH = resource_path("config.json")
log_path = resource_path('output.log')
 
# Configuração de logging
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    encoding='utf-8'
)
 
def log_interface(mensagem: str):
    hora = datetime.now().strftime("[%H:%M:%S]")
    s = f"{hora} {mensagem}"
    global transcricao_tab_global
    if transcricao_tab_global is not None:
        try:
            transcricao_tab_global.adicionar_log_console(s)
        except:
            pass
    logging.info(mensagem)
    print(s)

# Idiomas suportados
IDIOMAS = [
    ("auto", "Detectar automático"),
    ("pt", "Português"),
    ("en", "Inglês"),
    ("es", "Espanhol"),
    ("fr", "Francês"),
    ("de", "Alemão"),
]

def garantir_config():
    """Garante que o arquivo de configuração existe e está completo."""
    if not os.path.exists(CONFIG_PATH):
        config_padrao = {
            "modelo": "small",
            "idioma": "auto",
            "max_historico": 20,
            "aviso_tamanho_mb": 300,
            "tema": "escuro",
            "tamanho_fonte_transcricao": 14
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_padrao, f, indent=2, ensure_ascii=False)
    else:
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config_atual = json.load(f)
            alterado = False
            if "aviso_tamanho_mb" not in config_atual:
                config_atual["aviso_tamanho_mb"] = 300
                alterado = True
            if "tema" not in config_atual:
                config_atual["tema"] = "escuro"
                alterado = True
            if "tamanho_fonte_transcricao" not in config_atual:
                config_atual["tamanho_fonte_transcricao"] = 14
                alterado = True
            if alterado:
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(config_atual, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_interface(f"Erro ao carregar config: {e}")

garantir_config()

def get_dark_stylesheet():
    """Retorna o estilo escuro para o app."""
    return """
        QWidget {
            background: #23272b;
            color: #eee;
        }
        QTabWidget::pane {
            border: 1px solid #444;
            border-radius: 5px;
            background: #23272b;
        }
        QTabBar::tab {
            background: #292929;
            border: 1px solid #444;
            border-bottom: none;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            min-width: 130px;
            min-height: 32px;
            margin: 0 2px 0 0;
            padding: 4px 18px;
            color: #bbb;
        }
        QTabBar::tab:selected {
            background: #333;
            color: #8fffa0;
            border-bottom: 2px solid #4ecc5e;
            font-weight: 500;
        }
        QLabel { color: #eee; }
        QLabel#ArquivoLabel {
            background: #253a27;
            color: #8fffa0;
            border-radius: 5px;
            font-weight: bold;
            padding: 2px 10px 2px 6px;
            margin-bottom: 9px;
            border: 1.5px solid #1b5e20;
        }
        QLineEdit, QComboBox, QListWidget, QSpinBox {
            background: #2d3238 !important;
            color: #eee;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 5px;
            selection-background-color: #4ecc5e;
            selection-color: #23272b;
        }
        QTextEdit, QPlainTextEdit {
            background: #232e33 !important;
            color: #e4ede6;
            border: 1.5px solid #444;
            border-radius: 7px;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QTextEdit#TranscricaoTextEdit {
            background: #232e33 !important;
            color: #e4ede6;
        }
        QPlainTextEdit#ConsoleLog {
            background: #1a2320 !important;
            color: #a2ff9b;
            font-family: monospace;
            font-size: 11px;
            border-radius: 5px;
        }
        QPushButton {
            background-color: #292929;
            color: #eee;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 7px 25px;
            font-weight: 500;
            min-width: 170px;
        }
        QPushButton:pressed { background-color: #4ecc5e; color: #23272b;}
        QPushButton:hover { background-color: #343; color: #4ecc5e; }
        QProgressBar {
            border: 1px solid #444;
            border-radius: 4px;
            text-align: center;
            background: #2d3238;
            height: 16px;
        }
        QProgressBar::chunk {
            background-color: #4ecc5e;
            width: 16px;
        }
        QListWidget {
            border: 1px solid #444;
            border-radius: 4px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 9px;
            border: 2px solid #888;
            background: #23272b;
            margin-right: 6px;
        }
        QCheckBox::indicator:checked {
            background-color: #4ecc5e;
            border: 2px solid #4ecc5e;
        }
        QCheckBox:checked {
            font-weight: bold;
            color: #4ecc5e;
        }
        QCheckBox:hover {
            background-color: #232e23;
        }
    """

def get_light_stylesheet():
    """Retorna o estilo claro para o app."""
    return """
        QWidget {
            background: #f7f7f7;
            color: #23272b;
        }
        QTabWidget::pane {
            border: 1px solid #ccc;
            border-radius: 5px;
            background: #f7f7f7;
        }
        QTabBar::tab {
            background: #e9e9e9;
            border: 1px solid #ccc;
            border-bottom: none;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            min-width: 130px;
            min-height: 32px;
            margin: 0 2px 0 0;
            padding: 4px 18px;
            color: #23272b;
        }
        QTabBar::tab:selected {
            background: #fff;
            color: #238c38;
            border-bottom: 2px solid #4ecc5e;
            font-weight: 500;
        }
        QLabel { color: #23272b; }
        QLabel#ArquivoLabel {
            background: #eaffef;
            color: #186b2c;
            border-radius: 5px;
            font-weight: bold;
            padding: 2px 10px 2px 6px;
            margin-bottom: 9px;
            border: 1.5px solid #43c96f;
        }
        QLineEdit, QComboBox, QListWidget, QSpinBox {
            background: #fff !important;
            color: #23272b;
            border: 1px solid #bbb;
            border-radius: 4px;
            padding: 5px;
            selection-background-color: #bdf5c6;
            selection-color: #23272b;
        }
        QTextEdit, QPlainTextEdit {
            background: #fff !important;
            color: #23272b;
            border: 1.5px solid #bbb;
            border-radius: 7px;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QTextEdit#TranscricaoTextEdit {
            background: #fff !important;
            color: #23272b;
        }
        QPlainTextEdit#ConsoleLog {
            background: #fff !important;
            color: #23272b;
            font-family: monospace;
            font-size: 11px;
            border-radius: 5px;
        }
        QPushButton {
            background-color: #e9e9e9;
            color: #23272b;
            border: 1px solid #bbb;
            border-radius: 4px;
            padding: 7px 25px;
            font-weight: 500;
            min-width: 170px;
        }
        QPushButton:pressed { background-color: #bdf5c6; color: #23272b;}
        QPushButton:hover { background-color: #d2f7df; color: #238c38; }
        QProgressBar {
            border: 1px solid #bbb;
            border-radius: 4px;
            text-align: center;
            background: #eee;
            height: 16px;
        }
        QProgressBar::chunk {
            background-color: #4ecc5e;
            width: 16px;
        }
        QListWidget {
            border: 1px solid #bbb;
            border-radius: 4px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 9px;
            border: 2px solid #888;
            background: #fff;
            margin-right: 6px;
        }
        QCheckBox::indicator:checked {
            background-color: #4ecc5e;
            border: 2px solid #4ecc5e;
        }
        QCheckBox:checked {
            font-weight: bold;
            color: #238c38;
        }
        QCheckBox:hover {
            background-color: #e9f7ee;
        }
    """

def carregar_config():
    """Carrega o JSON de configuração."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_interface(f"Erro ao carregar config: {e}")
            return {}
    return {}

def salvar_config(config):
    """Salva o JSON de configuração."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log_interface(f"Erro ao salvar config: {e}")

class ConfigTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("TranscricaoTab")
        self.config = carregar_config()
        layout = QVBoxLayout()
        form = QFormLayout()

        self.combo_tema = QComboBox()
        self.combo_tema.addItem("Escuro", "escuro")
        self.combo_tema.addItem("Claro", "claro")
        tema_atual = self.config.get("tema", "escuro")
        idx_tema = 0 if tema_atual == "escuro" else 1
        self.combo_tema.setCurrentIndex(idx_tema)
        form.addRow("Tema do aplicativo:", self.combo_tema)

        self.combo_modelo = QComboBox()
        self.combo_modelo.addItems(["tiny", "base", "small", "medium", "large"])
        self.combo_modelo.setCurrentText(self.config.get("modelo", "small"))
        form.addRow("Modelo Whisper:", self.combo_modelo)

        self.combo_idioma = QComboBox()
        for cod, nome in IDIOMAS:
            self.combo_idioma.addItem(nome, cod)
        idx = [i for i, (cod, _) in enumerate(IDIOMAS) if cod == self.config.get("idioma", "auto")]
        self.combo_idioma.setCurrentIndex(idx[0] if idx else 0)
        form.addRow("Idioma padrão:", self.combo_idioma)

        self.combo_fontsize = QComboBox()
        self.fontsize_opcoes = [12, 14, 16, 18, 20, 24]
        for size in self.fontsize_opcoes:
            self.combo_fontsize.addItem(f"{size}px", size)
        fontsize_padrao = self.config.get("tamanho_fonte_transcricao", 14)
        idx_font = self.fontsize_opcoes.index(fontsize_padrao) if fontsize_padrao in self.fontsize_opcoes else 1
        self.combo_fontsize.setCurrentIndex(idx_font)
        form.addRow("Tamanho padrão da fonte da transcrição:", self.combo_fontsize)

        self.spin_max_hist = QSpinBox()
        self.spin_max_hist.setRange(1, 100)
        self.spin_max_hist.setValue(self.config.get("max_historico", 20))
        form.addRow("Máximo histórico:", self.spin_max_hist)

        self.spin_aviso_tamanho_mb = QSpinBox()
        self.spin_aviso_tamanho_mb.setRange(10, 4096)
        self.spin_aviso_tamanho_mb.setSuffix(" MB")
        self.spin_aviso_tamanho_mb.setValue(self.config.get("aviso_tamanho_mb", 300))
        form.addRow("Avisar arquivos acima de:", self.spin_aviso_tamanho_mb)

        btn_salvar = QPushButton("Salvar configurações")
        btn_salvar.clicked.connect(self.salvar)
        layout.addLayout(form)
        layout.addWidget(btn_salvar)
        layout.addStretch()
        self.setLayout(layout)

    def salvar(self):
        novo_config = carregar_config()
        novo_config["tema"] = self.combo_tema.currentData()
        novo_config["modelo"] = self.combo_modelo.currentText()
        novo_config["idioma"] = self.combo_idioma.currentData()
        novo_config["tamanho_fonte_transcricao"] = self.combo_fontsize.currentData()
        novo_config["max_historico"] = self.spin_max_hist.value()
        novo_config["aviso_tamanho_mb"] = self.spin_aviso_tamanho_mb.value()
        salvar_config(novo_config)
        self.config = novo_config
        parent = self.parent()
        while parent and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        if parent and hasattr(parent, "aplicar_tema"):
            parent.aplicar_tema()
        QMessageBox.information(self, "Configurações", "Configurações salvas com sucesso!")

class SobreTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        lbl = QLabel(
            "<b>Processador de Áudio e Vídeo (Qt)</b><br>"
            "Desenvolvido por Allyson Almeida Sirvano<br>"
            "Sob a supervisão de Mauricio Menon<br>"
            "Data: Junho/2025<br>"
            "<a href='https://github.com/allysonalmeidaa'>GitHub do autor</a>"
        )
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        lbl.setOpenExternalLinks(True)
        layout.addWidget(lbl)
        layout.addStretch()
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Processador de Áudio e Vídeo (Qt)")
        icon_path = os.path.join(os.path.dirname(__file__), "microphone2.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setGeometry(200, 200, 1200, 700)
        
        # Inicialização das abas
        self.transcricao_tab = None
        self.conversao_tab = None
        self.config_tab = None
        self.logs_tab = None
        
        # Cria widget de abas
        self.tabs = QTabWidget()
        
        # Aba de carregamento inicial
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout()
        loading_label = QLabel("Carregando interface...\n\nIsso pode levar alguns segundos.")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_label.setStyleSheet("font-size: 16px; color: #4ecc5e;")
        
        self.loading_spinner = QProgressBar()
        self.loading_spinner.setRange(0, 0)
        self.loading_spinner.setFixedHeight(20)
        
        loading_layout.addWidget(loading_label)
        loading_layout.addWidget(self.loading_spinner)
        loading_layout.addStretch()
        self.loading_widget.setLayout(loading_layout)
        
        self.tabs.addTab(self.loading_widget, "Carregando")
        self.setCentralWidget(self.tabs)
        
        # Configura tema inicial
        self.config = carregar_config()
        tema = self.config.get("tema", "escuro")
        if tema == "claro":
            QApplication.instance().setStyleSheet(get_light_stylesheet())
        else:
            QApplication.instance().setStyleSheet(get_dark_stylesheet())
        
        # Carrega as abas reais após um breve delay
        QTimer.singleShot(100, self.carregar_abas_reais)

    def carregar_abas_reais(self):
        """Carrega as abas reais após a UI estar visível NA ORDEM CORRETA"""
        try:
            self.adicionar_log_global("Iniciando carregamento das abas...")
            
            # Remove aba de carregamento
            self.tabs.removeTab(0)
            
            # CARREGA NA ORDEM CORRETA:
            # 1. Transcrição (primeira aba)
            self.carregar_transcricao_tab()
            
            # 2. Conversão (segunda aba)
            self.carregar_conversao_tab()
            
            # 3. Configurações (terceira aba)
            self.carregar_config_tab()
            
            # 4. Logs (quarta aba)
            self.carregar_logs_tab()
            
            # 5. Sobre (quinta aba)
            self.carregar_sobre_tab()
            
            # DEFINIR ABA INICIAL COMO TRANSCRIÇÃO (índice 0)
            self.tabs.setCurrentIndex(0)
            
            self.adicionar_log_global("Interface carregada com sucesso!")
            
            # Verifica FFmpeg em background
            QTimer.singleShot(1000, self.verificar_ffmpeg_background)
            
        except Exception as e:
            error_msg = f"Erro crítico ao carregar interface: {e}"
            print(error_msg)
            self.mostrar_erro_critico(error_msg)

    def carregar_transcricao_tab(self):
        """Carrega aba de transcrição - retorna índice"""
        try:
            from Transcricao_tab_V3 import TranscricaoTab
            self.transcricao_tab = TranscricaoTab()
            set_transcricao_tab_instance(self.transcricao_tab)
            self.tabs.addTab(self.transcricao_tab, "Transcrição")
            self.adicionar_log_global("Aba de transcrição carregada")
        except Exception as e:
            error_msg = f"Erro ao carregar aba de transcrição: {e}"
            self.adicionar_log_global(error_msg)
            import traceback
            traceback.print_exc()
            
            # Cria aba alternativa
            alt_tab = QWidget()
            layout = QVBoxLayout()
            
            error_label = QLabel(f"Erro ao carregar transcrição:\n{str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setWordWrap(True)
            
            reload_btn = QPushButton("Tentar recarregar")
            reload_btn.clicked.connect(self.recarregar_transcricao_tab)
            
            debug_btn = QPushButton("Informações de diagnóstico")
            debug_btn.clicked.connect(self.mostrar_diagnostico)
            
            layout.addWidget(error_label)
            layout.addWidget(reload_btn)
            layout.addWidget(debug_btn)
            layout.addStretch()
            
            alt_tab.setLayout(layout)
            self.tabs.addTab(alt_tab, "Transcrição (erro)")

    def carregar_conversao_tab(self):
        """Carrega aba de conversão"""
        try:
            from Transcricao_conversão_tab_V3 import ConversaoTab
            self.conversao_tab = ConversaoTab()
            self.tabs.addTab(self.conversao_tab, "Conversão")
            self.adicionar_log_global("Aba de conversão carregada")
        except Exception as e:
            error_msg = f"Erro ao carregar aba de conversão: {e}"
            self.adicionar_log_global(error_msg)
            alt_tab = QLabel(f"Erro ao carregar conversão:\n{str(e)}")
            alt_tab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabs.addTab(alt_tab, "Conversão (erro)")

    def carregar_config_tab(self):
        """Carrega aba de configuração"""
        try:
            self.config_tab = ConfigTab()
            self.tabs.addTab(self.config_tab, "Configurações")
            self.adicionar_log_global("Aba de configuração carregada")
        except Exception as e:
            self.adicionar_log_global(f"Erro ao carregar aba de configuração: {e}")

    def carregar_logs_tab(self):
        """Carrega aba de logs"""
        try:
            from logs_tab import LogsTab
            self.logs_tab = LogsTab()
            self.tabs.addTab(self.logs_tab, "Logs")
            self.adicionar_log_global("Aba de logs carregada")
        except Exception as e:
            self.adicionar_log_global(f"Erro ao carregar aba de logs: {e}")
            self.logs_tab = QPlainTextEdit()
            self.logs_tab.setReadOnly(True)
            self.tabs.addTab(self.logs_tab, "Logs (alternativa)")

    def carregar_sobre_tab(self):
        """Carrega aba sobre"""
        try:
            self.tabs.addTab(SobreTab(), "Sobre")
            self.adicionar_log_global("Aba sobre carregada")
        except Exception as e:
            self.adicionar_log_global(f"Erro ao carregar aba sobre: {e}")

    def recarregar_transcricao_tab(self):
        """Tenta recarregar a aba de transcrição"""
        try:
            current_idx = self.tabs.currentIndex()
            if self.tabs.tabText(current_idx) == "Transcrição (erro)":
                self.tabs.removeTab(current_idx)
                self.carregar_transcricao_tab()
                self.tabs.setCurrentIndex(0)
        except Exception as e:
            self.adicionar_log_global(f"Falha ao recarregar transcrição: {e}")

    def mostrar_diagnostico(self):
        """Mostra informações de diagnóstico"""
        try:
            info = f"""
            Python: {sys.version}
            Plataforma: {sys.platform}
            Diretório: {get_app_dir()}
            
            Tente executar:
            python3 -c "import whisper; print('Whisper OK')"
            python3 -c "import torch; print('Torch OK')"
            """
            
            QMessageBox.information(self, "Diagnóstico", info)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao gerar diagnóstico: {e}")

    def verificar_ffmpeg_background(self):
        """Verifica FFmpeg em background sem travar a UI"""
        try:
            from ffmpeg_utils import garantir_ffmpeg
            garantir_ffmpeg(self.adicionar_log_global)
            self.adicionar_log_global("FFmpeg verificado")
        except Exception as e:
            self.adicionar_log_global(f"Erro ao verificar FFmpeg: {e}")

    def adicionar_log_global(self, mensagem: str):
        """Adiciona log global que funciona mesmo se as abas não estiverem carregadas"""
        try:
            hora = datetime.now().strftime("[%H:%M:%S]")
            log_msg = f"{hora} {mensagem}"
            
            # Log para console
            print(log_msg)
            
            # Log para arquivo
            logging.info(mensagem)
            
            # Tenta enviar para aba de logs se estiver carregada
            if hasattr(self, 'logs_tab') and self.logs_tab:
                if hasattr(self.logs_tab, 'adicionar_log'):
                    self.logs_tab.adicionar_log(log_msg)
                elif hasattr(self.logs_tab, 'appendPlainText'):
                    self.logs_tab.appendPlainText(log_msg)

            # Tenta enviar para console da transcrição se estiver carregada
            if hasattr(self, 'transcricao_tab') and self.transcricao_tab:
                if hasattr(self.transcricao_tab, 'adicionar_log_console'):
                    self.transcricao_tab.adicionar_log_console(log_msg)

        except Exception as e:
            print(f"Erro ao adicionar log: {e}")

    def aplicar_tema(self):
        """Aplica o tema selecionado"""
        try:
            config = carregar_config()
            tema = config.get("tema", "escuro")
            if tema == "claro":
                QApplication.instance().setStyleSheet(get_light_stylesheet())
            else:
                QApplication.instance().setStyleSheet(get_dark_stylesheet())
        except Exception as e:
            self.adicionar_log_global(f"Erro ao aplicar tema: {e}")

    def mostrar_erro_critico(self, mensagem):
        """Mostra erro crítico de inicialização"""
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Icon.Critical)
        error_dialog.setWindowTitle("Erro Crítico")
        error_dialog.setText("Falha ao inicializar o aplicativo")
        error_dialog.setInformativeText(mensagem)
        
        error_dialog.addButton("Fechar", QMessageBox.ButtonRole.AcceptRole)
        debug_btn = error_dialog.addButton("Diagnóstico", QMessageBox.ButtonRole.ActionRole)
        
        error_dialog.exec()
        
        if error_dialog.clickedButton() == debug_btn:
            self.mostrar_diagnostico()

    def closeEvent(self, event):
        """Limpeza segura ao fechar o aplicativo"""
        try:
            # Limpa threads das abas se existirem
            if self.transcricao_tab and hasattr(self.transcricao_tab, 'thread'):
                if self.transcricao_tab.thread and self.transcricao_tab.thread.isRunning():
                    self.transcricao_tab.thread.quit()
                    self.transcricao_tab.thread.wait(2000)
            
            if self.conversao_tab and hasattr(self.conversao_tab, 'thread'):
                if self.conversao_tab.thread and self.conversao_tab.thread.isRunning():
                    self.conversao_tab.thread.quit()
                    self.conversao_tab.thread.wait(2000)
                    
            # Limpa cache do PyTorch se disponível
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
                
        except Exception as e:
            print(f"Erro durante fechamento: {e}")
        
        event.accept()

if __name__ == "__main__":
    try:    
        # === VERIFICAÇÃO DE INSTÂNCIA (nova versão) ===
        if not check_single_instance():
            # Se estiver no terminal, pergunta se quer forçar
            if sys.stdout.isatty():  # Está no terminal
                resposta = input("Deseja forçar a abertura? (s/N): ").lower().strip()
                if resposta != 's':
                    sys.exit(1)
                print("⚠️  Abertura forçada - pode causar conflitos!")
            else:  # Interface gráfica, simplesmente fecha
                sys.exit(1)
 
        # === CONFIGURAÇÕES ESSENCIAIS ===
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        os.environ["QT_SCALE_FACTOR"] = "1"
 
        # Apenas no Windows: evitar janela de subprocesso
        if sys.platform.startswith("win"):
            import subprocess
            _orig_popen = subprocess.Popen
 
            def _popen_no_window(*args, **kwargs):
                cf = kwargs.get("creationflags", 0)
                cf |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
                kwargs["creationflags"] = cf
                return _orig_popen(*args, **kwargs)
 
            subprocess.Popen = _popen_no_window
 
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        config = carregar_config()
        tema = config.get("tema", "escuro")
        if tema == "claro":
            app.setStyleSheet(get_light_stylesheet())
        else:
            app.setStyleSheet(get_dark_stylesheet())
 
        app.setApplicationName("ProcessadorAudioVideo")
        app.setOrganizationName("AllysondeAlmeida")
        app.setApplicationVersion("3.2")
 
        window = MainWindow()
        window.show()
 
        from ffmpeg_utils import garantir_ffmpeg
        garantir_ffmpeg(log_interface)
 
        return_code = app.exec()
 
        print("Encerrando aplicação...")
 
    except Exception as e:
        print(f"Erro fatal na inicialização: {e}")
        import traceback
        traceback.print_exc()
        input("Pressione Enter para sair...")
    finally:
        # LIMPEZA FINAL GARANTIDA
        try:
            import tempfile
            lock_file = os.path.join(tempfile.gettempdir(), "processador_audio_video.lock")
            if os.path.exists(lock_file):
                os.unlink(lock_file)
        except:
            pass
        os._exit(0)