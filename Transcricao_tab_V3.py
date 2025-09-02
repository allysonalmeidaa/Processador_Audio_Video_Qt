import os
import sys
import json
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QLabel, QFileDialog, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPlainTextEdit, QComboBox, QMessageBox, QProgressBar,
    QListWidget, QLineEdit, QPushButton, QToolButton, QMenu
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QTextCursor, QIcon, QAction

# Importação segura do módulo de logs
try:
    from logs_tab import adicionar_log
except ImportError:
    def adicionar_log(mensagem):
        print(f"LOG: {mensagem}")


def get_app_dir():
    """Retorna o diretório do app, considerando empacotamento."""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.join(base_dir, "ProcessadorDeAudioVideo")
    if not os.path.exists(app_dir):
        os.makedirs(app_dir, exist_ok=True)
    return app_dir


# Caminhos globais
PASTA_SCRIPT = get_app_dir()
HISTORICO_PATH = os.path.join(PASTA_SCRIPT, "historico.json")
CONFIG_PATH = os.path.join(PASTA_SCRIPT, "config.json")
TRANSCRICOES_DIR = os.path.join(PASTA_SCRIPT, "Transcricoes")

# Criar pasta de transcrições se não existir
if not os.path.exists(TRANSCRICOES_DIR):
    os.makedirs(TRANSCRICOES_DIR, exist_ok=True)

# Idiomas suportados
IDIOMAS = [
    ("auto", "Detectar automático"),
    ("pt", "Português"),
    ("en", "Inglês"),
    ("es", "Espanhol"),
    ("fr", "Francês"),
    ("de", "Alemão"),
]


def carregar_config():
    """Carrega configuração do JSON."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def salvar_config(config):
    """Salva configuração no JSON."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


class TranscricaoTextEdit(QTextEdit):
    """Campo de texto personalizado com suporte a arrastar e soltar e botão de fonte."""
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
        """Texto inicial quando não há conteúdo."""
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
        """Aplica estilo com tamanho de fonte dinâmico."""
        self.setStyleSheet(f"""
            QTextEdit#TranscricaoTextEdit {{
                font-size: {tamanho}px;
                font-family: 'Segoe UI', Arial, sans-serif;
                padding: 18px;
            }}
        """)

    def setFontSize(self, tamanho):
        """Altera o tamanho da fonte."""
        self._tamanho_fonte = tamanho
        self.setProperty("tamanhoFonte", tamanho)
        self._apply_custom_style(tamanho)
        self.fonteAlterada.emit(tamanho)

    def _create_font_size_button(self):
        """Botão para alterar tamanho da fonte."""
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
        """Atualiza posição do botão de fonte ao redimensionar."""
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
    finished = pyqtSignal()

    def __init__(self, caminho, modelo, idioma, log_callback=None):
        super().__init__()
        self.caminho = caminho
        self.modelo = modelo
        self.idioma = idioma
        self._cancelado = False
        self.log_callback = log_callback

    def run(self):
        try:
            if self._cancelado:
                self.cancelado.emit()
                self.finished.emit()
                return
                
            self.progresso.emit(10, "Iniciando", "Preparando")
            if not os.path.exists(self.caminho):
                raise Exception("Arquivo não existe")
    
            self.progresso.emit(30, "Processando", "Transcrevendo")
            
            # EXECUTAR TRANSCRIÇÃO DIRETAMENTE
            resultado = self.executar_transcricao_direta(
                self.caminho,
                self.modelo,
                self.idioma
            )
            
            # VERIFICAR RESULTADO
            if not resultado.get("success", False):
                error_msg = resultado.get("error", "Erro desconhecido")
                raise Exception(f"Erro na transcrição: {error_msg}")
    
            self.progresso.emit(100, "Concluído", "Finalizado")
            self.resultado.emit(resultado["text"])
    
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[DEBUG] Erro no run(): {error_trace}")
            self.erro.emit(f"Erro: {str(e)}")
        finally:
            self.finished.emit()
    
    def executar_transcricao_direta(self, caminho_arquivo, modelo, idioma):
        """Função de transcrição direta - tudo em um só lugar"""
        try:
            print(f"[TRANSCRIÇÃO] Iniciando: {caminho_arquivo}")
            if not os.path.exists(caminho_arquivo):
                return {
                    "success": False,
                    "error": f"Arquivo não encontrado: {caminho_arquivo}"
                }
                
            # Configurações de ambiente
            os.environ['CUDA_VISIBLE_DEVICES'] = ''
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
            
            # IMPORTAÇÃO SEGURA - REMOVER QUALQUER MOCK EXISTENTE
            import sys
            for mod_name in list(sys.modules.keys()):
                if 'whisper' in mod_name or 'openai' in mod_name:
                    del sys.modules[mod_name]
            
            # Forçar importação limpa do Whisper
            import importlib
            importlib.invalidate_caches()
            
            # Importar whisper diretamente do sistema, não de mocks
            try:
                import whisper
                # Verificar se é o whisper real, não um mock
                if not hasattr(whisper, 'load_model') or not callable(whisper.load_model):
                    return {
                        "success": False,
                        "error": "Whisper inválido detectado (possível mock)"
                    }
            except ImportError:
                return {
                    "success": False,
                    "error": "Biblioteca whisper não encontrada. Instale com: pip install openai-whisper"
                }
            
            print(f"[TRANSCRIÇÃO] Bibliotecas importadas - Whisper real detectado")
            
            # Carregar modelo Whisper
            try:
                model = whisper.load_model(modelo)
                print(f"[TRANSCRIÇÃO] Modelo carregado: {modelo}")
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Erro ao carregar modelo: {str(e)}"
                }
            
            # Configurar argumentos de transcrição
            transcribe_args = {}
            if idioma and idioma != "auto":
                transcribe_args["language"] = idioma
                
            print(f"[TRANSCRIÇÃO] Iniciando transcrição...")
            
            # Fazer transcrição
            try:
                result = model.transcribe(caminho_arquivo, **transcribe_args, verbose=False)
                print(f"[TRANSCRIÇÃO] Transcrição concluída")
                
                # TENTAR DIARIZAÇÃO
                try:
                    print(f"[DIARIZAÇÃO] Iniciando diarização...")
                    from diarizacao_resemblyzer import diarize_audio
                    diarization = diarize_audio(caminho_arquivo, verbose=True)
                    print(f"[DIARIZAÇÃO] Diarização concluída: {len(diarization)} segmentos")
                    
                    # COMBINAR TRANSCRIÇÃO COM DIARIZAÇÃO (VERSÃO INTELIGENTE)
                    segments_combinados = []
                    ultimo_texto = ""
                    ultimo_speaker = ""
                    
                    for diar_start, diar_end, speaker in diarization:
                        segment_text = ""
                        # Coletar TODO o texto dos segmentos Whisper que se sobrepõem
                        for segment in result["segments"]:
                            whisper_start = segment["start"]
                            whisper_end = segment["end"]
                            # Verificar sobreposição (basta qualquer sobreposição)
                            if (whisper_start <= diar_end and whisper_end >= diar_start):
                                segment_text += " " + segment["text"].strip()
                        segment_text = segment_text.strip()
                        if segment_text:
                            speaker_label = f"Speaker {speaker.split('_')[-1]}" if speaker != "unknown" else "Speaker desconhecido"
                            # VERIFICAÇÃO INTELIGENTE DE REPETIÇÃO
                            is_repeticao = False
                            if segments_combinados:
                                # 1. Verifica se é repetição EXATA
                                if segment_text == ultimo_texto:
                                    is_repeticao = True
                                # 2. Verifica se é repetição PARCIAL (80% similar)
                                elif ultimo_texto and segment_text.startswith(ultimo_texto):
                                    is_repeticao = True

                                elif ultimo_texto and segment_text.endswith(ultimo_texto):
                                    is_repeticao = True

                                elif ultimo_texto and speaker_label == ultimo_speaker:
                                    palavras_atual = segment_text.lower().split()
                                    palavras_anterior = ultimo_texto.lower().split()

                                    if len(palavras_atual) > 3 and len(palavras_anterior) > 3:
                                        palavras_comuns = set(palavras_atual).intersection(palavras_anterior)
                                        similaridade = len(palavras_comuns) / min(len(palavras_atual), len(palavras_anterior))

                                        if similaridade > 0.8:
                                            is_repeticao = True

                                elif (len(segment_text.split()) <= 4 and
                                      segment_text in ultimo_texto):
                                    is_repeticao = True

                            # SE NÃO FOR REPETIÇÃO, adiciona ao resultado
                            if not is_repeticao:
                                segments_combinados.append({
                                    "speaker": speaker_label,
                                    "start": diar_start,
                                    "end": diar_end,
                                    "text": segment_text
                                })
                                ultimo_texto = segment_text
                                ultimo_speaker = speaker_label
                    
                    # Formatar texto final com timestamps
                    texto_final = "\n\n".join([
                        f"[{s['start']:.1f}s -> {s['end']:.1f}s] {s['speaker']}: {s['text']}" 
                        for s in segments_combinados
                    ])
                    
                    return {
                        "success": True,
                        "text": texto_final,
                        "language": result.get("language", "unknown"),
                        "diarization": segments_combinados,
                        "segments": result["segments"]
                    }
                    
                except ImportError as e:
                    print(f"[AVISO] Diarização não disponível: {e}")
                    # Fallback: retornar apenas transcrição sem diarização
                    return {
                        "success": True,
                        "text": result["text"],
                        "language": result.get("language", "unknown"),
                        "segments": result["segments"]
                    }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Erro durante transcrição: {str(e)}"
                }
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": f"Erro na transcrição: {str(e)}",
                "traceback": traceback.format_exc()
            }

    def cancel(self):
        """Método para cancelar a thread"""
        self._cancelado = True


class AnimatedProgressBar(QProgressBar):
    """Barra de progresso com animação suave."""
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
    """Aba principal de transcrição de áudio."""

    _whisper_loaded = False
    _import_error = None

    def __init__(self):
        super().__init__()
        self.config = carregar_config()
        self.caminho_arquivo = ""
        self.thread = None
        self._historico_cache = []

        self.setup_ui()

        QTimer.singleShot(1000, self.carregar_whisper_tardio)

    def setup_ui(self):
        # Layout principal
        layout_principal = QHBoxLayout()
        layout_esquerda = QVBoxLayout()
        layout_direita = QVBoxLayout()

        # Linha superior: seletores
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

        # Label do arquivo
        self.label_arquivo = QLabel("Arquivo: nenhum selecionado")
        self.label_arquivo.setObjectName("ArquivoLabel")
        layout_esquerda.addWidget(self.label_arquivo)

        # Botões de transcrição
        botoes_transcricao_layout = QHBoxLayout()
        self.btn_transcrever = QPushButton("Transcrever")
        self.btn_transcrever.clicked.connect(self.transcrever)
        self.btn_cancelar = QPushButton("Cancelar Transcrição")
        self.btn_cancelar.clicked.connect(self.cancelar_transcricao)
        self.btn_cancelar.setEnabled(False)
        botoes_transcricao_layout.addWidget(self.btn_transcrever)
        botoes_transcricao_layout.addWidget(self.btn_cancelar)
        layout_esquerda.addLayout(botoes_transcricao_layout)

        # Progresso
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

        # Área de transcrição
        tamanho_fonte = self.config.get("tamanho_fonte_transcricao", 14)
        self.texto_transcricao = TranscricaoTextEdit()
        self.texto_transcricao.setObjectName("TranscricaoTextEdit")
        self.texto_transcricao.setFontSize(tamanho_fonte)
        self.texto_transcricao.fileDropped.connect(self.arquivo_arrastado)
        layout_esquerda.addWidget(self.texto_transcricao)

        # Botões de download
        btns_download_layout = QHBoxLayout()
        self.btn_download_transcricao = QPushButton("Baixar Transcrição")
        self.btn_download_transcricao.clicked.connect(self.baixar_transcricao)
        btns_download_layout.addWidget(self.btn_download_transcricao)
        self.btn_download_traducao = QPushButton("Baixar Tradução (EN)")
        self.btn_download_traducao.clicked.connect(self.baixar_traducao)
        self.btn_download_traducao.setEnabled(False)
        btns_download_layout.addWidget(self.btn_download_traducao)
        btn_limpar_memoria = QPushButton("Limpar Memória")
        btn_limpar_memoria.clicked.connect(self.limpar_memoria)
        btns_download_layout.addWidget(btn_limpar_memoria)
        layout_esquerda.addLayout(btns_download_layout)

        # Histórico
        self.busca_historico = QLineEdit()
        self.busca_historico.setPlaceholderText("Buscar no histórico...")
        self.busca_historico.textChanged.connect(self.filtrar_historico)
        layout_direita.addWidget(self.busca_historico)
        layout_direita.addWidget(QLabel("Histórico de transcrições:"))
        self.lista_historico = QListWidget()
        self.lista_historico.itemClicked.connect(self.abrir_do_historico)
        layout_direita.addWidget(self.lista_historico)

        # Botões do histórico
        botoes_historico_layout = QVBoxLayout()
        self.btn_remover = QPushButton("Remover selecionado")
        self.btn_limpar = QPushButton("Limpar histórico")
        self.btn_remover.clicked.connect(self.remover_selecionado)
        self.btn_limpar.clicked.connect(self.limpar_historico)
        botoes_historico_layout.addWidget(self.btn_remover)
        botoes_historico_layout.addWidget(self.btn_limpar)
        layout_direita.addLayout(botoes_historico_layout)

        # Console
        layout_direita.addWidget(QLabel("Console:"))
        self.console_log = QPlainTextEdit()
        self.console_log.setObjectName("ConsoleLog")
        self.console_log.setReadOnly(True)
        self.console_log.setMaximumBlockCount(300)
        layout_direita.addWidget(self.console_log)

        layout_direita.setStretch(2, 4)
        layout_direita.setStretch(5, 6)

        # Monta layout
        layout_principal.addLayout(layout_esquerda, 5)
        layout_principal.addLayout(layout_direita, 2)
        self.setLayout(layout_principal)

        # Inicializa
        self.thread = None
        self.carregar_historico()
        self.atualizar_config_interface()
        self.adicionar_log_console("Programa iniciado.")
        self.log_criacao_pastas_arquivos()

    def carregar_whisper_tardio(self):
        """Carrega whisper após inicialização para evitar travamentos iniciais."""
        try:
            # Limpar qualquer mock existente
            import sys
            for mod_name in list(sys.modules.keys()):
                if 'whisper' in mod_name or 'openai' in mod_name:
                    del sys.modules[mod_name]
            
            import importlib
            importlib.invalidate_caches()
            
            import whisper
            self._whisper_loaded = True
            self.adicionar_log_console("Módulo Whisper carregado com sucesso.")
        except ImportError as e:
            self._import_error = f"Whisper não instalado. Execute: pip install openai-whisper"
            self.adicionar_log_console(f"Erro ao carregar Whisper: {self._import_error}")
        except Exception as e:
            self._import_error = str(e)
            self.adicionar_log_console(f"Erro ao carregar Whisper: {e}")

    def verificar_whisper_carregado(self):
        if not self._whisper_loaded:
            if self._import_error:
                QMessageBox.critical(self, "Erro", f"Erro ao carregar módulo Whisper:\n{self._import_error}")
            else:
                QMessageBox.critical(self, "Aguarde", "As bibliotecas de transcrição ainda estão sendo carregadas.")
            return False
        return True

    def closeEvent(self, event):
        """Encerra thread ao fechar."""
        if self.thread and self.thread.isRunning():
            self.thread.cancel()
            self.thread.quit()
            self.thread.wait()
        event.accept()

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
        self.adicionar_log_console(f"Arquivo selecionado: {nome}{tamanho_str}")

    def transcrever(self):
        if not self.caminho_arquivo:
            QMessageBox.warning(self, "Aviso", "Selecione um arquivo primeiro.")
            return
    
        if not self.verificar_whisper_carregado():
            return
    
        if not os.path.exists(self.caminho_arquivo):
            QMessageBox.warning(self, "Erro", f"Arquivo não encontrado: {self.caminho_arquivo}")
            return
    
        # Garantir que não há thread anterior rodando
        if self.thread and self.thread.isRunning():
            self.thread.cancel()
            self.thread.quit()
            self.thread.wait(1000)
        self.thread = None

        modelo = self.combo_modelos.currentText()
        idioma = self.combo_idioma.currentData()
    
        self.texto_transcricao.setHtml("<div style='color:#b0f7b8;font-size:17px;text-align:center;'>Processando, aguarde...</div>")
        self.label_progresso.setVisible(True)
        self.progress.setVisible(True)
        self.label_etapa.setVisible(True)
        self.progress.setIndeterminate(True)
        self.progress.setFormatWithStatus("Preparando", None)
        self.smooth_target = 0
        self.smooth_status = "Preparando"
        self.smooth_progress_timer.start(40)
    
        self.thread = TranscricaoThread(
            self.caminho_arquivo, modelo, idioma,
            log_callback=self.adicionar_log_console
        )
        self.thread.progresso.connect(self.atualizar_progresso_detalhado)
        self.thread.resultado.connect(self.exibir_transcricao)
        self.thread.erro.connect(self.exibir_erro)
        self.thread.cancelado.connect(self.tratamento_cancelado)
        self.thread.finished.connect(self.limpar_thread)
    
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
            self.thread.cancel()
            self.thread.quit()
            if not self.thread.wait(2000):
                self.thread.terminate()
                self.thread.wait()
        self.btn_cancelar.setEnabled(False)
        self.adicionar_log_console("Transcrição cancelada pelo usuário.")

    def limpar_thread(self):
        """Limpa a referência da thread após finalização"""
        if self.thread:
            self.thread.deleteLater()
            self.thread = None
        self.btn_cancelar.setEnabled(False)

    def limpar_memoria(self):
        """Limpeza manual de memória"""
        try: 
            import gc
            gc.collect()
            self.adicionar_log_console("Memória limpa manualmente.")
            QMessageBox.information(self, "Sucesso", "Memória limpa com sucesso.")
        except Exception as e:
            self.adicionar_log_console(f"Erro ao limpar memória: {e}")

    def tratamento_cancelado(self):
        self.progress.setVisible(False)
        self.label_progresso.setVisible(False)
        self.label_etapa.setVisible(False)
        self.btn_cancelar.setEnabled(False)
        self.progress.setIndeterminate(False)
        self.smooth_progress_timer.stop()
        self.texto_transcricao.setHtml("""
            <div style="color:#ff6b6b;font-size:16px;text-align:center;font-weight:bold;padding:10px 0;">
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
                    return json.load(f)
            except Exception:
                return []
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
        for h in self._historico_cache:
            nome = h['nome'].lower()
            data_str = h['data'].lower()
            idioma_str = h.get('idioma', 'auto')
            idioma_nome = next((n for c, n in IDIOMAS if c == idioma_str), idioma_str)
            if texto in nome or texto in data_str or texto in idioma_nome.lower():
                display = f"{h['nome']}  ({h['data']}, {idioma_nome})"
                self.lista_historico.addItem(display)

    def abrir_do_historico(self, item):
        idx = self.lista_historico.currentRow()
        if idx < 0 or idx >= len(self._historico_cache):
            return
        nome_arquivo = self._historico_cache[idx]["arquivo"]
        caminho = os.path.join(TRANSCRICOES_DIR, nome_arquivo)
        if os.path.exists(caminho):
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    conteudo = f.read()
                self.texto_transcricao.setPlainText(conteudo)
                self.adicionar_log_console(f"Transcrição do histórico carregada: {nome_arquivo}")
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Erro ao ler arquivo: {str(e)}")
        else:
            QMessageBox.warning(self, "Aviso", "Arquivo de transcrição não encontrado!")

    def remover_selecionado(self):
        idx = self.lista_historico.currentRow()
        if idx < 0 or idx >= len(self._historico_cache):
            return
        to_remove = self._historico_cache[idx]
        historico = self._ler_historico_arquivo()
        historico = [h for h in historico if h["arquivo"] != to_remove["arquivo"]]
        self._salvar_historico_arquivo(historico)
        self.carregar_historico()
        self.adicionar_log_console(f"Entrada removida do histórico: {to_remove['nome']}")

    def limpar_historico(self):
        resp = QMessageBox.question(self, "Limpar histórico", "Tem certeza que deseja apagar todo o histórico?")
        if resp == QMessageBox.StandardButton.Yes:
            try:
                with open(HISTORICO_PATH, "w", encoding="utf-8") as f:
                    json.dump([], f)
                self.adicionar_log_console("Histórico de transcrições limpo.")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao apagar histórico: {str(e)}")
            self.carregar_historico()

    def baixar_transcricao(self):
        texto = self.texto_transcricao.toPlainText()
        if not texto.strip():
            QMessageBox.warning(self, "Aviso", "Nenhuma transcrição para baixar.")
            return
        
        base = os.path.splitext(os.path.basename(self.caminho_arquivo))[0] if self.caminho_arquivo else "transcricao"
        nome_sugestao = f"transcricao_{base}.txt"
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
        
        try:
            with open(caminho_trad, "r", encoding="utf-8") as f:
                texto = f.read()
            self._salvar_com_dialogo(texto, nome_traducao)
            self.adicionar_log_console(f"Tradução salva como: {nome_traducao}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao ler tradução: {str(e)}")

    def _salvar_com_dialogo(self, texto, sugestao_nome):
        caminho, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar como...",
            sugestao_nome,
            "Text Files (*.txt);;All Files (*)"
        )
        if caminho:
            try:
                with open(caminho, "w", encoding="utf-8") as f:
                    f.write(texto)
                self.adicionar_log_console(f"Arquivo salvo: {caminho}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao salvar arquivo: {str(e)}")


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    janela = TranscricaoTab()
    janela.show()
    sys.exit(app.exec())