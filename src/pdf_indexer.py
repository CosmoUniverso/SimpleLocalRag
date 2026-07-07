import sqlite3
from pathlib import Path
import pdfplumber
import docx
from src.config import DB_PATH

class FileIndexer:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def _ensure_chunk_index_column(self, cursor):
        cursor.execute("PRAGMA table_info(chunks)")
        columns = {row[1] for row in cursor.fetchall()}
        if "chunk_index" not in columns:
            cursor.execute("ALTER TABLE chunks ADD COLUMN chunk_index INTEGER")

    def clear_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM chunks")
        conn.commit()
        conn.close()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT NOT NULL,
                page_number INTEGER,
                chunk_index INTEGER,
                text TEXT NOT NULL
            )
        """)
        self._ensure_chunk_index_column(c)
        conn.commit()
        conn.close()

    def remove_file(self, file_path):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM chunks WHERE source_file = ?", (str(file_path),))
        conn.commit()
        conn.close()

    def index_pdf(self, file_path):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                text = text.strip()
                if text:
                    c.execute(
                        "INSERT INTO chunks (source_file, page_number, chunk_index, text) VALUES (?, ?, ?, ?)",
                        (str(file_path), page_num, page_num, text)
                    )

        conn.commit()
        conn.close()

    def index_txt(self, file_path):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        text = Path(file_path).read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            c.execute(
                "INSERT INTO chunks (source_file, page_number, chunk_index, text) VALUES (?, ?, ?, ?)",
                (str(file_path), None, 1, text)
            )

        conn.commit()
        conn.close()

    def index_docx(self, file_path):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        doc = docx.Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs]).strip()

        if text:
            c.execute(
                "INSERT INTO chunks (source_file, page_number, chunk_index, text) VALUES (?, ?, ?, ?)",
                (str(file_path), None, 1, text)
            )

        conn.commit()
        conn.close()

    def index_file(self, file_path):
        self.init_db()
        self.remove_file(file_path)

        ext = file_path.suffix.lower()

        if ext == ".pdf":
            self.index_pdf(file_path)
        elif ext == ".txt":
            self.index_txt(file_path)
        elif ext == ".docx":
            self.index_docx(file_path)
        else:
            print(f"Formato non supportato: {file_path}")
