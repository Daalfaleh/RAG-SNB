import json
import os
import re
import time
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from langchain_community.vectorstores import Chroma
from werkzeug.security import check_password_hash

from get_embedding_function import get_embedding_function


def required_setting(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} must be set in the environment.")
    return value


app = Flask(__name__, static_folder="static")
app.config.update(
    SECRET_KEY=required_setting("FLASK_SECRET_KEY"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=1800,
    MAX_CONTENT_LENGTH=16 * 1024,
)
CSRFProtect(app)

ADMIN_USERNAME = required_setting("ADMIN_USERNAME")
ADMIN_PASSWORD_HASH = required_setting("ADMIN_PASSWORD_HASH")
CHROMA_PATH = "Chroma"
PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}
"""

db, model = None, None
GREETINGS = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]


def setup_rag():
    global db, model
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    model = Ollama(model="llama2")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            if request.path == "/query":
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def write_message_to_file(sender, message):
    with open("chat_log.txt", "a", encoding="utf-8") as file:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file.write(json.dumps({"timestamp": timestamp, "sender": sender, "message": message}) + "\n")


def is_greeting(text):
    return text.lower().strip() in GREETINGS


def handle_greeting():
    return "Hello! How can I assist you today?", []


def is_gibberish(text):
    words = re.findall(r"\w+", text.lower())
    return len(words) < 2 and not is_greeting(text)


def query_rag(query_text):
    if is_greeting(query_text):
        return handle_greeting()
    if is_gibberish(query_text):
        return "I'm sorry, but I didn't understand your question. Could you please rephrase it?", []

    results = db.similarity_search_with_score(query_text, k=5)
    if not results:
        return "I don't have enough information to answer that question. Can you try asking something else?", []

    context_text = "\n\n---\n\n".join(doc.page_content for doc, _score in results)
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE).format(context=context_text, question=query_text)
    response_text = model.invoke(prompt)
    return response_text, [doc.metadata.get("id") for doc, _score in results]


@app.route("/")
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/do_login", methods=["POST"])
def do_login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
        session.clear()
        session["logged_in"] = True
        session.permanent = True
        return redirect(url_for("index"))

    return render_template("login.html", error="Invalid username or password."), 401


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/index")
@login_required
def index():
    return render_template("index.html")


@app.route("/query", methods=["POST"])
@login_required
def query():
    payload = request.get_json(silent=True) or {}
    user_input = payload.get("query", "").strip()
    if not user_input:
        return jsonify({"error": "A query is required."}), 400

    write_message_to_file("User", user_input)
    time.sleep(2)
    response, sources = query_rag(user_input)
    write_message_to_file("Chatbot", response)
    return jsonify({"response": response, "sources": sources})


if __name__ == "__main__":
    setup_rag()
    app.run(host="127.0.0.1", port=2000, debug=False)
