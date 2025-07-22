import os
import sys
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QLabel, QFileDialog, QVBoxLayout, QHBoxLayout,
    QTextEdit, QComboBox, QMessageBox, QProgressBar, QListWidget, QLineEdit, QPushButton
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from Transcricao_core_V3 import transcrever_com_diarizacao

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

PASTA_SCRIPT = get_app_dir()
HISTORICO_PATH = os.path.join(PASTA_SCRIPT, "historico.json")
CONFIG_PATH = os.path.join(PASTA_SCRIPT, "config.json")
TRANSCRICOES_DIR = os.path.join(PASTA_SCRIPT, "Transcricoes")

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

        hlayout = QHBoxLayout()
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setSpacing(10)
        self.label_modelo = QLabel("Modelo Whisper:")
        self.combo_modelos = QComboBox()
        self.combo_modelos.addItems(["tiny", "base", "small", "medium", "large"])
        self.label_idioma = QLabel("Idioma:")
        self.combo_idioma = QComboBox()
        for cod, nome in IDIOMAS:
            self.combo_idioma.addItem(nome, cod)
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

        self.drop_area = DropLabel()
        self.drop_area.setFixedHeight(40)
        self.drop_area.fileDropped.connect(self.arquivo_arrastado)
        layout_esquerda.addWidget(self.drop_area)

        self.texto_transcricao = QTextEdit()
        self.texto_transcricao.setReadOnly(True)
        self.texto_transcricao.setMinimumHeight(200)
        layout_esquerda.addWidget(self.texto_transcricao)

        btns_download_layout = QHBoxLayout()
        self.btn_download_transcricao = QPushButton("Baixar Transcrição")
        self.btn_download_transcricao.clicked.connect(self.baixar_transcricao)
        btns_download_layout.addWidget(self.btn_download_transcricao)
        self.btn_download_traducao = QPushButton("Baixar Tradução (EN)")
        self.btn_download_traducao.clicked.connect(self.baixar_traducao)
        btns_download_layout.addWidget(self.btn_download_traducao)
        self.btn_download_traducao.setEnabled(False)
        layout_esquerda.addLayout(btns_download_layout)

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

        self.carregar_historico()
        self.atualizar_config_interface()  # <--- Garante que modelo/idioma iniciais sejam os do config

    def carregar_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def atualizar_config_interface(self):
        """Atualiza combo_modelos e combo_idioma com base no config.json."""
        self.config = self.carregar_config()
        modelo_salvo = self.config.get("modelo", "small")
        idx_modelo = self.combo_modelos.findText(modelo_salvo)
        if idx_modelo >= 0:
            self.combo_modelos.setCurrentIndex(idx_modelo)
        else:
            self.combo_modelos.setCurrentIndex(2)  # "small"
        config_idioma = self.config.get("idioma", "auto")
        idx_idioma = 0
        for i, (cod, nome) in enumerate(IDIOMAS):
            if cod == config_idioma:
                idx_idioma = i
                break
        self.combo_idioma.setCurrentIndex(idx_idioma)

    def salvar_config(self, novo_config):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(novo_config, f, indent=2, ensure_ascii=False)
        self.config = novo_config
        self.atualizar_config_interface()

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
        base = os.path.splitext(os.path.basename(self.caminho_arquivo))[0]
        caminho_trad = os.path.join(TRANSCRICOES_DIR, f"transcricao_{base}_ingles.txt")
        self.btn_download_traducao.setEnabled(os.path.exists(caminho_trad))

    def exibir_erro(self, mensagem):
        self.texto_transcricao.setPlainText("Erro durante a transcrição:\n" + mensagem)
        self.progress.setVisible(False)
        self.label_status.setText("Erro!")

    def adicionar_ao_historico(self):
        base = os.path.splitext(os.path.basename(self.caminho_arquivo))[0]
        nome_transcricao = f"transcricao_{base}.txt"
        idioma_cod = self.combo_idioma.currentData()
        data = {
            "arquivo": nome_transcricao,
            "nome": nome_transcricao,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "idioma": idioma_cod
        }
        historico = self._ler_historico_arquivo()
        historico = [h for h in historico if h["arquivo"] != data["arquivo"]]
        historico.insert(0, data)
        max_itens = self.config.get("max_historico", 20)
        historico = historico[:max_itens]
        self._salvar_historico_arquivo(historico)
        self.carregar_historico()

    def carregar_historico(self):
        historico = self._ler_historico_arquivo()
        self._historico_cache = historico
        self.filtrar_historico(self.busca_historico.text())

    def _ler_historico_arquivo(self):
        if os.path.exists(HISTORICO_PATH):
            try:
                with open(HISTORICO_PATH, "r", encoding="utf-8") as f:
                    historico = json.load(f)
                    if isinstance(historico, list):
                        return historico
            except Exception:
                pass
        return []

    def _salvar_historico_arquivo(self, historico):
        try:
            with open(HISTORICO_PATH, "w", encoding="utf-8") as f:
                json.dump(historico, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar histórico: {str(e)}")

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
        nome_arquivo = filtrados[idx]["arquivo"]
        caminho = os.path.join(TRANSCRICOES_DIR, nome_arquivo)
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
        historico = self._ler_historico_arquivo()
        historico = [h for h in historico if h != to_remove]
        self._salvar_historico_arquivo(historico)
        self.carregar_historico()

    def limpar_historico(self):
        resp = QMessageBox.question(self, "Limpar histórico", "Tem certeza que deseja apagar todo o histórico?")
        if resp == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists(HISTORICO_PATH):
                    os.remove(HISTORICO_PATH)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao apagar histórico: {str(e)}")
            self.carregar_historico()

    # Funções de download
    def baixar_transcricao(self):
        if not self.caminho_arquivo:
            QMessageBox.warning(self, "Aviso", "Nenhuma transcrição para baixar.")
            return
        base = os.path.splitext(os.path.basename(self.caminho_arquivo))[0]
        nome_transcricao = f"transcricao_{base}.txt"
        caminho_transcr = os.path.join(TRANSCRICOES_DIR, nome_transcricao)
        if not os.path.exists(caminho_transcr):
            QMessageBox.warning(self, "Aviso", "Arquivo de transcrição não encontrado.")
            return
        with open(caminho_transcr, "r", encoding="utf-8") as f:
            texto = f.read()
        nome_sugestao = nome_transcricao
        self._salvar_com_dialogo(texto, nome_sugestao)

    def baixar_traducao(self):
        if not self.caminho_arquivo:
            QMessageBox.warning(self, "Aviso", "Nenhuma tradução para baixar.")
            return
        base = os.path.splitext(os.path.basename(self.caminho_arquivo))[0]
        nome_traducao = f"transcricao_{base}_ingles.txt"
        caminho_trad = os.path.join(TRANSCRICOES_DIR, nome_traducao)
        if not os.path.exists(caminho_trad):
            QMessageBox.warning(self, "Aviso", "Arquivo de tradução não encontrado.")
            return
        with open(caminho_trad, "r", encoding="utf-8") as f:
            texto = f.read()
        nome_sugestao = nome_traducao
        self._salvar_com_dialogo(texto, nome_sugestao)

    def _salvar_com_dialogo(self, texto, sugestao_nome):
        caminho, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar como...",
            sugestao_nome,
            "Text Files (*.txt);;All Files (*)"
        )
        if caminho:
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(texto)