import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QLabel, QFileDialog, QVBoxLayout, QHBoxLayout,
    QTextEdit, QComboBox, QMessageBox, QProgressBar, QListWidget, QLineEdit, QPushButton
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from Transcricao_core_V3 import transcrever_com_diarizacao

PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
HISTORICO_PATH = os.path.join(PASTA_SCRIPT, "historico.json")
CONFIG_PATH = os.path.join(PASTA_SCRIPT, "config.json")

IDIOMAS = [
    ("auto", "Detectar automático"),
    ("pt", "Português"),
    ("en", "Inglês"),
    ("es", "Espanhol"),
    ("fr", "Francês"),
    ("de", "Alemão"),
]

class DropLabel(QLabel):
    fileDropped = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Arraste e solte um arquivo de áudio ou vídeo aqui")
        # Fonte e tamanho padronizados (igual QLabel padrão)
        self.setStyleSheet("""
            QLabel {
                background: #2d3238;
                border: 1px solid #444;
                border-radius: 5px;
                color: #eee;
                font-style: normal;
                font-size: 13px;
                font-weight: normal;
                padding: 8px;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.mp3', '.mp4', '.wav', '.m4a', '.ogg', '.flac')):
                self.fileDropped.emit(file_path)
                break

class TranscricaoThread(QThread):
    progresso = pyqtSignal(int, str)
    resultado = pyqtSignal(str)
    erro = pyqtSignal(str)
    def __init__(self, caminho, modelo, idioma):
        super().__init__()
        self.caminho = caminho
        self.modelo = modelo
        self.idioma = idioma
    def run(self):
        try:
            def progresso_callback(valor, texto=""):
                self.progresso.emit(valor, texto)
            texto = transcrever_com_diarizacao(self.caminho, self.modelo, self.idioma, progresso_callback)
            self.resultado.emit(texto)
        except Exception as e:
            self.erro.emit(str(e))

class TranscricaoTab(QWidget):
    def __init__(self):
        super().__init__()
        self.config = self.carregar_config()
        self.caminho_arquivo = ""

        layout_principal = QHBoxLayout()
        layout_esquerda = QVBoxLayout()
        layout_direita = QVBoxLayout()
        layout_esquerda.setContentsMargins(8, 4, 4, 8)
        layout_esquerda.setSpacing(3)

        # Layout horizontal para modelo/idioma/arquivo
        hlayout = QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setSpacing(10)
        self.label_modelo = QLabel("Modelo Whisper:")
        self.combo_modelos = QComboBox()
        self.combo_modelos.addItems(["tiny", "base", "small", "medium", "large"])
        self.combo_modelos.setCurrentText(self.config.get("modelo", "small"))
        self.label_idioma = QLabel("Idioma:")
        self.combo_idioma = QComboBox()
        for cod, nome in IDIOMAS:
            self.combo_idioma.addItem(nome, cod)
        idx_idioma = 0
        config_idioma = self.config.get("idioma", "auto")
        for i, (cod, nome) in enumerate(IDIOMAS):
            if cod == config_idioma:
                idx_idioma = i
                break
        self.combo_idioma.setCurrentIndex(idx_idioma)
        hlayout.addWidget(self.label_modelo)
        hlayout.addWidget(self.combo_modelos)
        hlayout.addSpacing(10)
        hlayout.addWidget(self.label_idioma)
        hlayout.addWidget(self.combo_idioma)
        hlayout.addStretch(1)
        self.btn_abrir = QPushButton("Selecionar arquivo")
        self.btn_abrir.setMinimumWidth(170)
        self.btn_abrir.setMaximumWidth(220)
        self.btn_abrir.setMinimumHeight(32)
        self.btn_abrir.clicked.connect(self.selecionar_arquivo)
        hlayout.addWidget(self.btn_abrir)
        layout_esquerda.addLayout(hlayout)

        self.label_status = QLabel("Aguardando para começar.")
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_status.setFixedHeight(18)
        layout_esquerda.addWidget(self.label_status)

        self.label_arquivo = QLabel("Arquivo: nenhum selecionado")
        layout_esquerda.addWidget(self.label_arquivo)

        self.btn_transcrever = QPushButton("Transcrever")
        self.btn_transcrever.clicked.connect(self.transcrever)
        layout_esquerda.addWidget(self.btn_transcrever)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout_esquerda.addWidget(self.progress)

        # DropLabel padronizado
        self.drop_area = DropLabel()
        self.drop_area.setFixedHeight(40)
        self.drop_area.fileDropped.connect(self.arquivo_arrastado)
        layout_esquerda.addWidget(self.drop_area)

        self.texto_transcricao = QTextEdit()
        self.texto_transcricao.setReadOnly(True)
        self.texto_transcricao.setMinimumHeight(200)
        layout_esquerda.addWidget(self.texto_transcricao)

        # Lateral direita: busca + histórico
        self.busca_historico = QLineEdit()
        self.busca_historico.setPlaceholderText("Buscar no histórico...")
        self.busca_historico.textChanged.connect(self.filtrar_historico)
        self.label_historico = QLabel("Histórico de transcrições:")
        self.lista_historico = QListWidget()
        self.lista_historico.itemClicked.connect(self.abrir_do_historico)
        self.btn_remover = QPushButton("Remover selecionado")
        self.btn_limpar = QPushButton("Limpar histórico")
        self.btn_remover.clicked.connect(self.remover_selecionado)
        self.btn_limpar.clicked.connect(self.limpar_historico)

        layout_direita.addWidget(self.busca_historico)
        layout_direita.addWidget(self.label_historico)
        layout_direita.addWidget(self.lista_historico, 7)
        layout_direita.addWidget(self.btn_remover)
        layout_direita.addWidget(self.btn_limpar)
        layout_direita.setStretch(2, 7)
        layout_direita.setStretch(3, 0)
        layout_direita.setStretch(4, 0)

        layout_principal.addLayout(layout_esquerda, 4)
        layout_principal.addLayout(layout_direita, 2)
        self.setLayout(layout_principal)

        self.thread = None
        self._historico_cache = []
        self.carregar_historico()

    def carregar_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def salvar_config(self, novo_config):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(novo_config, f, indent=2, ensure_ascii=False)
        self.config = novo_config
        self.combo_modelos.setCurrentText(novo_config.get("modelo", "small"))
        idx_idioma = 0
        for i, (cod, nome) in enumerate(IDIOMAS):
            if cod == novo_config.get("idioma", "auto"):
                idx_idioma = i
                break
        self.combo_idioma.setCurrentIndex(idx_idioma)

    def selecionar_arquivo(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Selecione um arquivo de áudio ou vídeo",
            "", "Áudio/Vídeo (*.mp3 *.mp4 *.wav *.m4a *.ogg *.flac)"
        )
        if fname:
            self.setar_arquivo(fname)

    def arquivo_arrastado(self, file_path):
        self.setar_arquivo(file_path)

    def setar_arquivo(self, caminho):
        self.caminho_arquivo = caminho
        self.label_arquivo.setText(f"Arquivo: {os.path.basename(caminho)}")

    def transcrever(self):
        if not self.caminho_arquivo:
            QMessageBox.warning(self, "Aviso", "Selecione um arquivo primeiro.")
            return
        modelo = self.combo_modelos.currentText()
        idioma = self.combo_idioma.currentData()
        self.texto_transcricao.setPlainText("Processando, aguarde...\n")
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.label_status.setText("Iniciando processamento...")
        self.repaint()
        self.thread = TranscricaoThread(self.caminho_arquivo, modelo, idioma)
        self.thread.progresso.connect(self.atualizar_progresso_detalhado)
        self.thread.resultado.connect(self.exibir_transcricao)
        self.thread.erro.connect(self.exibir_erro)
        self.thread.start()

    def atualizar_progresso_detalhado(self, valor, texto):
        self.progress.setValue(valor)
        self.label_status.setText(texto)

    def exibir_transcricao(self, texto):
        self.texto_transcricao.setPlainText(texto)
        self.progress.setValue(100)
        self.progress.setVisible(False)
        self.label_status.setText("Pronto!")
        self.adicionar_ao_historico()

    def exibir_erro(self, mensagem):
        self.texto_transcricao.setPlainText("Erro durante a transcrição:\n" + mensagem)
        self.progress.setVisible(False)
        self.label_status.setText("Erro!")

    def adicionar_ao_historico(self):
        base = os.path.splitext(os.path.basename(self.caminho_arquivo))[0]
        pasta = os.path.dirname(os.path.abspath(__file__))
        caminho_transcr = os.path.join(pasta, "Transcricoes", f"transcricao_{base}.txt")
        idioma_cod = self.combo_idioma.currentData()
        data = {
            "arquivo": caminho_transcr,
            "nome": f"transcricao_{base}.txt",
            "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "idioma": idioma_cod
        }
        historico = []
        if os.path.exists(HISTORICO_PATH):
            try:
                with open(HISTORICO_PATH, "r", encoding="utf-8") as f:
                    historico = json.load(f)
            except Exception:
                historico = []
        historico = [h for h in historico if h["arquivo"] != data["arquivo"]]
        historico.insert(0, data)
        max_itens = self.config.get("max_historico", 20)
        historico = historico[:max_itens]
        with open(HISTORICO_PATH, "w", encoding="utf-8") as f:
            json.dump(historico, f, indent=2, ensure_ascii=False)
        self.carregar_historico()

    def carregar_historico(self):
        if os.path.exists(HISTORICO_PATH):
            try:
                with open(HISTORICO_PATH, "r", encoding="utf-8") as f:
                    historico = json.load(f)
                self._historico_cache = historico
            except Exception:
                self._historico_cache = []
        else:
            self._historico_cache = []
        self.filtrar_historico(self.busca_historico.text())

    def filtrar_historico(self, texto):
        texto = texto.strip().lower()
        self.lista_historico.clear()
        for h in getattr(self, '_historico_cache', []):
            nome = h['nome'].lower()
            data_str = h['data'].lower()
            idioma_str = h.get('idioma', 'auto')
            idioma_nome = next((n for c, n in IDIOMAS if c == idioma_str), idioma_str)
            if texto in nome or texto in data_str or texto in idioma_nome.lower():
                display = f"{h['nome']}  ({h['data']}, {idioma_nome})"
                self.lista_historico.addItem(display)

    def abrir_do_historico(self, item):
        idx = self.lista_historico.currentRow()
        filtrados = []
        texto = self.busca_historico.text().strip().lower()
        for h in getattr(self, '_historico_cache', []):
            nome = h['nome'].lower()
            data_str = h['data'].lower()
            idioma_str = h.get('idioma', 'auto')
            idioma_nome = next((n for c, n in IDIOMAS if c == idioma_str), idioma_str)
            if texto in nome or texto in data_str or texto in idioma_nome.lower():
                filtrados.append(h)
        if idx >= len(filtrados):
            return
        caminho = filtrados[idx]["arquivo"]
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                conteudo = f.read()
            self.texto_transcricao.setPlainText(conteudo)
        else:
            QMessageBox.warning(self, "Aviso", "Arquivo de transcrição não encontrado!")

    def remover_selecionado(self):
        idx = self.lista_historico.currentRow()
        texto = self.busca_historico.text().strip().lower()
        filtrados = []
        for h in getattr(self, '_historico_cache', []):
            nome = h['nome'].lower()
            data_str = h['data'].lower()
            idioma_str = h.get('idioma', 'auto')
            idioma_nome = next((n for c, n in IDIOMAS if c == idioma_str), idioma_str)
            if texto in nome or texto in data_str or texto in idioma_nome.lower():
                filtrados.append(h)
        if idx < 0 or idx >= len(filtrados):
            return
        to_remove = filtrados[idx]
        self._historico_cache = [h for h in self._historico_cache if h != to_remove]
        with open(HISTORICO_PATH, "w", encoding="utf-8") as f:
            json.dump(self._historico_cache, f, indent=2, ensure_ascii=False)
        self.carregar_historico()

    def limpar_historico(self):
        resp = QMessageBox.question(self, "Limpar histórico", "Tem certeza que deseja apagar todo o histórico?")
        if resp == QMessageBox.StandardButton.Yes:
            self._historico_cache = []
            if os.path.exists(HISTORICO_PATH):
                os.remove(HISTORICO_PATH)
            self.carregar_historico()