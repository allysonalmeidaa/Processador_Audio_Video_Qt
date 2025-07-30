import os
import sys
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

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
LOG_PATH = os.path.join(PASTA_SCRIPT, "output.log")

class LogSignal(QObject):
    log_message = pyqtSignal(str)

global_log_signal = LogSignal()

def adicionar_log(mensagem):
    """Adiciona uma mensagem ao log com timestamp e emite o sinal para atualizar a aba."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = f"{timestamp} - {mensagem.strip()}"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(linha + "\n")
    global_log_signal.log_message.emit(linha)

class LogsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.label = QLabel("Logs do programa:")
        self.label.setStyleSheet("font-size:13px; font-weight:bold;")
        layout.addWidget(self.label)
        self.text_log = QPlainTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setMaximumBlockCount(1000)
        self.text_log.setObjectName("ConsoleLog")  # Adiciona o objectName para o CSS global agir
        layout.addWidget(self.text_log)
        self.btn_salvar = QPushButton("Salvar logs em arquivo")
        self.btn_salvar.clicked.connect(self.salvar_logs)
        layout.addWidget(self.btn_salvar)
        self.btn_limpar = QPushButton("Limpar logs")
        self.btn_limpar.clicked.connect(self.limpar_logs)
        layout.addWidget(self.btn_limpar)
        self.setLayout(layout)

        global_log_signal.log_message.connect(self.adicionar_log)
        self.carregar_log_inicial()

    def adicionar_log(self, mensagem):
        self.text_log.appendPlainText(mensagem)

    def carregar_log_inicial(self):
        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                self.text_log.setPlainText(f.read())
        else:
            self.text_log.setPlainText("Nenhum log encontrado.")

    def salvar_logs(self):
        if os.path.exists(LOG_PATH):
            caminho, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar logs como...",
                "output.log",
                "Log Files (*.log);;Text Files (*.txt);;All Files (*)"
            )
            if caminho:
                with open(LOG_PATH, "r", encoding="utf-8") as src, open(caminho, "w", encoding="utf-8") as dst:
                    dst.write(src.read())

    def limpar_logs(self):
        resposta = QMessageBox.question(
            self,
            "Confirmar limpeza",
            "Tem certeza que deseja limpar todos os logs?\nEssa ação não poderá ser desfeita.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resposta == QMessageBox.StandardButton.Yes:
            with open(LOG_PATH, "w", encoding="utf-8") as f:
                f.write("")
            self.text_log.setPlainText("")