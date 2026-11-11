import os
import time
import threading
from flask import Flask, request, render_template_string
from instagrapi import Client

app = Flask(__name__)

# Variabilă globală pentru a urmări statusul botului
bot_status = "Oprit"
bot_logs = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram Bot Control</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; margin: 0; }
        .card { background: #1e293b; padding: 20px; border-radius: 12px; max-width: 500px; margin: 0 auto; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); }
        h2 { color: #38bdf8; text-align: center; margin-top: 0; }
        label { display: block; margin-top: 15px; font-weight: bold; font-size: 14px; color: #94a3b8; }
        input, textarea { width: 100%; padding: 10px; margin-top: 5px; border-radius: 6px; border: 1px solid #334155; background: #0f172a; color: white; box-sizing: border-box; font-size: 16px; }
        button { width: 100%; margin-top: 25px; padding: 12px; background: #0284c7; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; }
        button:hover { background: #0369a1; }
        .logs { margin-top: 20px; background: #090d16; padding: 10px; border-radius: 6px; height: 15px; overflow-y: auto; font-family: monospace; font-size: 12px; border: 1px solid #334155; }
        .status { text-align: center; font-weight: bold; margin-bottom: 10px; color: #4ade80; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🤖 Instagram Bot</h2>
        <div class="status">Status: {{ status }}</div>
        
        <form action="/start" method="POST">
            <label>Username Instagram:</label>
            <input type="text" name="username" required placeholder="utilizator">

            <label>Parolă Instagram:</label>
            <input type="password" name="password" required placeholder="parola">

            <label>Mesaje (separate prin virgulă):</label>
            <textarea name="messages" rows="3" required placeholder="Salut, Ce faci?, Cu ce te ajut?"></textarea>

            <label>Nume Grupuri / Chat-uri (separate prin virgulă):</label>
            <input type="text" name="groups" required placeholder="Grup 1, Grup 2">

            <label>Pauză între cicluri (secunde):</label>
            <input type="number" name="delay" value="5" min="1" required>

            <button type="submit">🚀 Pornește Botul</button>
        </form>

        <h3>Jurnal activitate:</h3>
        <div class="logs">
            {% for log in logs %}
                <div>{{ log }}</div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

def log_message(msg):
    global bot_logs
    bot_logs.append
