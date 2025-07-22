import sys
import os
import json

log_path = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), 'output.log')
sys.stdout = open(log_path, 'a', encoding='utf-8', buffering=1)
sys.stderr = sys.stdout

if getattr(sys, 'frozen', False):
    bundle_dir = os.path.dirname(sys.executable)
    os.environ["XDG_CACHE_HOME"] = os.path.join(bundle_dir, ".cache")
    os.makedirs(os.path.join(bundle_dir, ".cache", "whisper"), exist_ok=True)
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ["XDG_CACHE_HOME"] = os.path.join(bundle_dir, ".cache")
    os.makedirs(os.path.join(bundle_dir, ".cache", "whisper"), exist_ok=True)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QHBoxLayout, QMessageBox, QSpinBox, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor, QIcon

from Transcricao_tab_V3 import TranscricaoTab
from Transcricao_conversão_tab_V3 import ConversaoTab
from logs_tab import LogsTab

from ffmpeg_utils import garantir_ffmpeg

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

PASTA_SCRIPT = get_app_dir()
CONFIG_PATH = os.path.join(PASTA_SCRIPT, "config.json")
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
            "max_historico": 20
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_padrao, f, indent=2, ensure_ascii=False)

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
        QLineEdit, QTextEdit, QComboBox, QListWidget, QSpinBox {
            background: #2d3238 !important;
            color: #eee;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 5px;
            selection-background-color: #4ecc5e;
            selection-color: #23272b;
        }
        QLineEdit, QLineEdit:disabled, QLineEdit[readOnly="true"] {
            background: #2d3238 !important;
            color: #eee;
            border: 1px solid #444;
        }
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QListWidget:focus, QSpinBox:focus {
            border: 1.5px solid #4ecc5e;
            background: #23272b !important;
        }
        QLineEdit:disabled {
            color: #666;
        }
        QLineEdit::placeholder {
            color: #888 !important;
            background: transparent !important;
        }
        QTextEdit[placeholderText] {
            color: #888 !important;
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
        QCheckBox::indicator:checked:after {
            content: '\\2713';
            color: #23272b;
            font-size: 14px;
            font-weight: bold;
            position: absolute;
            left: 3px;
            top: 0px;
        }
        QCheckBox:checked {
            font-weight: bold;
            color: #4ecc5e;
        }
        QCheckBox:hover {
            background-color: #232e23;
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
        self.spin_max_hist = QSpinBox()
        self.spin_max_hist.setRange(1, 100)
        self.spin_max_hist.setValue(self.config.get("max_historico", 20))
        form.addRow("Máximo histórico:", self.spin_max_hist)
        btn_salvar = QPushButton("Salvar configurações")
        btn_salvar.clicked.connect(self.salvar)
        layout.addLayout(form)
        layout.addWidget(btn_salvar)
        layout.addStretch()
        self.setLayout(layout)

    def salvar(self):
        novo_config = carregar_config()
        novo_config["modelo"] = self.combo_modelo.currentText()
        novo_config["idioma"] = self.combo_idioma.currentData()
        novo_config["max_historico"] = self.spin_max_hist.value()
        salvar_config(novo_config)
        self.config = novo_config
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

_log_tab_instance = None

def set_log_tab_instance(log_tab):
    global _log_tab_instance
    _log_tab_instance = log_tab

def log_interface(mensagem: str):
    print(mensagem)
    if _log_tab_instance:
        _log_tab_instance.adicionar_log(str(mensagem))

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
        self.conversao_tab = ConversaoTab()
        self.config_tab = ConfigTab()
        self.logs_tab = LogsTab()
        set_log_tab_instance(self.logs_tab)
        self.tabs.addTab(self.transcricao_tab, "Transcrição")
        self.tabs.addTab(self.conversao_tab, "Conversão")
        self.tabs.addTab(self.config_tab, "Configurações")
        self.tabs.addTab(self.logs_tab, "Logs")
        self.tabs.addTab(SobreTab(), "Sobre")
        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(self.atualizar_aba_transcricao)

    def atualizar_aba_transcricao(self, idx):
        if self.tabs.widget(idx) == self.transcricao_tab:
            self.transcricao_tab.atualizar_config_interface()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(get_dark_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())