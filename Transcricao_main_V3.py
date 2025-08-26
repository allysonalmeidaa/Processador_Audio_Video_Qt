import sys
import os
import json
import shutil

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QHBoxLayout, QMessageBox, QSpinBox, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from Transcricao_tab_V3 import TranscricaoTab
from Transcricao_conversao_tab_V3 import ConversaoTab
from logs_tab import LogsTab, adicionar_log

APP_FOLDER_NAME = "ProcessadorDeAudioVideo"

def get_app_folder():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.join(base_dir, APP_FOLDER_NAME)
    if not os.path.exists(app_dir):
        os.makedirs(app_dir, exist_ok=True)
    return app_dir

def ensure_running_in_app_folder():
    app_dir = get_app_folder()
    os.chdir(app_dir)

ensure_running_in_app_folder()

def get_app_dir():
    return get_app_folder()

PASTA_SCRIPT = get_app_dir()
CONFIG_PATH = os.path.join(PASTA_SCRIPT, "config.json")
log_path = os.path.join(PASTA_SCRIPT, 'output.log')
sys.stdout = open(log_path, 'a', encoding='utf-8', buffering=1)
sys.stderr = sys.stdout

if getattr(sys, 'frozen', False):
    bundle_dir = PASTA_SCRIPT
    os.environ["XDG_CACHE_HOME"] = os.path.join(bundle_dir, ".cache")
    os.makedirs(os.path.join(bundle_dir, ".cache", "whisper"), exist_ok=True)
else:
    bundle_dir = PASTA_SCRIPT
    os.environ["XDG_CACHE_HOME"] = os.path.join(bundle_dir, ".cache")
    os.makedirs(os.path.join(bundle_dir, ".cache", "whisper"), exist_ok=True)

transcricao_tab_global = None

def set_transcricao_tab_instance(tab):
    global transcricao_tab_global
    transcricao_tab_global = tab

def log_interface(mensagem: str):
    from datetime import datetime
    hora = datetime.now().strftime("[%H:%M:%S]")
    s = f"{hora} {mensagem}"
    if transcricao_tab_global:
        transcricao_tab_global.adicionar_log_console(s)
    adicionar_log(s)
    print(s)

IDIOMAS = [
    ("auto", "Detectar automático"),
    ("pt", "Português"),
    ("en", "Inglês"),
    ("es", "Espanhol"),
    ("fr", "Francês"),
    ("de", "Alemão"),
]

def garantir_config():
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
        except Exception:
            pass

garantir_config()

def get_dark_stylesheet():
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
        QTabBar::tab:!selected {
            color: #bbb;
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
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def salvar_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

class ConfigTab(QWidget):
    def __init__(self):
        super().__init__()
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
        self.tabs = QTabWidget()
        self.transcricao_tab = TranscricaoTab()
        set_transcricao_tab_instance(self.transcricao_tab)
        self.conversao_tab = ConversaoTab()
        self.config_tab = ConfigTab()
        self.logs_tab = LogsTab()
        self.tabs.addTab(self.transcricao_tab, "Transcrição")
        self.tabs.addTab(self.conversao_tab, "Conversão")
        self.tabs.addTab(self.config_tab, "Configurações")
        self.tabs.addTab(self.logs_tab, "Logs")
        self.tabs.addTab(SobreTab(), "Sobre")
        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(self.atualizar_aba_transcricao)

        from ffmpeg_utils import garantir_ffmpeg
        garantir_ffmpeg(log_interface)

    def atualizar_aba_transcricao(self, idx):
        if self.tabs.widget(idx) == self.transcricao_tab:
            self.transcricao_tab.atualizar_config_interface()

    def aplicar_tema(self):
        config = carregar_config()
        tema = config.get("tema", "escuro")
        if tema == "claro":
            QApplication.instance().setStyleSheet(get_light_stylesheet())
        else:
            QApplication.instance().setStyleSheet(get_dark_stylesheet())

if __name__ == "__main__":
    import subprocess
    if sys.platform.startswith("win"):
        _orig_popen = subprocess.Popen
        def _popen_no_window(*args, **kwargs):
            cf = kwargs.get("creationflags", 0)
            cf |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
            kwargs["creationflags"] = cf
            return _orig_popen(*args, **kwargs)
        subprocess.Popen = _popen_no_window

    app = QApplication(sys.argv)
    config = carregar_config()
    tema = config.get("tema", "escuro")
    if tema == "claro":
        app.setStyleSheet(get_light_stylesheet())
    else:
        app.setStyleSheet(get_dark_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())