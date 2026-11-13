import os
import time
import random
import threading
from flask import Flask, render_template_string, request
from instagrapi import Client

app = Flask(__name__)

# Stare globală pentru loguri și activitatea boților
logs = []
bot_status = {"running": False}

def log_message(message):
    global logs
    timestamp = time.strftime("[%H:%M:%S]")
    entry = f"{timestamp} {message}"
    logs.append(entry)
    # Păstrăm ultimele 100 de loguri să nu ocupe multă memorie
    if len(logs) > 100:
        logs.pop(0)
    print(entry)

def run_instagram_bot(session_id, group_targets, messages_list, bot_name):
    """ Funcția care rulează pe un fir separat pentru fiecare cont în parte """
    client = Client()
    
    # Setează un delay de siguranță pentru cereri
    client.delay_range = [2, 5]

    log_message(f"[{bot_name}] Încercare de autentificare cu Session ID...")
    try:
        client.login_by_sessionid(session_id.strip())
        log_message(f"[{bot_name}] Autentificare reușită!")
    except Exception as e:
        log_message(f"[{bot_name}] ❌ Eroare la autentificare: {str(e)}")
        return

    # Ciclul infinit de trimitere mesaje pe grupuri
    msg_index = 0
    while bot_status["running"]:
        for target_group in group_targets:
            if not bot_status["running"]:
                break
            
            target_group = target_group.strip()
            if not target_group:
                continue

            log_message(f"[{bot_name}] Caut grupul: '{target_group}'...")
            chat_thread = None
            
            try:
                # Caută în mesajele directe
                threads = client.direct_threads(amount=20)
                for thread in threads:
                    # Verifică dacă numele grupului conține textul căutat sau ID-ul
                    thread_name = thread.title if thread.title else ""
                    if target_group.lower() in thread_name.lower() or target_group == str(thread.id):
                        chat_thread = thread
                        break
                
                if chat_thread:
                    message_text = messages_list[msg_index % len(messages_list)]
                    msg_index += 1
                    
                    client.direct_send(message_text, thread_ids=[chat_thread.id])
                    log_message(f"[{bot_name}] ✉️ Trimis pe '{target_group}': {message_text[:30]}...")
                else:
                    log_message(f"[{bot_name}] ⚠️ Grupul '{target_group}' nu a fost găsit în inbox.")
            
            except Exception as e:
                log_message(f"[{bot_name}] ⚠️ Eroare la trimitere: {str(e)}")

            # Pauză umană aleatorie între mesaje (între 3 și 7 secunde)
            sleep_time = random.uniform(3.0, 7.0)
            time.sleep(sleep_time)
            
        # Pauză scurtă între iterările listei de grupuri
        time.sleep(5)

@app.route("/", methods=["GET", "POST"])
def index():
    global logs, bot_status
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "start" and not bot_status["running"]:
            sessions_raw = request.form.get("sessions", "")
            groups_raw = request.form.get("groups", "")
            messages_raw = request.form.get("messages", "")
            
            # Împarte datele după virgulă sau linie nouă
            sessions = [s.strip() for s in sessions_raw.split(",") if s.strip()]
            groups = [g.strip() for g in groups_raw.replace("\r", "").split("\n") if g.strip()]
            messages = [m.strip() for m in messages_raw.replace("\r", "").split("\n") if m.strip()]
            
            if not sessions:
                log_message("❌ Eroare: Nu ai adăugat niciun Session ID!")
            elif not groups:
                log_message("❌ Eroare: Nu ai adăugat niciun grup!")
            elif not messages:
                log_message("❌ Eroare: Nu ai adăugat niciun mesaj!")
            else:
                bot_status["running"] = True
                logs.clear()
                log_message(f"🚀 Pornire sistem cu {len(sessions)} conturi pe {len(groups)} grupuri în paralel!")
                
                # Pornește câte un fir (thread) separat pentru fiecare cont
                for idx, session in enumerate(sessions, start=1):
                    bot_name = f"Cont #{idx}"
                    t = threading.Thread(target=run_instagram_bot, args=(session, groups, messages, bot_name))
                    t.daemon = True
                    t.start()
                    
        elif action == "stop":
            bot_status["running"] = False
            log_message("⏹️ S-a cerut oprirea boților.")

    return render_template_string(HTML_TEMPLATE, logs=logs, running=bot_status["running"])

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <title>Instagram Multi-Bot Paralel</title>
    <style>
        body { background: #0f172a; color: #f8fafc; font-family: monospace; padding: 20px; }
        .container { max-width: 800px; margin: auto; background: #1e293b; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        textarea, input { width: 100%; background: #0f172a; color: #38bdf8; border: 1px solid #334155; padding: 10px; margin-top: 5px; margin-bottom: 15px; border-radius: 4px; box-sizing: border-box; }
        button { padding: 12px 20px; font-weight: bold; border: none; border-radius: 4px; cursor: pointer; text-transform: uppercase; }
        .btn-start { background: #22c55e; color: white; }
        .btn-stop { background: #ef4444; color: white; }
        .logs { background: #020617; padding: 15px; height: 300px; overflow-y: scroll; border: 1px solid #334155; font-size: 12px; border-radius: 4px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <h2>👑 Instagram Multi-Bot Paralel (Render)</h2>
        <form method="POST">
            <label><b>Session ID-uri (separate prin virgulă):</b></label>
            <textarea name="sessions" rows="2" placeholder="cookie1, cookie2..."></textarea>
            
            <label><b>Grupuri (câte unul pe fiecare rând):</b></label>
            <textarea name="groups" rows="3" placeholder="Nume grup 1&#10;Nume grup 2"></textarea>

            <label><b>Mesaje (câte unul pe fiecare rând):</b></label>
            <textarea name="messages" rows="4" placeholder="Mesaj 1&#10;Mesaj 2"></textarea>

            {% if running %}
                <button type="submit" name="action" value="stop" class="btn-stop">Oprește Toate Conturile</button>
            {% else %}
                <button type="submit" name="action" value="start" class="btn-start">Pornește Boții în Paralel</button>
            {% endif %}
        </form>

        <h3 style="margin-top: 25px;">Jurnal activitate în timp real:</h3>
        <div class="logs">{% for log in logs %}{{ log }}&#10;{% endfor %}</div>
    </div>
    <script>
        // Auto-refresh la fiecare 3 secunde pentru a vedea logurile noi
        setTimeout(function(){ location.reload(); }, 3000);
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
