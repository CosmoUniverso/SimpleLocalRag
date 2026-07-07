from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QTextBrowser, QComboBox,
    QLineEdit, QFileDialog
)
from PyQt6.QtCore import Qt
import sys

class RAGWindow(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        self.setWindowTitle("RAG Locale - PDF")
        self.setGeometry(200, 200, 800, 600)

        layout = QVBoxLayout()

        # Cartella documenti
        self.folder_label = QLabel("Cartella documenti:")
        self.folder_path = QLineEdit()
        self.folder_path.setReadOnly(True)
        self.folder_path.setText(controller.get_documents_folder())
        self.folder_browse = QPushButton("Scegli cartella")
        self.folder_browse.clicked.connect(self.choose_folder)

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_path)
        folder_layout.addWidget(self.folder_browse)
        layout.addLayout(folder_layout)

        # Modello
        self.model_label = QLabel("Modello:")
        self.model_search = QLineEdit()
        self.model_search.setPlaceholderText("Cerca tra i modelli locali...")
        self.model_search.textChanged.connect(self.filter_models)
        self.model_select = QComboBox()
        self.all_models = controller.get_models()
        self.model_select.addItems(self.all_models)
        self.model_select.setCurrentText(controller.get_selected_model())
        self.model_select.currentTextChanged.connect(
            lambda m: controller.set_model(m)
        )

        self.refresh_models_btn = QPushButton("Aggiorna modelli")
        self.refresh_models_btn.clicked.connect(self.refresh_models)

        model_layout = QHBoxLayout()
        model_layout.addWidget(self.model_label)
        model_layout.addWidget(self.model_search)
        model_layout.addWidget(self.model_select)
        model_layout.addWidget(self.refresh_models_btn)
        layout.addLayout(model_layout)

        # Pulsante aggiornamento DB
        self.update_btn = QPushButton("Aggiorna database PDF")
        self.update_btn.clicked.connect(self.update_db)
        layout.addWidget(self.update_btn)

        # Domanda
        self.question_box = QTextEdit()
        self.question_box.setPlaceholderText("Scrivi la domanda...")
        layout.addWidget(self.question_box)

        # Pulsante invio
        self.ask_btn = QPushButton("Chiedi")
        self.ask_btn.clicked.connect(self.ask_question)
        layout.addWidget(self.ask_btn)

        # Risposta
        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)
        layout.addWidget(self.response_box)

        # Fonti
        self.sources_box = QTextBrowser()
        self.sources_box.setReadOnly(True)
        self.sources_box.setOpenExternalLinks(True)
        layout.addWidget(self.sources_box)

        self.setLayout(layout)

    def ask_question(self):
        question = self.question_box.toPlainText().strip()
        if not question:
            return

        response, chunks = self.controller.ask(question)

        self.response_box.setPlainText(response)

        if chunks:
            sources_html = self.controller.rag.build_source_links(chunks)
        else:
            sources_html = "<i>Nessuna fonte trovata.</i>"

        self.sources_box.setHtml(sources_html)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella documenti", self.controller.get_documents_folder())
        if not folder:
            return

        self.controller.set_documents_folder(folder)
        self.folder_path.setText(folder)
        self.response_box.setPlainText("Cartella documenti aggiornata. Premi 'Aggiorna database PDF' per reindicizzare.")

    def refresh_models(self):
        current_filter = self.model_search.text().strip().lower()
        self.all_models = self.controller.get_models()
        self.filter_models(current_filter)

    def filter_models(self, text):
        filtered = [model for model in self.all_models if text.lower() in model.lower()]
        current_model = self.controller.get_selected_model()

        self.model_select.blockSignals(True)
        self.model_select.clear()
        self.model_select.addItems(filtered)
        if current_model in filtered:
            self.model_select.setCurrentText(current_model)
        self.model_select.blockSignals(False)

    def update_db(self):
        changes = self.controller.update_db()
        txt = "\n".join(f"{c}: {f}" for c, f in changes)
        self.response_box.setPlainText("Aggiornamenti:\n" + txt)


def start_ui(controller):
    app = QApplication(sys.argv)
    window = RAGWindow(controller)
    window.show()
    sys.exit(app.exec())
