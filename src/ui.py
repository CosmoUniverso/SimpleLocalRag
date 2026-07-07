import html
import sys

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class AskWorker(QObject):
    finished = pyqtSignal(str, list)
    error = pyqtSignal(str)

    def __init__(self, controller, question):
        super().__init__()
        self.controller = controller
        self.question = question

    def run(self):
        try:
            response, chunks = self.controller.ask(self.question)
        except Exception as exc:
            self.error.emit(str(exc))
            return

        self.finished.emit(response, chunks)


class UpdateWorker(QObject):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def run(self):
        try:
            changes = self.controller.update_db()
        except Exception as exc:
            self.error.emit(str(exc))
            return

        self.finished.emit(changes)


class RAGWindow(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.ask_thread = None
        self.ask_worker = None
        self.update_thread = None
        self.update_worker = None
        self.thinking_dots = 0

        self.setWindowTitle("RAG Locale - PDF")
        self.setGeometry(200, 200, 900, 720)

        layout = QVBoxLayout()

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

        self.model_label = QLabel("Modello:")
        self.model_search = QLineEdit()
        self.model_search.setPlaceholderText("Cerca tra i modelli locali...")
        self.model_search.textChanged.connect(self.filter_models)
        self.model_select = QComboBox()
        self.all_models = controller.get_models()
        self.model_select.addItems(self.all_models)
        self.model_select.setCurrentText(controller.get_selected_model())
        self.model_select.currentTextChanged.connect(lambda model: controller.set_model(model))

        self.refresh_models_btn = QPushButton("Aggiorna modelli")
        self.refresh_models_btn.clicked.connect(self.refresh_models)

        model_layout = QHBoxLayout()
        model_layout.addWidget(self.model_label)
        model_layout.addWidget(self.model_search)
        model_layout.addWidget(self.model_select)
        model_layout.addWidget(self.refresh_models_btn)
        layout.addLayout(model_layout)

        self.update_btn = QPushButton("Aggiorna database PDF")
        self.update_btn.clicked.connect(self.update_db)
        layout.addWidget(self.update_btn)

        self.update_progress = QProgressBar()
        self.update_progress.setVisible(False)
        self.update_progress.setRange(0, 0)
        layout.addWidget(self.update_progress)

        self.chat_history = QTextBrowser()
        self.chat_history.setReadOnly(True)
        self.chat_history.setOpenExternalLinks(False)
        self.chat_history.setMinimumHeight(320)
        self.chat_history.setHtml(
            "<div style='color:#666; font-style:italic;'>"
            "La conversazione apparirà qui."
            "</div>"
        )
        layout.addWidget(self.chat_history)

        self.question_box = QTextEdit()
        self.question_box.setPlaceholderText("Scrivi la domanda...")
        self.question_box.setFixedHeight(100)
        layout.addWidget(self.question_box)

        self.ask_btn = QPushButton("Chiedi")
        self.ask_btn.clicked.connect(self.ask_question)
        layout.addWidget(self.ask_btn)

        self.thinking_label = QLabel("")
        layout.addWidget(self.thinking_label)

        self.sources_label = QLabel("Fonti usate:")
        layout.addWidget(self.sources_label)

        self.sources_box = QTextBrowser()
        self.sources_box.setReadOnly(True)
        self.sources_box.setOpenExternalLinks(False)
        self.sources_box.anchorClicked.connect(self.open_source_link)
        self.sources_box.setMinimumHeight(210)
        layout.addWidget(self.sources_box)

        self.setLayout(layout)

        self.thinking_timer = QTimer(self)
        self.thinking_timer.timeout.connect(self.animate_thinking)

    def set_interaction_enabled(self, enabled):
        self.ask_btn.setEnabled(enabled)
        self.update_btn.setEnabled(enabled)
        self.folder_browse.setEnabled(enabled)
        self.refresh_models_btn.setEnabled(enabled)
        self.model_search.setEnabled(enabled)
        self.model_select.setEnabled(enabled)
        self.question_box.setEnabled(enabled)

    def append_chat_message(self, role, text, color):
        safe_text = html.escape(text).replace("\n", "<br>")
        block = (
            "<div style='margin:0 0 12px 0; padding:10px 12px; border-radius:10px; "
            "background:#f8fafc;'>"
            f"<div style='font-weight:700; color:{color}; margin-bottom:4px;'>{role}</div>"
            f"<div style='white-space:pre-wrap;'>{safe_text}</div>"
            "</div>"
        )
        self.chat_history.append(block)
        self.chat_history.verticalScrollBar().setValue(self.chat_history.verticalScrollBar().maximum())

    def append_system_message(self, text):
        safe_text = html.escape(text).replace("\n", "<br>")
        block = (
            "<div style='margin:0 0 12px 0; padding:10px 12px; border-radius:10px; "
            "background:#f1f5f9; color:#334155;'>"
            f"<div style='font-weight:700; margin-bottom:4px;'>Sistema</div>"
            f"<div style='white-space:pre-wrap;'>{safe_text}</div>"
            "</div>"
        )
        self.chat_history.append(block)
        self.chat_history.verticalScrollBar().setValue(self.chat_history.verticalScrollBar().maximum())

    def start_ask_worker(self, question):
        self.set_interaction_enabled(False)
        self.thinking_dots = 0
        self.thinking_label.setText("AI sta pensando")
        self.thinking_timer.start(400)

        self.ask_thread = QThread(self)
        self.ask_worker = AskWorker(self.controller, question)
        self.ask_worker.moveToThread(self.ask_thread)

        self.ask_thread.started.connect(self.ask_worker.run)
        self.ask_worker.finished.connect(self.on_ask_finished)
        self.ask_worker.error.connect(self.on_ask_error)
        self.ask_worker.finished.connect(self.ask_thread.quit)
        self.ask_worker.error.connect(self.ask_thread.quit)
        self.ask_thread.finished.connect(self.ask_worker.deleteLater)
        self.ask_thread.finished.connect(self.ask_thread.deleteLater)
        self.ask_thread.finished.connect(self.clear_ask_worker)

        self.ask_thread.start()

    def clear_ask_worker(self):
        self.ask_thread = None
        self.ask_worker = None

    def ask_question(self):
        question = self.question_box.toPlainText().strip()
        if not question:
            return

        self.append_chat_message("Tu", question, "#166534")
        self.question_box.clear()
        self.sources_box.setHtml("<i>In attesa della risposta...</i>")
        self.start_ask_worker(question)

    def on_ask_finished(self, response, chunks):
        self.thinking_timer.stop()
        self.thinking_label.setText("")
        self.append_chat_message("AI", response, "#1d4ed8")
        if chunks:
            self.sources_box.setHtml(self.controller.rag.build_source_links(chunks))
        else:
            self.sources_box.setHtml("<i>Nessuna fonte trovata.</i>")
        self.set_interaction_enabled(True)

    def on_ask_error(self, message):
        self.thinking_timer.stop()
        self.thinking_label.setText("")
        self.append_chat_message("AI", f"Errore: {message}", "#b91c1c")
        self.sources_box.setHtml("<i>Errore durante la generazione delle fonti.</i>")
        self.set_interaction_enabled(True)

    def animate_thinking(self):
        self.thinking_dots = (self.thinking_dots + 1) % 4
        self.thinking_label.setText("AI sta pensando" + ("." * self.thinking_dots))

    def start_update_worker(self):
        self.set_interaction_enabled(False)
        self.update_btn.setText("Indicizzazione in corso...")
        self.update_progress.setVisible(True)
        self.update_progress.setRange(0, 0)

        self.update_thread = QThread(self)
        self.update_worker = UpdateWorker(self.controller)
        self.update_worker.moveToThread(self.update_thread)

        self.update_thread.started.connect(self.update_worker.run)
        self.update_worker.finished.connect(self.on_update_finished)
        self.update_worker.error.connect(self.on_update_error)
        self.update_worker.finished.connect(self.update_thread.quit)
        self.update_worker.error.connect(self.update_thread.quit)
        self.update_thread.finished.connect(self.update_worker.deleteLater)
        self.update_thread.finished.connect(self.update_thread.deleteLater)
        self.update_thread.finished.connect(self.clear_update_worker)

        self.update_thread.start()

    def clear_update_worker(self):
        self.update_thread = None
        self.update_worker = None

    def update_db(self):
        self.start_update_worker()

    def on_update_finished(self, changes):
        self.update_progress.setVisible(False)
        self.update_btn.setText("Aggiorna database PDF")
        if changes:
            txt = "\n".join(f"{change}: {file_path}" for change, file_path in changes)
            self.append_system_message(f"Indicizzazione completata.\n{txt}")
        else:
            self.append_system_message("Indicizzazione completata. Nessuna modifica trovata.")
        self.set_interaction_enabled(True)

    def on_update_error(self, message):
        self.update_progress.setVisible(False)
        self.update_btn.setText("Aggiorna database PDF")
        self.append_system_message(f"Errore durante l'aggiornamento del database: {message}")
        self.set_interaction_enabled(True)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleziona cartella documenti",
            self.controller.get_documents_folder(),
        )
        if not folder:
            return

        self.controller.set_documents_folder(folder)
        self.folder_path.setText(folder)
        self.sources_box.setHtml("<i>Cartella documenti aggiornata. Reindicizza per usare il nuovo contenuto.</i>")
        self.append_system_message("Cartella documenti aggiornata. Premi 'Aggiorna database PDF' per reindicizzare.")

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

    def open_source_link(self, url):
        QDesktopServices.openUrl(url)


def start_ui(controller):
    app = QApplication(sys.argv)
    window = RAGWindow(controller)
    window.show()
    sys.exit(app.exec())
