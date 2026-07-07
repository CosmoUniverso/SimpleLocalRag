# Guida installazione Windows

Questa guida è pensata per lavorare in locale, senza inviare i documenti fuori dal PC.

## Hardware consigliato

La macchina indicata è adatta a un RAG locale leggero:

- CPU: Intel i7-9750H
- GPU: GTX 1050 da 3 GB VRAM
- RAM: 32 GB

La scelta pratica è usare un modello da 3B con Ollama. La GPU può essere usata quando basta, ma con 3 GB di VRAM è normale che il sistema cada su CPU per molti carichi.

## 1. Installa Ollama

Scarica Ollama da qui:

- [Download Windows](https://ollama.com/download/OllamaSetup.exe)
- [Pagina download ufficiale](https://ollama.com/download)

Installa il programma e verifica che funzioni aprendo un terminale e lanciando:

```powershell
ollama --version
```

## 2. Scarica un modello locale

Per il tuo hardware, usa prima uno di questi:

- `llama3.2:3b`
- `qwen2.5:3b`
- `phi3:mini`

Comandi:

```powershell
ollama pull llama3.2:3b
ollama pull qwen2.5:3b
ollama pull phi3:mini
```

Link utili:

- [Llama 3.2](https://ollama.com/library/llama3.2)
- [Qwen2.5](https://ollama.com/library/qwen2.5)
- [Phi-3](https://ollama.com/library/phi3)

## 3. Crea l'ambiente Python

Dentro la cartella del progetto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Se NLTK dovesse chiedere dati aggiuntivi, puoi installarli con:

```powershell
python -m nltk.downloader popular
```

## 4. Avvia l'app in locale

```powershell
.\.venv\Scripts\python.exe src\main.py
```

## 5. Usa la cartella documenti

Nella UI premi `Scegli cartella` e punta alla directory che contiene i PDF o i file di testo.

Poi premi `Aggiorna database PDF` per indicizzare il contenuto.

## 6. Scegli il modello

La UI mostra solo i modelli già scaricati in Ollama. Usa la casella di ricerca per filtrare e seleziona quello che vuoi.

## 7. Come scaricarlo e usarlo senza comandi

Per chi lo riceve, il flusso deve essere questo:

1. scarica il pacchetto `SimpleLocalRag-v0.1.4-portable.zip`
2. estrailo in una cartella qualsiasi
3. fai doppio clic su `SimpleLocalRag-v0.1.4.exe`

Non servono PowerShell, cmd o Python.

Se l'utente non ha ancora Ollama, deve installarlo una sola volta dal sito ufficiale e scaricare almeno un modello locale tra quelli consigliati sopra. Dopo di che, il programma si apre con il doppio clic.

## 8. Compila il pacchetto portable

Questa parte serve solo a chi prepara la distribuzione.

Installa prima `PyInstaller` con `pip install -r requirements.txt`, poi esegui:

```powershell
.\build_windows.ps1
```

Il pacchetto condivisibile sarà `SimpleLocalRag-v0.1.4-portable.zip` e dentro troverai la cartella pronta da aprire con doppio clic.

## 9. Domande frequenti

### Si può scegliere la cartella che si vuole?

Sì. Nella UI premi `Scegli cartella` e puoi puntare a qualunque cartella locale che contenga PDF, TXT o DOCX.

### Il programma è portable?

Sì. Il pacchetto è portable: non richiede installazione nel sistema, basta estrarlo e avviare l'eseguibile.

### Quindi ogni volta deve reindicizzare i file?

No. La reindicizzazione serve solo quando cambi cartella, aggiungi, modifichi o elimini documenti. Se non cambia nulla, non serve rifare l'indicizzazione.

### Le fonti possono indicare nome file e paragrafo?

Sì, in parte. Le fonti mostrano sempre il nome del file e, quando disponibile, anche la pagina e un indice del blocco/paragrafo estratto.

## 10. Note di sicurezza

- Tieni i documenti su disco locale.
- Non configurare integrazioni cloud.
- Se vuoi il massimo isolamento, blocca l'accesso internet dell'app e lascia solo il traffico verso `127.0.0.1` per Ollama.
