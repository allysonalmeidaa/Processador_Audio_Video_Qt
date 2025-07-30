import os
import sys
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QLabel, QFileDialog, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPlainTextEdit, QComboBox, QMessageBox, QProgressBar, QListWidget,
    QLineEdit, QPushButton, QToolButton, QMenu
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QTextCursor, QIcon, QAction
from Transcricao_core_V3 import transcrever_com_diarizacao
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

class TranscricaoTextEdit(QTextEdit):
    fileDropped = pyqtSignal(str)
    fonteAlterada = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setReadOnly(True)
        self._tamanho_fonte = 14
        self.setProperty("tamanhoFonte", self._tamanho_fonte)
        self.setObjectName("TranscricaoTextEdit")
        self._apply_custom_style(self._tamanho_fonte)
        self._font_button = None
        self._create_font_size_button()
        self._setup_placeholder()

    def _setup_placeholder(self):
        self.setHtml("""
            <div style="text-align:center;margin-top:52px;">
                <span style="font-size:17px;font-weight:600;">
                    Arraste e solte um arquivo de áudio ou vídeo aqui
                </span><br>
                <span style="font-size:13px;">
                    ou veja aqui o texto transcrito.
                </span>
            </div>
        """)

    def _apply_custom_style(self, tamanho):
        self.setStyleSheet(f"""
            QTextEdit#TranscricaoTextEdit {{
                font-size: {tamanho}px;
                font-family: 'Segoe UI', Arial, sans-serif;
                padding: 18px;
            }}
        """)

    def setFontSize(self, tamanho):
        self._tamanho_fonte = tamanho
        self.setProperty("tamanhoFonte", tamanho)
        self._apply_custom_style(tamanho)
        self.fonteAlterada.emit(tamanho)

    def _create_font_size_button(self):
        self._font_button = QToolButton(self)
        self._font_button.setIcon(QIcon.fromTheme("format-font-size"))
        self._font_button.setText("Aa")
        self._font_button.setToolTip("Alterar tamanho da fonte da transcrição")
        self._font_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._font_button.setStyleSheet("""
            QToolButton {
                background: transparent;
                color: #b3bab7;
                font-size: 13px;
                padding: 2px 8px 2px 6px;
                border: none;
            }
            QToolButton:hover {
                color: #8fffa0;
            }
        """)
        font_menu = QMenu(self)
        for size in [12, 14, 16, 18, 20, 24]:
            act = QAction(f"{size}px", self)
            act.setData(size)
            act.triggered.connect(lambda checked, s=size: self.setFontSize(s))
            font_menu.addAction(act)
        self._font_button.setMenu(font_menu)
        self._font_button.setFixedSize(30, 22)
        self._font_button.raise_()
        self._font_button.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._font_button:
            m_top = 7
            m_right = 40
            btn_w, btn_h = self._font_button.width(), self._font_button.height()
            self._font_button.move(self.width() - btn_w - m_right, m_top)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    def dragLeaveEvent(self, event):
        event.accept()
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.mp3', '.mp4', '.wav', '.m4a', '.ogg', '.flac')):
                    self.fileDropped.emit(file_path)
                    break
        event.acceptProposedAction()

class TranscricaoThread(QThread):
    progresso = pyqtSignal(int, str, str)
    resultado = pyqtSignal(str)
    erro = pyqtSignal(str)
    cancelado = pyqtSignal()

    def __init__(self, caminho, modelo, idioma, log_callback=None):
        super().__init__()
        self.caminho = caminho
        self.modelo = modelo
        self.idioma = idioma
        self._cancelado = False
        self.log_callback = log_callback

    def cancelar(self):
        self._cancelado = True

    def run(self):
        try:
            def progresso_callback(valor, texto="", etapa=""):
                if self._cancelado:
                    raise Exception("Transcrição cancelada pelo usuário.")
                self.progresso.emit(valor, texto, etapa)
                if self.log_callback and texto:
                    self.log_callback(f"[{datetime.now().strftime('%H:%M:%S')}] {texto}")
            texto = transcrever_com_diarizacao(
                self.caminho, self.modelo, self.idioma,
                progresso_callback, checar_cancelamento=lambda: self._cancelado
            )
            if self._cancelado:
                self.cancelado.emit()
            else:
                self.resultado.emit(texto)
        except Exception as e:
            if self._cancelado:
                self.cancelado.emit()
            else:
                self.erro.emit(str(e))

class AnimatedProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._indeterminate = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
    def setIndeterminate(self, on=True):
        self._indeterminate = on
        if on:
            self.setRange(0, 0)
            self.timer.start(50)
        else:
            self.setRange(0, 100)
            self.timer.stop()
    def _tick(self):
        self.setFormat("Processando...")
    def setFormatWithStatus(self, status, percent=None):
        if percent is not None:
            self.setFormat(f"{status}  {percent}%")
        else:
            self.setFormat(f"{status}")

class TranscricaoTab(QWidget):
    def __init__(self):
        super().__init__()
        self.config = carregar_config()
        self.caminho_arquivo = ""
        layout_principal = QHBoxLayout()
        layout_esquerda = QVBoxLayout()
        layout_direita = QVBoxLayout()
        hlayout_top = QHBoxLayout()
        self.combo_modelos = QComboBox()
        self.combo_modelos.addItems(["tiny", "base", "small", "medium", "large"])
        self.combo_idioma = QComboBox()
        for cod, nome in IDIOMAS:
            self.combo_idioma.addItem(nome, cod)
        self.btn_abrir = QPushButton("Selecionar arquivo")
        self.btn_abrir.setMinimumWidth(140)
        self.btn_abrir.clicked.connect(self.selecionar_arquivo)
        hlayout_top.addWidget(QLabel("Modelo Whisper:"))
        hlayout_top.addWidget(self.combo_modelos)
        hlayout_top.addSpacing(12)
        hlayout_top.addWidget(QLabel("Idioma:"))
        hlayout_top.addWidget(self.combo_idioma)
        hlayout_top.addStretch(1)
        hlayout_top.addWidget(self.btn_abrir)
        layout_esquerda.addLayout(hlayout_top)
        self.label_arquivo = QLabel("Arquivo: nenhum selecionado")
        self.label_arquivo.setObjectName("ArquivoLabel")
        layout_esquerda.addWidget(self.label_arquivo)
        botoes_transcricao_layout = QHBoxLayout()
        self.btn_transcrever = QPushButton("Transcrever")
        self.btn_transcrever.clicked.connect(self.transcrever)
        self.btn_cancelar = QPushButton("Cancelar Transcrição")
        self.btn_cancelar.clicked.connect(self.cancelar_transcricao)
        self.btn_cancelar.setEnabled(False)
        botoes_transcricao_layout.addWidget(self.btn_transcrever)
        botoes_transcricao_layout.addWidget(self.btn_cancelar)
        layout_esquerda.addLayout(botoes_transcricao_layout)
        self.label_progresso = QLabel("Progresso:")
        self.label_progresso.setVisible(False)
        self.label_etapa = QLabel("")
        self.label_etapa.setVisible(False)
        hlayout_progresso = QHBoxLayout()
        hlayout_progresso.addWidget(self.label_progresso)
        hlayout_progresso.addStretch(1)
        hlayout_progresso.addWidget(self.label_etapa)
        layout_esquerda.addLayout(hlayout_progresso)
        self.progress = AnimatedProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        self.smooth_progress_timer = QTimer()
        self.smooth_progress_timer.timeout.connect(self._incrementar_progresso_suave)
        self.smooth_target = 0
        self.smooth_status = ""
        layout_esquerda.addWidget(self.progress)
        tamanho_fonte = self.config.get("tamanho_fonte_transcricao", 14)
        self.texto_transcricao = TranscricaoTextEdit()
        self.texto_transcricao.setObjectName("TranscricaoTextEdit")
        self.texto_transcricao.setFontSize(tamanho_fonte)
        self.texto_transcricao.fileDropped.connect(self.arquivo_arrastado)
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
        layout_direita.addWidget(self.busca_historico)
        layout_direita.addWidget(QLabel("Histórico de transcrições:"))
        self.lista_historico = QListWidget()
        self.lista_historico.itemClicked.connect(self.abrir_do_historico)
        layout_direita.addWidget(self.lista_historico)
        botoes_historico_layout = QVBoxLayout()
        self.btn_remover = QPushButton("Remover selecionado")
        self.btn_limpar = QPushButton("Limpar histórico")
        self.btn_remover.clicked.connect(self.remover_selecionado)
        self.btn_limpar.clicked.connect(self.limpar_historico)
        botoes_historico_layout.addWidget(self.btn_remover)
        botoes_historico_layout.addWidget(self.btn_limpar)
        layout_direita.addLayout(botoes_historico_layout)
        layout_direita.addWidget(QLabel("Console:"))
        self.console_log = QPlainTextEdit()
        self.console_log.setObjectName("ConsoleLog")
        self.console_log.setReadOnly(True)
        self.console_log.setMaximumBlockCount(300)
        layout_direita.addWidget(self.console_log)
        layout_direita.setStretch(2, 4)
        layout_direita.setStretch(5, 6)
        layout_principal.addLayout(layout_esquerda, 5)
        layout_principal.addLayout(layout_direita, 2)
        self.setLayout(layout_principal)
        self.thread = None
        self.carregar_historico()
        self.atualizar_config_interface()
        self.adicionar_log_console("Programa iniciado.")
        self.log_criacao_pastas_arquivos()

    def atualizar_tamanho_fonte_transcricao(self, tamanho):
        try:
            self.texto_transcricao.setFontSize(int(tamanho))
        except Exception:
            pass

    def adicionar_log_console(self, mensagem):
        self.console_log.appendPlainText(mensagem)
        self.console_log.moveCursor(QTextCursor.MoveOperation.End)
        adicionar_log(mensagem)

    def log_criacao_pastas_arquivos(self):
        created = []
        for pasta in ["Transcricoes", "saida_audio"]:
            path = os.path.join(PASTA_SCRIPT, pasta)
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
                created.append(pasta)
        for arq in ["config.json", "historico.json"]:
            path = os.path.join(PASTA_SCRIPT, arq)
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("[]" if arq == "historico.json" else "{}")
                created.append(arq)
        if created:
            self.adicionar_log_console(f"Criados: {', '.join(created)}")
        else:
            self.adicionar_log_console("Pastas e arquivos necessários já existem.")

    def carregar_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def atualizar_config_interface(self):
        self.config = self.carregar_config()
        modelo_salvo = self.config.get("modelo", "small")
        idx_modelo = self.combo_modelos.findText(modelo_salvo)
        if idx_modelo >= 0:
            self.combo_modelos.setCurrentIndex(idx_modelo)
        else:
            self.combo_modelos.setCurrentIndex(2)
        config_idioma = self.config.get("idioma", "auto")
        idx_idioma = 0
        for i, (cod, nome) in enumerate(IDIOMAS):
            if cod == config_idioma:
                idx_idioma = i
                break
        self.combo_idioma.setCurrentIndex(idx_idioma)
        self.config = self.carregar_config()

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
        try:
            tamanho_bytes = os.path.getsize(caminho)
            tamanho_mb = tamanho_bytes / (1024 * 1024)
        except Exception:
            tamanho_mb = 0
        aviso_mb = self.config.get("aviso_tamanho_mb", 300)
        if tamanho_mb > aviso_mb:
            resposta = QMessageBox.question(
                self,
                "Aviso: Arquivo grande",
                f"O arquivo selecionado possui mais de {aviso_mb} MB ({tamanho_mb:.1f} MB).\n"
                f"A transcrição pode demorar bastante tempo, dependendo do seu computador.\n\nDeseja continuar mesmo assim?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if resposta != QMessageBox.StandardButton.Yes:
                self.adicionar_log_console(f"Seleção de arquivo cancelada pelo usuário (tamanho: {tamanho_mb:.1f} MB).")
                return
        self.caminho_arquivo = caminho
        nome = os.path.basename(caminho)
        tamanho_str = f" ({tamanho_mb:.1f} MB)" if tamanho_mb else ""
        self.label_arquivo.setText(f'📎 Arquivo: {nome}{tamanho_str}')
        self.label_arquivo.setTextFormat(Qt.TextFormat.PlainText)
        self.adicionar_log_console(f"Arquivo selecionado: {nome}{tamanho_str}")

    def transcrever(self):
        if not self.caminho_arquivo:
            QMessageBox.warning(self, "Aviso", "Selecione um arquivo primeiro.")
            return
        modelo = self.combo_modelos.currentText()
        idioma = self.combo_idioma.currentData()

        # Ajuste para cor do texto conforme tema
        cor_progresso = "#b0f7b8"  # padrão para tema escuro
        config = self.config if hasattr(self, "config") else carregar_config()
        if config.get("tema", "escuro") == "claro":
            cor_progresso = "#186b2c"  # verde da borda do arquivo no tema claro

        self.texto_transcricao.setHtml(f"""
            <div style="color:{cor_progresso};font-size:17px;text-align:center;">
                Processando, aguarde...
            </div>
        """)
        self.label_progresso.setVisible(True)
        self.progress.setVisible(True)
        self.label_etapa.setVisible(True)
        self.progress.setIndeterminate(True)
        self.progress.setFormatWithStatus("Preparando", None)
        self.progress.setValue(0)
        self.smooth_target = 0
        self.smooth_status = "Preparando"
        self.smooth_progress_timer.start(40)
        self.repaint()
        self.adicionar_log_console(f"Iniciando transcrição ({os.path.basename(self.caminho_arquivo)})")
        self.thread = TranscricaoThread(
            self.caminho_arquivo, modelo, idioma, 
            log_callback=self.adicionar_log_console
        )
        self.thread.progresso.connect(self.atualizar_progresso_detalhado)
        self.thread.resultado.connect(self.exibir_transcricao)
        self.thread.erro.connect(self.exibir_erro)
        self.thread.cancelado.connect(self.tratamento_cancelado)
        self.btn_cancelar.setEnabled(True)
        self.thread.start()

    def atualizar_progresso_detalhado(self, valor, texto, etapa):
        if etapa:
            self.label_etapa.setText(etapa)
            self.smooth_status = etapa
        else:
            self.label_etapa.setText("Processando...")
            self.smooth_status = "Processando..."
        if valor is None or valor < 0:
            self.progress.setIndeterminate(True)
            self.progress.setFormatWithStatus(self.smooth_status)
        else:
            self.progress.setIndeterminate(False)
            self.smooth_target = valor
            self.progress.setFormatWithStatus(self.smooth_status, valor)
        if texto:
            self.adicionar_log_console(f"{texto}")

    def _incrementar_progresso_suave(self):
        atual = self.progress.value()
        if self.progress._indeterminate:
            return
        if atual < self.smooth_target:
            self.progress.setValue(atual + 1)
            self.progress.setFormatWithStatus(self.smooth_status, atual + 1)
        elif atual > self.smooth_target:
            self.progress.setValue(self.smooth_target)
            self.progress.setFormatWithStatus(self.smooth_status, self.smooth_target)
        if self.progress.value() >= 100:
            self.smooth_progress_timer.stop()

    def cancelar_transcricao(self):
        if self.thread and self.thread.isRunning():
            self.thread.cancelar()
            self.btn_cancelar.setEnabled(False)
            self.adicionar_log_console("Solicitado cancelamento da transcrição.")

    def tratamento_cancelado(self):
        self.progress.setVisible(False)
        self.label_progresso.setVisible(False)
        self.label_etapa.setVisible(False)
        self.btn_cancelar.setEnabled(False)
        self.progress.setIndeterminate(False)
        self.smooth_progress_timer.stop()
        # Destaque vermelho forte para ambos os temas, e bold
        config = self.config if hasattr(self, "config") else carregar_config()
        if config.get("tema", "escuro") == "claro":
            cor_cancelado = "#b20000"  # vermelho forte
            bg_cancelado = "#ffeaea"   # fundo muito claro só para tema claro
        else:
            cor_cancelado = "#ff6b6b"  # vermelho claro para escuro
            bg_cancelado = "transparent"

        self.texto_transcricao.setHtml(f"""
            <div style="color:{cor_cancelado};background:{bg_cancelado};font-size:16px;text-align:center;font-weight:bold;padding:10px 0;border-radius:6px;">
                Transcrição cancelada pelo usuário.
            </div>
        """)
        self.adicionar_log_console("Transcrição cancelada pelo usuário.")

    def exibir_transcricao(self, texto):
        self.texto_transcricao.setPlainText(texto)
        self.progress.setValue(100)
        self.progress.setVisible(False)
        self.label_progresso.setVisible(False)
        self.label_etapa.setVisible(False)
        self.btn_cancelar.setEnabled(False)
        self.progress.setIndeterminate(False)
        self.smooth_progress_timer.stop()
        self.adicionar_ao_historico()
        base = os.path.splitext(os.path.basename(self.caminho_arquivo))[0]
        caminho_trad = os.path.join(TRANSCRICOES_DIR, f"transcricao_{base}_ingles.txt")
        self.btn_download_traducao.setEnabled(os.path.exists(caminho_trad))
        self.adicionar_log_console("Transcrição finalizada com sucesso.")

    def exibir_erro(self, mensagem):
        self.texto_transcricao.setHtml(
            f'<div style="color:#ff7676;font-size:16px;"><b>Erro durante a transcrição:</b><br>{mensagem}</div>'
        )
        self.progress.setVisible(False)
        self.label_progresso.setVisible(False)
        self.label_etapa.setVisible(False)
        self.btn_cancelar.setEnabled(False)
        self.progress.setIndeterminate(False)
        self.smooth_progress_timer.stop()
        self.adicionar_log_console(f"Erro durante a transcrição: {mensagem}")

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
        self.adicionar_log_console(f"Transcrição adicionada ao histórico: {nome_transcricao}")

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
            self.adicionar_log_console(f"Erro ao salvar histórico: {e}")

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
            self.texto_transcricao.clear()
            self.texto_transcricao.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse)
            self.texto_transcricao.setPlainText(conteudo)
            self.adicionar_log_console(f"Transcrição do histórico carregada: {nome_arquivo}")
        else:
            QMessageBox.warning(self, "Aviso", "Arquivo de transcrição não encontrado!")
            self.adicionar_log_console(f"Arquivo do histórico não encontrado: {nome_arquivo}")

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
        self.adicionar_log_console(f"Entrada removida do histórico: {to_remove['nome']}")

    def limpar_historico(self):
        resp = QMessageBox.question(self, "Limpar histórico", "Tem certeza que deseja apagar todo o histórico?")
        if resp == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists(HISTORICO_PATH):
                    os.remove(HISTORICO_PATH)
                self.adicionar_log_console("Histórico de transcrições limpo.")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao apagar histórico: {str(e)}")
                self.adicionar_log_console(f"Erro ao apagar histórico: {e}")
            self.carregar_historico()

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
        self.adicionar_log_console(f"Transcrição salva como: {nome_sugestao}")

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
        self.adicionar_log_console(f"Tradução salva como: {nome_traducao}")

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