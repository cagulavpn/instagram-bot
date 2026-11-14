import os
import time
import random
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template_string, request
from instagrapi import Client

app = Flask(__name__)

logs = []
bot_status = {"running": False}
group_id_cache = {}

def log_message(message):
    global logs
    timestamp = time.strftime("[%H:%M:%S.%f]")[:-3]
    entry = f"{timestamp} {message}"
    logs.append(entry)
    if len(logs) > 200:
        logs.pop(0)
    print(entry)

def fire_and_forget(client, thread_id, message_text, bot_name):
    try:
        client.direct_send(message_text, thread_ids=[thread_id])
        log_message(f"[{bot_name}] 🎯 [BLIND HIT] Mesaj trimis!")
    except Exception as e:
        log_message(f"[{bot_name}] ⚡ [FIRE] Pachet livrat (Răspuns server: {str(e)[:25]}...)")

def run_blind_bot(session_id, group_targets, messages_list, bot_name):
    client = Client()
    client.delay_range = [0, 0]

    log_message(f"[{bot_name}] Conectare Mitralieră...")
    try:
        client.login_by_sessionid(session_id.strip())
        log_message(f"[{bot_name}] Conexiune armată cu succes!")
    except Exception as e:
        log_message(f"[{bot_name}] ❌ Sesiune eșuată: {str(e)}")
        return

    active_threads = []
    for target_group in group_targets:
        target_group = target_group.strip()
        if not target_group:
            continue
        
        chat_thread = None
        if target_group in group_id_cache:
            try:
                chat_thread = client.direct_thread(group_id_cache[target_group])
            except:
                pass
        
        if not chat_thread:
            try:
                threads = client.direct_threads(amount=30)
                for thread in threads:
                    thread_name = getattr(thread, 'thread_title', None) or getattr(thread, 'title', None) or ""
                    if target_group.lower() in thread_name.lower() or target_group == str(thread.id):
                        chat_thread = thread
                        group_id_cache[target_group] = thread.id
                        break
            except Exception as e:
                log_message(f"[{bot_name}] Eroare căutare grup: {str(e)}")
        
        if chat_thread:
            active_threads.append(chat_thread.id)
            log_message(f"[{bot_name}] 🎯 Țintă fixată: {target_group}")

    if not active_threads:
        log_message(f"[{bot_name}] ❌ Nicio țintă validă găsită.")
        return

    log_message(f"[{bot_name}] 🔥 FOC CONTINUU DECLANȘAT!")
    
    msg_index = 0
    # Folosim 15 fire optimizate ca să nu blocăm serverul de pe Render
    with ThreadPoolExecutor(max_workers=15) as executor:
        while bot_status["running"]:
            for thread_id in active_threads:
                if not bot_status["running"]:
                    break
                
                message_text = messages_list[msg_index % len(messages_list)]
                msg_index += 1
                
                executor.submit(fire_and_forget, client, thread_id, message_text, bot_name)
            
            # Micro-pauză de siguranță pentru a ține serverul în viață (fără erori 500)
            time.sleep(0.05)

    log_message(f"[{bot_name}] 🏁 Sesiunea s-a oprit.")

@app.route("/", methods=["GET", "POST"])
def index():
    global logs, bot_status
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "start" and not bot_status["running"]:
            sessions_raw = request.form.get("sessions", "")
            groups_raw = request.form.get("groups", "")
            messages_raw = request.form.get("messages", "")
            
            sessions = [s.strip() for s in sessions_raw.split(",") if s.strip()]
            groups = [g.strip() for g in groups_raw.replace("\r", "").split("\n") if g.strip()]
            messages = [m.strip() for m in messages_raw.replace("\r", "").split("\n") if m.strip()]
            
            if not sessions or not groups or not messages:
                log_message("❌ Completează toate câmpurile!")
            else:
                bot_status["running"] = True
                logs.clear()
                log_message(f"⚡ ⚠️ S-a pornit MODUL MITRALIERĂ STABIL ⚠️")
                
                for idx, session in enumerate(sessions, start=1):
                    bot_name = f"Mitraliera #{idx}"
                    t = threading.Thread(target=run_blind_bot, args=(session, groups, messages, bot_name))
                    t.daemon = True
                    t.start()
                    
        elif action == "stop":
            bot_status["running"] = False
            log_message("⏹️ Oprire forțată cerută.")

    return render_template_string(HTML_TEMPLATE, logs=logs, running=bot_status["running"])

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <title>Instagram Blind Fire Bot</title>
    <style>
        body { background: #1a0000; color: #ff3333; font-family: monospace; padding: 20px; }
        .container { max-width: 800px; margin: auto; background: #2a0000; padding: 20px; border-radius: 8px; border: 1px solid #ff0000; box-shadow: 0 0 35px rgba(255,0,0,0.4); }
        textarea { width: 100%; background: #0a0000; color: #ff6666; border: 1px solid #990000; padding: 10px; margin-top: 5px; margin-bottom: 15px; border-radius: 4px; box-sizing: border-box; }
        button { padding: 12px 20px; font-weight: bold; border: none; border-radius: 4px; cursor: pointer; text-transform: uppercase; }
        .btn-start { background: #ff0000; color: white; width: 100%; font-size: 16px; }
        .btn-stop { background: #440000; color: white; width: 100%; font-size: 16px; }
        .logs { background: #0a0000; padding: 15px; height: 350px; overflow-y: scroll; border: 1px solid #660000; font-size: 11px; border-radius: 4px; white-space: pre-wrap; color: #ff9999; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🔥 Instagram Blind Fire Bot (Modul Mitralieră)</h2>
        <form method="POST">
            <label><b>Session ID-uri:</b></label>
            <textarea name="sessions" rows="2" placeholder="cookie..."></textarea>
            
            <label><b>Grupuri:</b></label>
            <textarea name="groups" rows="3" placeholder="Grup..."></textarea>

            <label><b>Mesaje:</b></label>
            <textarea name="messages" rows="4" placeholder="Mesaj..."></textarea>

            {% if running %}
                <button type="submit" name="action" value="stop" class="btn-stop">Oprește Mitraliera</button>
            {% else %}
                <button type="submit" name="action" value="start" class="btn-start">PORNEȘTE MITRALIERA 💥</button>
            {% endif %}
        </form>

        <h3 style="margin-top: 25px; color: #ffcccc;">Jurnal Blind Fire:</h3>
        <div class="logs">{% for log in logs %}{{ log }}&#10;{% endfor %}</div>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
