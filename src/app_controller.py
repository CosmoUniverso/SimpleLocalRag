from src.model_manager import ModelManager
from src.pdf_indexer import FileIndexer
from src.pdf_watcher import FileWatcher
from src.rag_engine import RAGEngine
from src.config import PDF_FOLDER, SETTINGS_FOLDER_FILE
from pathlib import Path

class AppController:
    def __init__(self):
        self.model_manager = ModelManager()
        self.indexer = FileIndexer()
        self.documents_folder = self._load_documents_folder()
        Path(self.documents_folder).mkdir(parents=True, exist_ok=True)
        self.watcher = FileWatcher(self.documents_folder)
        self.rag = RAGEngine()
        self.rag.set_model(self.model_manager.get_model())

    def _load_documents_folder(self):
        try:
            folder_path = Path(SETTINGS_FOLDER_FILE)
            if folder_path.exists():
                saved_folder = folder_path.read_text(encoding="utf-8").strip()
                if saved_folder:
                    return saved_folder
        except Exception:
            pass

        return PDF_FOLDER

    def get_models(self):
        return self.model_manager.list_models()

    def get_selected_model(self):
        return self.model_manager.get_model()

    def get_documents_folder(self):
        return self.documents_folder

    def set_documents_folder(self, folder_path):
        self.documents_folder = folder_path
        self.indexer.init_db()
        self.indexer.clear_db()
        self.watcher.set_folder(folder_path)
        Path(SETTINGS_FOLDER_FILE).write_text(folder_path, encoding="utf-8")

    def set_model(self, model):
        self.model_manager.set_model(model)
        self.rag.set_model(model)

    def update_db(self):
        changes = self.watcher.scan()
        for change, file in changes:
            if change in ("new", "modified"):
                self.indexer.index_file(file)
            elif change == "deleted":
                self.indexer.remove_file(file)
        self.rag._load_chunks()
        return [(c, str(f)) for c, f in changes]

    def ask(self, question):
        return self.rag.answer(question)
