# RAG-SNB

A local retrieval-augmented generation application for asking questions over PDF documents. It loads PDFs into a Chroma vector store, creates Ollama embeddings, retrieves relevant passages, and serves a Flask web interface backed by an Ollama language model.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Install and start Ollama, then make the configured embedding and chat models available.

## Index documents

Place PDFs in `data/`, then run:

```bash
python populate_database.py
```

Use `--reset` when you intentionally want to rebuild the Chroma database.

## Start the app

```bash
python query_data.py
```

Open the local Flask URL shown in the terminal. Before deployment, move credentials and session secrets out of source code and into environment variables.
