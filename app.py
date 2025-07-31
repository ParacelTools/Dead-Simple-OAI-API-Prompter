from flask import Flask, render_template, request, jsonify
import requests
import os
import json
import sqlite3
from datetime import datetime

app = Flask(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), ".llama_agent.conf")
DB_PATH = os.path.join(os.path.dirname(__file__), "chat_history.db")

# --- Config Functions ---
def save_llama_url(url):
    with open(CONFIG_PATH, "w") as f:
        f.write(url.strip())

def load_llama_url():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return f.read().strip()
    return "http://localhost:8080/v1/chat/completions"

# --- Chat History Functions ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                role TEXT,
                content TEXT
            )
        """)
        conn.commit()

def log_message(role, content):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO chat (timestamp, role, content) VALUES (?, ?, ?)",
                  (datetime.utcnow().isoformat(), role, content))
        conn.commit()

def get_recent_messages(limit=10):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT role, content FROM chat ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

# --- LLaMA Interaction ---
def send_to_llama(messages, url, model="llama-chat", temperature=0.7, top_p=0.9, max_tokens=10000, stream=False, grammar=None):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "stream": stream
    }
    if grammar:
        payload["grammar"] = grammar

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"], payload
    except Exception as e:
        return f"Error: {e}", payload

# --- Routes ---
@app.route("/")
def index():
    llama_url = load_llama_url()
    return render_template("index.html", llama_url=llama_url)

@app.route("/prompt", methods=["POST"])
def prompt():
    system_prompt = request.form.get("system", "You are a helpful assistant.")
    user_input = request.form["user"]
    llama_url = request.form.get("llama_url", load_llama_url())

    # New parameters
    try:
        recent_limit = int(request.form.get("recent_limit"))
        temperature = float(request.form.get("temperature"))
        top_p = float(request.form.get("top_p"))
        max_tokens = int(request.form.get("max_tokens"))
    except ValueError:
        return jsonify({"response": "Invalid numeric input"}), 400

    save_llama_url(llama_url)

    log_message("user", user_input)
    recent_messages = get_recent_messages(limit=recent_limit)
    messages = [{"role": "system", "content": system_prompt}] + recent_messages

    reply, payload = send_to_llama(
        messages,
        url=llama_url,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        grammar = request.form.get("grammar") or None
    )
    log_message("assistant", reply)

    return jsonify({
        "response": reply,
        "payload": payload
    })

@app.route("/clear", methods=["POST"])
def clear_history():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM chat")
        conn.commit()
    return jsonify({"status": "cleared"})

@app.route("/history")
def full_history():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT timestamp, role, content FROM chat ORDER BY id ASC")
        rows = c.fetchall()
    return jsonify([
        {"timestamp": ts, "role": role, "content": content}
        for ts, role, content in rows
    ])

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5005, debug=True)


