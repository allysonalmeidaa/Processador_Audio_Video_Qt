import os
import sys
import json
from PyQt6.QtWidgets import (
    QWidget, QLabel, QFileDialog, QVBoxLayout, QHBoxLayout,
    QCheckBox, QMessageBox, QPushButton, QLineEdit, QTextEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from Processamento_video import (
    processar_video, criar_diretorio_saida
)

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
CONFIG_PATH = os.path.join(PASTA_SCRIPT, "config.json")

class ConversaoWorker(QObject):
    finished = pyqtSignal(list)  # arquivos_convertidos
    log = pyqtSignal(str)

    def __init__(self, origem, formatos, diretorio_saida, parent_widget=None):
        super().__init__()
        self.origem = origem
        self.formatos = formatos
        self.diretorio_saida = diretorio_saida
        self.parent_widget = parent_widget

    def run(self):
        self.log.emit("Processando...\n")
        adicionar_log(f"Iniciando processamento de conversão: origem={self.origem}, formatos={self.formatos}")
        caminho_video, arquivos_gerados = processar_video(
            self.origem, self.diretorio_saida, self.formatos, parent_widget=self.parent_widget
        )
        if arquivos_gerados:
            self.log.emit("Arquivos gerados:")
            adicionar_log(f"Arquivos gerados: {', '.join(os.path.basename(a) for a in arquivos_gerados)}")
            for arquivo in arquivos_gerados:
                self.log.emit(os.path.basename(arquivo))
                adicionar_log(f"Arquivo convertido: {arquivo}")
            self.finished.emit(arquivos_gerados)
        else:
            self.log.emit("Erro: Nenhum arquivo foi gerado.")
            adicionar_log("Erro: Nenhum arquivo foi gerado na conversão.")
            self.finished.emit([])

class ConversaoTab(QWidget):
    def __init__(self):
        super().__init__()
        self.config = self.carregar_config()
        self.arquivos_convertidos = []

        layout = QVBoxLayout()
        hlayout_origem = QHBoxLayout()
        self.edit_origem = QLineEdit()
        self.edit_origem.setPlaceholderText("URL do vídeo ou caminho do arquivo local")
        hlayout_origem.addWidget(self.edit_origem)

        self.btn_selecionar_arquivo = QPushButton("Selecionar arquivo")
        self.btn_selecionar_arquivo.clicked.connect(self.selecionar_arquivo)
        hlayout_origem.addWidget(self.btn_selecionar_arquivo)
        layout.addLayout(hlayout_origem)

        lbl_formatos = QLabel("Formatos de saída desejados:")
        layout.addWidget(lbl_formatos)

        self.checkboxes = []
        # NOVA ORDEM E OPÇÕES: índice, label, id_interno
        self.formatos = [
            ("1", "Vídeo original (MP4)"),
            ("2", "Áudio original (MP3)"),
            ("3", "Padrão Telefonia (WAV 8kHz)"),
            ("4", "Alta Qualidade (FLAC 96kHz)"),
            ("5", "Podcast (M4A)"),
            ("6", "Streaming (OGG)"),
            ("7", "Rádio FM (WAV)"),
            ("8", "WhatsApp (OGG/OPUS)"),
        ]
        for idx, text in self.formatos:
            cb = QCheckBox(text)
            self.checkboxes.append(cb)
            layout.addWidget(cb)

        self.btn_converter = QPushButton("Processar")
        self.btn_converter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_converter.clicked.connect(self.converter)
        layout.addWidget(self.btn_converter)

        self.text_saida = QTextEdit()
        self.text_saida.setReadOnly(True)
        self.text_saida.setMinimumHeight(120)
        self.text_saida.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.text_saida)

        self.btn_baixar = QPushButton("Baixar Arquivo(s) Convertido(s)")
        self.btn_baixar.clicked.connect(self.baixar_arquivos)
        layout.addWidget(self.btn_baixar)

        self.setLayout(layout)

        self.thread = None
        self.worker = None

    def carregar_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def selecionar_arquivo(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Selecione um arquivo de áudio ou vídeo",
            "", "Áudio/Vídeo (*.mp3 *.mp4 *.wav *.m4a *.ogg *.flac)"
        )
        if fname:
            self.edit_origem.setText(fname)
            adicionar_log(f"Arquivo selecionado para conversão: {fname}")

    def converter(self):
        self.text_saida.clear()
        origem = self.edit_origem.text().strip()
        if not origem:
            QMessageBox.warning(self, "Aviso", "Informe a origem (URL ou arquivo local).")
            adicionar_log("Tentativa de conversão sem origem informada.")
            return

        # Identificadores (veja Processamento_video.py)
        formatos = [f[0] for f, cb in zip(self.formatos, self.checkboxes) if cb.isChecked()]
        if not formatos:
            QMessageBox.warning(self, "Aviso", "Selecione pelo menos um formato de saída.")
            adicionar_log("Tentativa de conversão sem formatos selecionados.")
            return

        diretorio_saida = os.path.join(get_app_dir(), "saida_audio")
        if not os.path.exists(diretorio_saida):
            os.makedirs(diretorio_saida, exist_ok=True)
            adicionar_log(f"Diretório de saída criado: {diretorio_saida}")

        self.btn_converter.setEnabled(False)
        self.btn_baixar.setEnabled(False)
        self.btn_selecionar_arquivo.setEnabled(False)
        for cb in self.checkboxes:
            cb.setEnabled(False)
        self.edit_origem.setEnabled(False)
        adicionar_log("Processamento de conversão iniciado.")

        self.thread = QThread()
        self.worker = ConversaoWorker(origem, formatos, diretorio_saida, parent_widget=self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.conversao_finalizada)
        self.worker.log.connect(self.text_saida.append)
        self.worker.log.connect(adicionar_log)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def conversao_finalizada(self, arquivos_gerados):
        self.arquivos_convertidos = arquivos_gerados
        self.btn_converter.setEnabled(True)
        self.btn_baixar.setEnabled(True)
        self.btn_selecionar_arquivo.setEnabled(True)
        for cb in self.checkboxes:
            cb.setEnabled(True)
        self.edit_origem.setEnabled(True)
        if arquivos_gerados:
            adicionar_log("Conversão finalizada com sucesso.")
        else:
            adicionar_log("Conversão finalizada sem arquivos gerados.")

    def baixar_arquivos(self):
        if not self.arquivos_convertidos:
            QMessageBox.information(self, "Baixar Arquivo(s)", "Nenhum arquivo convertido disponível para baixar.")
            adicionar_log("Tentativa de download sem arquivos convertidos disponíveis.")
            return
        target_dir = QFileDialog.getExistingDirectory(self, "Selecione a pasta para salvar os arquivos")
        if not target_dir:
            adicionar_log("Download cancelado: pasta de destino não selecionada.")
            return
        import shutil
        for arquivo in self.arquivos_convertidos:
            try:
                shutil.copy(arquivo, target_dir)
                adicionar_log(f"Arquivo copiado para {target_dir}: {arquivo}")
            except Exception as e:
                QMessageBox.warning(self, "Erro ao copiar arquivo", f"Falha ao copiar {arquivo}: {str(e)}")
                adicionar_log(f"Erro ao copiar {arquivo} para {target_dir}: {str(e)}")
        QMessageBox.information(self, "Download concluído", "Arquivo(s) copiado(s) com sucesso!")
        adicionar_log(f"Download concluído para pasta: {target_dir}")