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
        .logs { margin-top: 20px; background: #090d16; padding: 10px; border-radius: 6px; height: 150px; overflow-y: auto; font-family: monospace; font-size: 12px; border: 1px solid #334155; }
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
    bot_logs.append(msg)
    if len(bot_logs) > 50:
        bot_logs.pop(0)

def run_bot(username, password, messages, groups, delay):
    global bot_status
    bot_status = "În rulare..."
    log_message(f"🔑 Încercare de autentificare pentru {username}...")
    
    client = Client()
    client.set_user_agent("Instagram 365.0.0.35.116 Android (33/13; 480dpi; 1080x2340; Samsung; SM-S918B; qcom; sm8550; en_US; 618731234)")
    
    try:
        client.login(username, password)
        log_message("✅ Autentificat cu succes!")
    except Exception as e:
        log_message(f"❌ Eroare conectare: {e}")
        bot_status = "Eroare autentificare"
        return

    try:
        threads = client.direct_threads(amount=20)
    except Exception as e:
        log_message(f"❌ Eroare la citirea chat-urilor: {e}")
        bot_status = "Eroare preluare chaturi"
        return

    target_groups = [g.strip().lower() for g in groups.split(",") if g.strip()]
    selected_threads = []
    
    for thread in threads:
        title = thread.thread_title if thread.thread_title else ""
        for tg in target_groups:
            if tg in title.lower():
                selected_threads.append(thread)
                log_message(f"🎯 Găsit grup potrivit: {title}")

    if not selected_threads:
        log_message("⚠️ Nu s-au găsit grupuri potrivite cu denumirile specificate!")
        bot_status = "Oprit (Fără grupuri)"
        return

    msg_list = [m.strip() for m in messages.split(",") if m.strip()]
    loop_count = 1

    while True:
        log_message(f"--- Ciclul nr. {loop_count} ---")
        for thread in selected_threads:
            title = thread.thread_title if thread.thread_title else thread.id
            for msg in msg_list:
                try:
                    client.direct_send(msg, thread_ids=[thread.id])
                    log_message(f"✅ Trimis '{msg}' către '{title}'")
                except Exception as err:
                    log_message(f"❌ Eroare trimitere: {err}")
                time.sleep(1)

        log_message(f"⏳ Aștept {delay} secunde...")
        loop_count += 1
        time.sleep(delay)

@app.route('/', methods=['GET', 'HEAD'])
def index():
    return render_template_string(HTML_TEMPLATE, status=bot_status, logs=bot_logs)

@app.route('/start', methods=['POST'])
def start_bot():
    username = request.form.get('username')
    password = request.form.get('password')
    messages = request.form.get('messages')
    groups = request.form.get('groups')
    delay = float(request.form.get('delay', 5))

    thread = threading.Thread(target=run_bot, args=(username, password, messages, groups, delay))
    thread.daemon = True
    thread.start()

    return render_template_string(HTML_TEMPLATE, status="Pornit...", logs=bot_logs)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
