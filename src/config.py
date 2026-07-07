import sys
from pathlib import Path


MODEL = "llama3.2:3b"
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"


def app_root() -> Path:
	if getattr(sys, "frozen", False):
		return Path(sys.executable).resolve().parent
	return Path(__file__).resolve().parent.parent


APP_ROOT = app_root()

PDF_FOLDER = str(APP_ROOT / "pdf_docs")      # cartella con i PDF sensibili
DB_PATH = str(APP_ROOT / "knowledge.db")
TOP_K = 4

SETTINGS_MODEL_FILE = str(APP_ROOT / "selected_model.txt")
SETTINGS_FOLDER_FILE = str(APP_ROOT / "selected_folder.txt")
