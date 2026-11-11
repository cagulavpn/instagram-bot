import os
import time
import threading
from flask import Flask, request, render_template_string
from instagrapi import Client

app = Flask(__name__)

bot_status = "Oprit"
bot_logs = []
bot_thread_running = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🪽𝐍ïght𝐋ÿfe #CGL Control</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: url('https://i.ibb.co/6R228J5/image-f19b87.jpg') no-repeat center center fixed;
            background-size: cover;
            color: #f8fafc;
            padding: 20px;
            margin: 0;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
        }
        .bg-text {
            position: fixed;
            top: 15%;
            left: 50%;
            transform: translateX(-50%);
            font-size: 4rem;
            font-weight: 900;
            letter-spacing: 6px;
            color: #ffffff;
            text-transform: uppercase;
            text-shadow: 0 0 15px rgba(56, 189, 248, 0.9), 0 0 30px rgba(56, 189, 248, 0.6), 0 2px 5px rgba(0, 0, 0, 0.9);
            z-index: 1;
            pointer-events: none;
            text-align: center;
            width: 100%;
        }
        .card {
            position: relative;
            z-index: 2;
            background: rgba(15, 23, 42, 0.93);
            padding: 25px;
            border-radius: 16px;
            width: 100%;
            max-width: 500px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.9);
            border: 1px solid rgba(56, 189, 248, 0.5);
        }
        h2 { color: #38bdf8; text-align: center; margin-top: 0; text-shadow: 0 2px 4px rgba(0,0,0,0.8); }
        label { display: block; margin-top: 15px; font-weight: bold; font-size: 14px; color: #94a3b8; }
        input, textarea {
            width: 100%;
            padding: 10px;
            margin-top: 5px;
            border-radius: 8px;
            border: 1px solid #334155;
            background: rgba(15, 23, 42, 0.95);
            color: white;
            box-sizing: border-box;
            font-size: 16px;
        }
        input:focus, textarea:focus {
            outline: none;
            border-color: #38bdf8;
            box-shadow: 0 0 8px rgba(56, 189, 248, 0.6);
        }
        button {
            width: 100%;
            margin-top: 25px;
            padding: 12px;
            background: linear-gradient(135deg, #0284c7, #0369a1);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.5);
            transition: all 0.2s ease;
        }
        button:hover {
            background: linear-gradient(135deg, #0369a1, #075985);
            transform: translateY(-1px);
        }
        .logs {
            margin-top: 20px;
            background: rgba(5, 8, 15, 0.98);
            padding: 12px;
            border-radius: 8px;
            height: 150px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            border: 1px solid #334155;
            color: #38bdf8;
        }
        .status { text-align: center; font-weight: bold; margin-bottom: 10px; color: #4ade80; font-size: 15px; text-shadow: 0 1px 2px rgba(0,0,0,0.8); }
    </style>
</head>
<body>
    <div class="bg-text">CAGULĂ</div>
    <div class="card">
        <h2>🪽𝐍ïght𝐋ÿfe #CGL</h2>
        <div class="status">Status: {{ status }}</div>
        
        <form action="/start" method="POST">
            <label>Instagram Session ID (cookie):</label>
            <input type="text" name="sessionid" required placeholder="Lipește codul de sessionid aici">

            <label>Mesaje (separate prin virgulă):</label>
            <textarea name="messages" rows="3" required placeholder="Salut, Ce faci?"></textarea>

            <label>ID-uri Grupuri / Chat-uri (separate prin virgulă):</label>
            <input type="text" name="groups" required placeholder="Ex: 340282366841710301...">

            <label>Pauză între cicluri (secunde):</label>
            <input type="number" name="delay" value="2" min="1" required>

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

def run_bot(sessionid, messages, groups, delay):
    global bot_status, bot_thread_running
    bot_status = "În rulare..."
    bot_thread_running = True
    log_message("🔑 Autentificare dedicată cu Session ID...")
    
    client = Client()
    client.set_user_agent("Instagram 319.0.0.31.109 Android (33/13; 480dpi; 1080x2340; Samsung; SM-S918B; qcom; sm8550; en_US; 539583191)")
    
    try:
        client.login_by_sessionid(sessionid.strip())
        log_message("✅ Conectat stabil prin sesiune!")
    except Exception as e:
        log_message(f"❌ Eroare sesiune: {e}")
        bot_status = "Eroare sesiune"
        bot_thread_running = False
        return

    try:
        # Am crescut limita la 50 de chat-uri pentru a prinde și grupurile mai vechi
        threads = client.direct_threads(amount=50)
    except Exception as e:
        log_message(f"❌ Eroare la citirea chat-urilor: {e}")
        bot_status = "Eroare preluare chaturi"
        bot_thread_running = False
        return

    target_ids = [str(g).strip() for g in groups.split(",") if str(g).strip()]
    selected_threads = []
    
    for thread in threads:
        t_id = str(thread.id).strip()
        title = thread.thread_title if thread.thread_title else "Fără nume"
        
        for tid in target_ids:
            if tid == t_id or tid in t_id:
                selected_threads.append(thread)
                log_message(f"🎯 ID găsit și potrivit: '{title}' ({t_id})")

    if not selected_threads:
        log_message("⚠️ Niciun ID introdus nu se potrivește cu chaturile găsite în primele 50!")
        bot_status = "Oprit (ID-uri negăsite)"
        bot_thread_running = False
        return

    msg_list = [m.strip() for m in messages.split(",") if m.strip()]
    loop_count = 1

    while bot_thread_running:
        cycle_start_time = time.time()
        log_message(f"--- Ciclul nr. {loop_count} ---")
        
        for thread in selected_threads:
            title = thread.thread_title if thread.thread_title else thread.id
            for msg in msg_list:
                if not bot_thread_running:
                    break
                try:
                    client.direct_send(msg, thread_ids=[thread.id])
                    log_message(f"✅ Trimis către ID: {thread.id}")
                except Exception as err:
                    log_message(f"❌ Eroare trimitere: {err}")
                time.sleep(0.5)

        loop_count += 1
        
        elapsed = time.time() - cycle_start_time
        sleep_time = max(0.1, delay - elapsed)
        time.sleep(sleep_time)

@app.route('/', methods=['GET', 'POST', 'HEAD'])
def index():
    return render_template_string(HTML_TEMPLATE, status=bot_status, logs=bot_logs)

@app.route('/start', methods=['POST'])
def start_bot():
    global bot_thread_running
    bot_thread_running = False
    time.sleep(1)

    sessionid = request.form.get('sessionid')
    messages = request.form.get('messages')
    groups = request.form.get('groups')
    delay = float(request.form.get('delay', 2))

    thread = threading.Thread(target=run_bot, args=(sessionid, messages, groups, delay))
    thread.daemon = True
    thread.start()

    return render_template_string(HTML_TEMPLATE, status="Pornit (Mod Rapid)...", logs=bot_logs)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
