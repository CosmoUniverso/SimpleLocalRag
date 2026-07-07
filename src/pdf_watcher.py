from pathlib import Path

class FileWatcher:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.state = {}

    def set_folder(self, folder):
        self.folder = Path(folder)
        self.state = {}

    def scan(self):
        changes = []

        for file in self.folder.glob("*.*"):
            if file.suffix.lower() not in [".pdf", ".txt", ".docx"]:
                continue

            mtime = file.stat().st_mtime
            if file not in self.state:
                self.state[file] = mtime
                changes.append(("new", file))
            elif self.state[file] != mtime:
                self.state[file] = mtime
                changes.append(("modified", file))

        deleted = [p for p in list(self.state) if not p.exists()]
        for p in deleted:
            changes.append(("deleted", p))
            del self.state[p]

        return changes
