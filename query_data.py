from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from flask_cors import CORS
import time
from functools import wraps
from flask import session, abort
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from get_embedding_function import get_embedding_function
from langchain.embeddings import OpenAIEmbeddings
import re
import json
from datetime import datetime

app = Flask(__name__, static_folder='static')

app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for debugging

app.secret_key = '9thfloorsecret'  # Replace with a real secret key

CHROMA_PATH = "Chroma"
PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}
"""

db, model = None, None

def setup_rag():
    global db, model
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    model = Ollama(model="llama2")

import re

GREETINGS = ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening']


def write_message_to_file(sender, message):
    with open('chat_log.txt', 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = json.dumps({"timestamp": timestamp, "sender": sender, "message": message})
        f.write(log_entry + '\n')


def is_greeting(text):
    return text.lower().strip() in GREETINGS

def handle_greeting():
    return "Hello! How can I assist you today?", []

def is_gibberish(text):
    # Improved check for gibberish
    words = re.findall(r'\w+', text.lower())
    return len(words) < 2 and not is_greeting(text)


def query_rag(query_text: str):
    if is_greeting(query_text):
        return handle_greeting()

    if is_gibberish(query_text):
        return "I'm sorry, but I didn't understand your question. Could you please rephrase it?", []

    results = db.similarity_search_with_score(query_text, k=5)
    if not results:
        return "I don't have enough information to answer that question. Can you try asking something else?", []

    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)
    
    response_text = model.invoke(prompt)
    sources = [doc.metadata.get("id", None) for doc, _score in results]
    return response_text, sources

@app.route('/')
def login():
    return render_template('login.html')



@app.route('/do_login', methods=['POST'])
def do_login():
    print("Form data:", request.form)  # Add this line

    username = request.form.get('username')
    password = request.form.get('password')
    
    print(f"Received username: {username}, password: {password}")  # Add this line for debugging
    
    if username and password:
        if username == "bandern" and password == "9thfloor":
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return 'Invalid credentials', 401
    else:
        return 'Username or password missing', 400

@app.route('/index')
def index():
    print("Session:", session)  # Add this line
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    user_input = request.json['query']
    write_message_to_file("User", user_input)
    
    # Simulate a delay to show the typing indicator
    time.sleep(2)
    
    response, sources = query_rag(user_input)
    write_message_to_file("Chatbot", response)
    
    return jsonify({'response': response})

if __name__ == '__main__':
    setup_rag()
    app.run(debug=True,port=2000)

