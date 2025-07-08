import sys
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QHBoxLayout, QMessageBox, QSpinBox, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor, QIcon
from Transcricao_tab_V3 import TranscricaoTab
from Transcricao_conversão_tab_V3 import ConversaoTab

PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PASTA_SCRIPT, "config.json")
IDIOMAS = [
    ("auto", "Detectar automático"),
    ("pt", "Português"),
    ("en", "Inglês"),
    ("es", "Espanhol"),
    ("fr", "Francês"),
    ("de", "Alemão"),
]

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
        self.input_dir_saida = QLineEdit(self.config.get("dir_saida_conversao", "saida_audio"))
        form.addRow("Pasta saída conversão:", self.input_dir_saida)
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
        novo_config["dir_saida_conversao"] = self.input_dir_saida.text().strip() or "saida_audio"
        salvar_config(novo_config)
        self.config = novo_config
        QMessageBox.information(self, "Configurações", "Configurações salvas com sucesso!")

class SobreTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        lbl = QLabel(
            "<b>Transcrição com Whisper (Qt)</b><br>"
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
        self.setWindowTitle("Transcrição com Whisper (Qt)")
        icon_path = os.path.join(os.path.dirname(__file__), "microphone2.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setGeometry(200, 200, 1200, 700)
        self.tabs = QTabWidget()
        self.transcricao_tab = TranscricaoTab()
        self.conversao_tab = ConversaoTab()
        self.config_tab = ConfigTab()
        self.tabs.addTab(self.transcricao_tab, "Transcrição")
        self.tabs.addTab(self.conversao_tab, "Conversão")
        self.tabs.addTab(self.config_tab, "Configurações")
        self.tabs.addTab(SobreTab(), "Sobre")
        self.setCentralWidget(self.tabs)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(get_dark_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())