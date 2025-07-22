from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget, QLabel, QHBoxLayout
from erros_usuario import ler_erros_usuario, limpar_erros_usuario

class LogsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Erros recentes do sistema (transcrição/conversão):")
        self.lista_erros = QListWidget()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.lista_erros)

        botoes_layout = QHBoxLayout()
        self.btn_atualizar = QPushButton("Atualizar")
        self.btn_limpar = QPushButton("Limpar Logs")
        botoes_layout.addWidget(self.btn_atualizar)
        botoes_layout.addWidget(self.btn_limpar)
        self.layout.addLayout(botoes_layout)

        self.btn_atualizar.clicked.connect(self.atualizar_erros)
        self.btn_limpar.clicked.connect(self.limpar_erros)

        self.atualizar_erros()

    def atualizar_erros(self):
        self.lista_erros.clear()
        erros = ler_erros_usuario()
        if not erros:
            self.lista_erros.addItem("Nenhum erro recente registrado.")
        else:
            for erro in reversed(erros):
                self.lista_erros.addItem(f"[{erro['data']}] ({erro['tipo']}) {erro['mensagem']}")

    def limpar_erros(self):
        limpar_erros_usuario()
        self.atualizar_erros()