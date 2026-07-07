import subprocess

from src.config import MODEL, SETTINGS_MODEL_FILE

class ModelManager:
    def list_models(self):
        result = subprocess.run(
            ["ollama", "list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out = result.stdout.decode("utf-8")
        models = []
        for line in out.splitlines():
            if ":" in line:
                models.append(line.split()[0])
        return sorted(set(models))

    def set_model(self, model_name):
        with open(SETTINGS_MODEL_FILE, "w", encoding="utf-8") as f:
            f.write(model_name)

    def get_model(self):
        try:
            with open(SETTINGS_MODEL_FILE, encoding="utf-8") as f:
                return f.read().strip()
        except:
            return MODEL
