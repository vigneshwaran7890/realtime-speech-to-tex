# 🎙️ Real-time Speech to Text (Hindi + English)

A Streamlit web app that transcribes speech **in real time** with the **Gemini Live API**. It supports
multilingual, code-mixed speech (e.g. *"Kal meeting hai, please join on time"*). Every transcription
is stored in a relational database and managed from a **history dashboard** with full CRUD.
Saved text can be played back with **Text-to-Speech**.

## Features

| Area | What it does |
| --- | --- |
| **Live transcription** | Browser mic → WebRTC → server → Gemini Live (`gemini-3.5-transcribe-live`). Interim words appear while you speak, and final text is appended as each phrase completes. |
| **Multilingual** | Auto language detection handles Hindi / English code-switching. You can also pin the language (`hi-IN`, `en-IN`, `en-US`). |
| **Clip mode** | Record a clip with `st.audio_input` or upload a file (wav/mp3/m4a/ogg/webm/flac). This is a fallback for networks where WebRTC is blocked. |
| **Review before save** | Edit the transcript and its title, then save it to the DB or discard it. |
| **Dashboard (CRUD)** | **C**reate manually · **R**ead with search, source filter and metrics · **U**pdate title/text/language · **D**elete with a confirmation dialog. |
| **Text-to-Speech** | Listen to any transcript (gTTS; Hindi voice for Devanagari, Indian-English voice otherwise). |
| **Export** | Download one transcript as `.txt` or the filtered history as `.csv`. |
| **Long sessions** | Gemini Live sessions are capped at 10 minutes, so the app reconnects transparently every 9 minutes without dropping audio. |

## Architecture

```
Browser mic ──WebRTC──► streamlit-webrtc ──av frames──► PcmConverter (16 kHz mono PCM16)
                                                             │  ~100 ms chunks
                                                             ▼
                          LiveTranscriber (background thread + asyncio)
                             ├─ send:    session.send_realtime_input(audio=…)
                             └─ receive: interim_input_transcription / input_transcription
                                                             │
Streamlit UI ◄── polls final + interim text ─────────────────┘
     │
     └── Save ──► TranscriptionRepository (SQLAlchemy) ──► SQLite (local) / PostgreSQL (prod)
```

## Tech stack

- **Python 3.10+**, **Streamlit** (UI and multipage navigation)
- **Gemini Live API** via the `google-genai` SDK
- **streamlit-webrtc** + **PyAV** for real-time audio capture and resampling
- **SQLAlchemy 2** with **SQLite** (default) or **PostgreSQL** (`psycopg2`)
- **gTTS** for Text-to-Speech
- **pytest** for tests

## Project structure

```
├── app.py                    # Entry point: page navigation + sidebar
├── views/
│   ├── live.py               # Live mic + clip transcription, review & save
│   └── dashboard.py          # History dashboard with CRUD, TTS, export
├── stt/                      # Core package (UI-independent except app_context)
│   ├── config.py             # Settings from env / .env / Streamlit secrets
│   ├── database.py           # ORM model + TranscriptionRepository (CRUD)
│   ├── transcriber.py        # Gemini Live streaming client
│   ├── audio.py              # Frame/file → 16 kHz PCM16 conversion, chunking
│   ├── tts.py                # Text-to-Speech
│   ├── languages.py          # Language options → BCP-47 codes
│   └── app_context.py        # Streamlit glue: cached repo, API key, helpers
├── scripts/smoke_test_gemini.py  # End-to-end Gemini check without a mic
├── tests/                    # Unit tests (DB CRUD, audio, transcript handling)
├── .streamlit/config.toml
├── Dockerfile
├── requirements.txt / requirements-dev.txt
└── .env.example
```

## Getting started

```bash
# 1. Create a virtual environment and install dependencies
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt

# 2. Configure
cp .env.example .env        # then set GEMINI_API_KEY (get one at https://aistudio.google.com/apikey)

# 3. Run
streamlit run app.py
```

Open http://localhost:8501, choose a language (Auto-detect is the default), click **START**, allow
microphone access and speak.

### Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `GEMINI_API_KEY` | – | Required. You can also enter it in the sidebar (kept for the session only). |
| `GEMINI_LIVE_MODEL` | `gemini-3.5-transcribe-live` | Any Live-API model that supports input transcription. |
| `DATABASE_URL` | `sqlite:///data/transcriptions.db` | Any SQLAlchemy URL, e.g. `postgresql://user:pass@host:5432/db`. |
| `TURN_URL`, `TURN_USERNAME`, `TURN_CREDENTIAL` | – | Optional TURN server for WebRTC on cloud hosts or behind strict NATs. |

Values are read from environment variables, then `.env`, then `.streamlit/secrets.toml`.

## Tests

```bash
python -m pytest
python -m scripts.smoke_test_gemini "Kal meeting hai, please join on time"   # needs GEMINI_API_KEY
```

The smoke test synthesises speech with gTTS, streams it through Gemini Live and prints the transcript.
It checks the whole pipeline without a microphone.

## Deployment

### Streamlit Community Cloud (free)
1. Push this repo to GitHub.
2. Create a free PostgreSQL database (e.g. [Neon](https://neon.tech) or [Supabase](https://supabase.com)).
3. On [share.streamlit.io](https://share.streamlit.io), create an app pointing at `app.py`.
4. Under **Settings → Secrets**, add:
   ```toml
   GEMINI_API_KEY = "..."
   DATABASE_URL = "postgresql://..."
   # Recommended for WebRTC on cloud hosts (e.g. free TURN from metered.ca / Twilio):
   TURN_URL = "turn:..."
   TURN_USERNAME = "..."
   TURN_CREDENTIAL = "..."
   ```

### Docker (Render, Railway, Cloud Run, ...)
```bash
docker build -t speech-to-text .
docker run -p 8501:8501 -e GEMINI_API_KEY=... -e DATABASE_URL=postgresql://... speech-to-text
```
The container honours `$PORT` when the host injects one.

> Use PostgreSQL in production. Container filesystems on most free hosts are ephemeral, so a SQLite
> file would be wiped on redeploy.

## Notes & limitations

- **WebRTC connectivity:** on some networks the browser cannot reach the server without a TURN
  server. If **START** spins forever, configure TURN or use the **Record or upload a clip** tab, which
  uses plain HTTP.
- **Microphone access** requires HTTPS (or `localhost`).
- Speaker diarization and word-level timestamps are not supported by Gemini live transcription.

## Troubleshooting

- **`DLL load failed ... Application Control policy has blocked this file`** (Windows Smart App
  Control blocking SQLAlchemy's optional compiled extension): reinstall SQLAlchemy as pure Python:
  ```powershell
  $env:DISABLE_SQLALCHEMY_CEXT='1'; python -m pip install --force-reinstall --no-deps --no-binary sqlalchemy sqlalchemy
  ```
- **`pip.exe` blocked by policy:** call pip as `python -m pip ...` instead.
