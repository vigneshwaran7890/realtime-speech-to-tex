# 🎙️ Real-time Speech to Text (Hindi + English)

A web application that transcribes speech **in real time** using the **Gemini Live API**.
Speak in Hindi, English or a mix of both (e.g. *"Kal meeting hai, please join on time"*) and the
words appear on screen as you talk. Every transcription is saved to a relational database and can be
managed from a **History Dashboard** with full **CRUD** (Create, Read, Update, Delete) operations.
Saved text can also be played back with **Text-to-Speech**.

**Built with:** Python · Streamlit · Gemini Live API · SQLAlchemy · SQLite / PostgreSQL · WebRTC · gTTS

---

## 📑 Table of Contents

1. [Features](#-features)
2. [Prerequisites](#-prerequisites)
3. [Installation](#-installation)
4. [Configuration](#-configuration)
5. [Running the App](#-running-the-app)
6. [How to Use](#-how-to-use)
7. [Running Tests](#-running-tests)
8. [Run with Docker](#-run-with-docker)
9. [Deploy to the Cloud](#-deploy-to-the-cloud-streamlit-community-cloud)
10. [Project Structure](#-project-structure)
11. [Architecture](#-architecture)
12. [Troubleshooting](#-troubleshooting)
13. [Command Cheat Sheet](#-command-cheat-sheet)

---

## ✨ Features

| Feature | Description |
| --- | --- |
| **Real-time transcription** | Microphone audio is streamed via WebRTC to Gemini Live (`gemini-3.5-transcribe-live`). Words appear live while you speak. |
| **Multilingual (Hinglish)** | *Hindi + English mix* mode writes code-mixed speech in Roman script. *Auto-detect* mode supports any language (Hindi in Devanagari). |
| **Clip mode** | Record a clip in the browser or upload an audio file (wav, mp3, m4a, ogg, webm, flac). |
| **Review before saving** | Edit the title and text before saving to the database, or discard. |
| **History Dashboard (CRUD)** | **Create** entries manually, **Read** with search, filters and stats, **Update** title/text/language, **Delete** with a confirmation dialog. |
| **Text-to-Speech** | Listen to any transcription (Hindi voice for Devanagari, Indian-English voice otherwise). |
| **Export** | Download a single transcription as `.txt` or the whole history as `.csv`. |
| **Long sessions** | Automatically reconnects before Gemini's 10-minute session limit without losing audio. |

---

## 🧰 Prerequisites

| Requirement | Version / Notes |
| --- | --- |
| **Python** | 3.10 or newer → check with `python --version` |
| **Git** | Any recent version |
| **Gemini API key** | Free from [Google AI Studio](https://aistudio.google.com/apikey) |
| **Browser** | Chrome, Edge or Firefox with microphone access |

---

## 📦 Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/<your-username>/realtime-speech-to-text.git
cd realtime-speech-to-text
```

### Step 2 — Create a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

> If PowerShell blocks activation, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Step 3 — Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

> `requirements.txt` holds the app dependencies; `requirements-dev.txt` adds `pytest` for testing.

---

## ⚙️ Configuration

### Step 4 — Create the `.env` file

**Windows:**
```powershell
copy .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

### Step 5 — Add your Gemini API key

Open `.env` and set your key:

```env
GEMINI_API_KEY=your-gemini-api-key-here
```

> 🔒 `.env` is listed in `.gitignore`, so your key is never committed to GitHub.
> You can also paste the key into the app's sidebar instead (kept only for that browser session).

### All configuration options

| Variable | Default | Description |
| --- | --- | --- |
| `GEMINI_API_KEY` | – | **Required.** Your Gemini API key. |
| `GEMINI_LIVE_MODEL` | `gemini-3.5-transcribe-live` | Gemini Live model used for transcription. |
| `DATABASE_URL` | `sqlite:///data/transcriptions.db` | Database connection URL. SQLite locally; PostgreSQL in production, e.g. `postgresql://user:password@host:5432/dbname`. |
| `TURN_URL` | – | Optional TURN server for WebRTC (needed on some cloud hosts / networks). |
| `TURN_USERNAME` | – | TURN username. |
| `TURN_CREDENTIAL` | – | TURN password. |

Settings are read in this order: **environment variables → `.env` file → `.streamlit/secrets.toml`**.

---

## 🚀 Running the App

### Step 6 — Start the application

```bash
python -m streamlit run app.py
```

### Step 7 — Open in your browser

```
http://localhost:8501
```

The SQLite database (`data/transcriptions.db`) and its table are created automatically on first run.

**Optional start options:**

```bash
# Run on a different port
python -m streamlit run app.py --server.port 8080

# Make it reachable from other devices on your network
python -m streamlit run app.py --server.address 0.0.0.0
```

> 🎤 Browsers only allow microphone access on `localhost` or over **HTTPS**.

**Stop the app:** press `Ctrl + C` in the terminal.

---

## 🧭 How to Use

### 1. Live Transcription (real-time)
1. Open the **Live Transcription** page (default page).
2. Choose the **Spoken language**:
   - **Hindi + English mix (Hinglish)** — recommended for code-mixed speech → `Kal meeting hai, please join on time.`
   - **Auto-detect any language** — Hindi is written in Devanagari → `कल मीटिंग है, प्लीज जॉइन ऑन टाइम।`
   - **Hindi**, **English (India)**, **English (US)** — single language.
3. In the **🔴 Live microphone** tab, click **START** and allow microphone access.
4. Speak — text appears live (grey italic text = words still being recognised).
5. Click **STOP** when done.
6. Review/edit the title and text, then click **💾 Save to history** (or **🗑️ Discard**).
7. Click **🔊 Listen** to hear the text read aloud.

### 2. Record or Upload a Clip
1. Open the **📼 Record or upload a clip** tab.
2. Record using the built-in recorder, **or** upload an audio file.
3. Click **Transcribe clip**, then review and save as above.

### 3. History Dashboard (CRUD)
| Operation | How |
| --- | --- |
| **Create** | Expand **➕ Add a transcription manually**, fill the form, click **Create**. |
| **Read** | Browse the table; use the **search box** and **source filter**; view stats at the top. |
| **Update** | Click a row in the table → edit in the form below → **💾 Save changes**. |
| **Delete** | Click a row → **🗑️ Delete** → confirm in the dialog. |
| **Listen** | Click a row → **🔊 Listen**. |
| **Export** | **⬇️ Download .txt** for one record, **⬇️ Export all as CSV** for the list. |

---

## 🧪 Running Tests

### Unit tests (no API key needed)

```bash
python -m pytest
```

Covers database CRUD, input validation, audio conversion and transcript handling.

### End-to-end Gemini test (no microphone needed)

```bash
python -m scripts.smoke_test_gemini "Kal meeting hai, please join on time"
```

This generates speech from the sentence, streams it to Gemini Live and prints the transcript —
a quick way to confirm your API key and model work. Expected output:

```
Model:      gemini-3.5-transcribe-live
Input:      Kal meeting hai, please join on time  (3.1s of audio)
Transcript: ...
```

---

## 🐳 Run with Docker

```bash
# Build the image
docker build -t realtime-speech-to-text .

# Run (SQLite inside the container)
docker run -p 8501:8501 -e GEMINI_API_KEY=your-key realtime-speech-to-text

# Run with PostgreSQL
docker run -p 8501:8501 \
  -e GEMINI_API_KEY=your-key \
  -e DATABASE_URL=postgresql://user:password@host:5432/dbname \
  realtime-speech-to-text
```

Open `http://localhost:8501`. The container respects the `$PORT` variable, so it works on
Render, Railway and Google Cloud Run without changes.

---

## ☁️ Deploy to the Cloud (Streamlit Community Cloud)

### Step 1 — Push the code to GitHub

```bash
git init
git add .
git commit -m "Real-time speech to text with Gemini Live and Streamlit"
git branch -M main
git remote add origin https://github.com/<your-username>/realtime-speech-to-text.git
git push -u origin main
```

### Step 2 — Create a free PostgreSQL database

1. Sign up at [Neon](https://neon.tech) (or [Supabase](https://supabase.com)).
2. Create a project and copy the **connection string**, e.g.
   `postgresql://user:password@ep-xxxx.aws.neon.tech/neondb?sslmode=require`

> Use PostgreSQL in the cloud — the app's local SQLite file would be erased whenever the app restarts.

### Step 3 — Deploy the app

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. Click **Create app** → select your repository, branch `main`, main file `app.py`.
3. Open **Advanced settings → Secrets** and paste:

   ```toml
   GEMINI_API_KEY = "your-gemini-api-key"
   DATABASE_URL = "postgresql://user:password@host/dbname?sslmode=require"

   # Recommended for the live microphone on cloud hosting (free TURN e.g. from metered.ca)
   TURN_URL = "turn:your-turn-server:80"
   TURN_USERNAME = "your-turn-username"
   TURN_CREDENTIAL = "your-turn-password"
   ```

4. Click **Deploy**. You get a public URL like `https://realtime-speech-to-text.streamlit.app`.

> If the live microphone **START** button keeps spinning on the cloud, add the TURN settings above.
> The **Record or upload a clip** tab works without TURN.

---

## 🗂️ Project Structure

```
realtime-speech-to-text/
├── app.py                      # Entry point: page navigation + sidebar
├── views/
│   ├── live.py                 # Live mic + clip transcription, review & save
│   └── dashboard.py            # History dashboard: CRUD, search, TTS, export
├── stt/                        # Core application package
│   ├── config.py               # Settings from env / .env / Streamlit secrets
│   ├── database.py             # ORM model + repository with CRUD operations
│   ├── transcriber.py          # Gemini Live real-time streaming client
│   ├── audio.py                # Audio conversion to 16 kHz mono PCM, chunking
│   ├── tts.py                  # Text-to-Speech
│   ├── languages.py            # Language options → Gemini language codes
│   └── app_context.py          # Shared Streamlit helpers (DB, API key, toasts)
├── scripts/
│   └── smoke_test_gemini.py    # End-to-end Gemini test without a microphone
├── tests/                      # Unit tests (pytest)
├── .streamlit/config.toml      # Streamlit settings and theme
├── .env.example                # Configuration template
├── requirements.txt            # App dependencies
├── requirements-dev.txt        # App + test dependencies
├── Dockerfile                  # Container image for cloud deployment
└── pyproject.toml              # Project metadata + pytest config
```

### Database schema — `transcriptions` table

| Column | Type | Description |
| --- | --- | --- |
| `id` | Integer (PK) | Auto-increment ID |
| `title` | String(200) | Transcription title |
| `text` | Text | Transcribed text |
| `language` | String(20) | Language setting used (`hi-IN+en-IN`, `auto`, `hi-IN`, ...) |
| `source` | String(20) | `live`, `clip` or `manual` |
| `duration_seconds` | Float | Length of the recorded audio |
| `created_at` | DateTime | Created timestamp (UTC) |
| `updated_at` | DateTime | Last updated timestamp (UTC) |

---

## 🏗️ Architecture

```
Browser microphone
      │  WebRTC
      ▼
streamlit-webrtc ──► PcmConverter (resample to 16 kHz mono PCM16, 100 ms chunks)
                              │
                              ▼
            LiveTranscriber (background thread + asyncio)
              ├── sends audio  ──► Gemini Live API
              └── receives     ◄── interim + final transcripts
                              │
                              ▼
         Streamlit UI (shows live text) ──► Save ──► SQLAlchemy ──► SQLite / PostgreSQL
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
| --- | --- |
| `Add your Gemini API key` warning | Set `GEMINI_API_KEY` in `.env` and restart, or paste the key in the sidebar. |
| Microphone permission not asked | Use `http://localhost:8501` or an HTTPS URL; check the browser's site permissions. |
| **START** keeps spinning | WebRTC is blocked by the network — configure `TURN_*` settings or use the clip tab. |
| `No speech was detected` | Speak closer to the microphone and check the correct input device is selected. |
| Model not found error | Set `GEMINI_LIVE_MODEL` in `.env` to a Live model available for your key. |
| `pip.exe` blocked by policy (Windows) | Use `python -m pip ...` instead of `pip ...`. |
| `DLL load failed ... Application Control policy` (Windows Smart App Control) | Reinstall SQLAlchemy as pure Python: <br>`$env:DISABLE_SQLALCHEMY_CEXT='1'; python -m pip install --force-reinstall --no-deps --no-binary sqlalchemy sqlalchemy` |
| Port 8501 already in use | `python -m streamlit run app.py --server.port 8502` |

---

## 📋 Command Cheat Sheet

| Task | Command |
| --- | --- |
| Create virtual env | `python -m venv .venv` |
| Activate (Windows) | `.venv\Scripts\Activate.ps1` |
| Activate (macOS/Linux) | `source .venv/bin/activate` |
| Install dependencies | `python -m pip install -r requirements-dev.txt` |
| Create config | `copy .env.example .env` (Windows) / `cp .env.example .env` |
| **Start the app** | **`python -m streamlit run app.py`** |
| Open the app | `http://localhost:8501` |
| Run unit tests | `python -m pytest` |
| Test Gemini end-to-end | `python -m scripts.smoke_test_gemini` |
| Docker build | `docker build -t realtime-speech-to-text .` |
| Docker run | `docker run -p 8501:8501 -e GEMINI_API_KEY=your-key realtime-speech-to-text` |
| Stop the app | `Ctrl + C` |
