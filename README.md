# RAG-SNB

A local retrieval-augmented generation application for asking questions over PDF documents. It loads PDFs into a Chroma vector store, creates Ollama embeddings, retrieves relevant passages, and serves a password-protected Flask interface backed by an Ollama language model.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Install and start Ollama, then make the configured embedding and chat models available.

## Secure configuration

The application refuses to start until its required secrets are provided. Never commit real values.

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('CHOOSE-A-NEW-PASSWORD'))"

$env:FLASK_SECRET_KEY = "generated-secret"
$env:ADMIN_USERNAME = "daad"
$env:ADMIN_PASSWORD_HASH = "generated-password-hash"
$env:SESSION_COOKIE_SECURE = "false"
```

Use `SESSION_COOKIE_SECURE=true` when served over HTTPS. The credentials previously committed to this repository must not be reused.

## Index documents

Place PDFs in `data/`, then run `python populate_database.py`. Use `--reset` only when intentionally rebuilding Chroma.

## Start

Run `python query_data.py`, then open `http://127.0.0.1:2000`.

Authentication protects the chat and query endpoint, POST requests use CSRF protection, sessions expire after 30 minutes, and passwords are verified using a one-way hash.
