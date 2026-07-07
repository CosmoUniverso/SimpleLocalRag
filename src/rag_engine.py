import sqlite3
import re
import subprocess
import urllib.request
import time
import platform
from pathlib import Path
from nltk.stem.snowball import ItalianStemmer

from src.config import MODEL, OLLAMA_TAGS_URL, DB_PATH, TOP_K

stemmer = ItalianStemmer()

ITALIAN_STOPWORDS = {
    "a", "ad", "al", "allo", "ai", "agli", "all", "alla", "alle", "con", "col", "coi",
    "da", "dal", "dallo", "dai", "dagli", "dalla", "dalle", "di", "del", "dello", "dei",
    "degli", "della", "delle", "e", "ed", "in", "nel", "nello", "nei", "negli", "nella",
    "nelle", "su", "sul", "sullo", "sui", "sugli", "sulla", "sulle", "per", "tra", "fra",
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "ma", "o", "ed", "che", "chi",
    "cui", "come", "dove", "quando", "quanto", "quale", "quali", "qual", "se", "si", "no",
    "non", "piu", "meno", "anche", "solo", "sempre", "mai", "poi", "già", "gia", "qui",
    "lì", "li", "là", "la", "ne", "ci", "mi", "ti", "vi", "lo", "la", "gli", "le", "un", "una",
    "del", "della", "delle", "dei", "degli", "dell", "nell", "sull", "tale", "tali", "questo",
    "questa", "questi", "queste", "quello", "quella", "quelli", "quelle", "esso", "essa", "essi",
    "esse", "sono", "sei", "era", "erano", "essere", "avere", "ha", "hanno", "hai", "ho", "abbiamo",
    "avete", "fare", "fai", "fa", "fanno", "fatto", "molto", "molta", "molti", "molte", "poco",
    "poca", "pochi", "poche", "più", "piu", "meno", "tra", "fra", "perché", "perche", "perche", "etc"
}

BOT_IDENTITY = """
Ti chiami Vivo.
Parli in italiano.
Rispondi solo usando le informazioni presenti nel testo fornito.
Se la risposta non è presente nei dati disponibili, scrivi esattamente: "Non ho informazioni sufficienti".
"""

BOT_RULES = """
Regole:
- Rispondi in modo chiaro, naturale e coerente con la domanda.
- Se la domanda è semplice, rispondi in modo breve.
- Se la domanda richiede più dettagli, puoi rispondere in modo più esteso.
- Riformula con parole tue.
- Non copiare frasi intere dal testo, salvo casi strettamente necessari.
- Non includere parti non rilevanti.
- Non inventare informazioni.
- Non aggiungere conoscenze esterne.
- Evita errori ortografici e usa un italiano corretto.
"""


def is_ollama_running():
    try:
        req = urllib.request.Request(
            OLLAMA_TAGS_URL,
            headers={"User-Agent": "RAGLocal/1.0"}
        )
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def ensure_ollama_running():
    if is_ollama_running():
        return

    popen_kwargs = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True
    }

    if platform.system() == "Windows":
        popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    subprocess.Popen(["ollama", "serve"], **popen_kwargs)

    for _ in range(20):
        if is_ollama_running():
            return
        time.sleep(1)

    raise RuntimeError("Ollama non si è avviato sulla porta 11434")


def remove_ansi_escape_sequences(text):
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)


def ask_ollama(prompt: str, model: str = MODEL) -> str:
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="ignore").strip()
        err = remove_ansi_escape_sequences(err)
        return f"Errore nella generazione della risposta: {err or 'comando fallito'}"

    output = result.stdout.decode("utf-8", errors="ignore").strip()
    output = remove_ansi_escape_sequences(output)

    if not output:
        err = result.stderr.decode("utf-8", errors="ignore").strip()
        err = remove_ansi_escape_sequences(err)
        return f"Errore nella generazione della risposta: {err or 'output vuoto'}"

    return output


def normalize(text: str):
    text = text.lower()
    text = re.sub(r"[^a-zàèéìòùç0-9 ]", " ", text)
    words = text.split()
    stems = []
    for word in words:
        if len(word) <= 2:
            continue
        if word in ITALIAN_STOPWORDS:
            continue
        stems.append(stemmer.stem(word))
    return stems


def chunk_score(query_words, chunk_words):
    if not query_words or not chunk_words:
        return 0

    query_set = set(query_words)
    chunk_set = set(chunk_words)
    overlap = len(query_set & chunk_set)
    if overlap == 0:
        return 0

    length_penalty = max(1, len(chunk_set) // 80)
    return overlap / length_penalty


class RAGEngine:
    def __init__(self, db_path: str = DB_PATH, top_k: int = TOP_K):
        self.db_path = db_path
        self.top_k = top_k
        self.model = MODEL
        self._load_chunks()

    def set_model(self, model_name: str):
        self.model = model_name or MODEL

    def _load_chunks(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, source_file, page_number, text FROM chunks")
        rows = c.fetchall()
        conn.close()

        self.chunks = []
        self.normalized_chunks = []

        for row in rows:
            chunk_id, source_file, page_number, text = row
            self.chunks.append({
                "id": chunk_id,
                "source_file": source_file,
                "page_number": page_number,
                "text": text
            })
            self.normalized_chunks.append(normalize(text))

    def search_deterministic(self, query: str):
        q_words = normalize(query)
        if not q_words:
            return []

        scores = []

        for i, ch_words in enumerate(self.normalized_chunks):
            score = chunk_score(q_words, ch_words)
            if score > 0:
                ch = self.chunks[i]
                scores.append((score, ch))

        scores.sort(reverse=True, key=lambda x: x[0])

        results = []
        seen_ids = set()

        for score, ch in scores:
            if ch["id"] in seen_ids:
                continue
            results.append(ch)
            seen_ids.add(ch["id"])
            if len(results) >= self.top_k:
                break

        return results

    def has_enough_evidence(self, query: str, chunks):
        if not chunks:
            return False

        query_words = normalize(query)
        best_score = chunk_score(query_words, normalize(chunks[0]["text"]))

        if len(query_words) <= 4:
            return best_score >= 1

        return best_score >= 2

    def build_context(self, chunks):
        if not chunks:
            return "Nessuna informazione rilevante per questa domanda."

        blocks = []
        for ch in chunks:
            blocks.append(
                f"Fonte file: {ch['source_file']} (pagina {ch['page_number']})\nContenuto:\n{ch['text']}"
            )

        return "\n\n".join(blocks)

    def build_source_links(self, chunks):
        links = []
        seen_files = set()

        for ch in chunks:
            file_path = Path(ch["source_file"]).resolve()
            file_key = str(file_path).lower()
            if file_key in seen_files:
                continue
            seen_files.add(file_key)

            href = file_path.as_uri()

            if ch["page_number"]:
                href = f"{href}#page={ch['page_number']}"
                label = f"{file_path.name} - pagina {ch['page_number']}"
            else:
                label = file_path.name

            links.append(f'<a href="{href}">{label}</a>')

        return "<br>".join(links)

    def build_prompt(self, context: str, question: str):
        return f"""
{BOT_IDENTITY}

{BOT_RULES}

Testo disponibile:
{context}

Domanda: {question}

Risposta:
""".strip()

    def answer(self, question: str):
        ensure_ollama_running()

        chunks = self.search_deterministic(question)

        if not chunks or not self.has_enough_evidence(question, chunks):
            return "Non ho informazioni sufficienti", []

        context = self.build_context(chunks)
        prompt = self.build_prompt(context, question)
        response = ask_ollama(prompt, self.model)

        return response, chunks
