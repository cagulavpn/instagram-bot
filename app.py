import os
import time
import random
import threading
from flask import Flask, render_template_string, request
from instagrapi import Client

app = Flask(__name__)

logs = []
bot_status = {"running": False}

# Dicționar global pentru a memora ID-urile grupurilor pe baza numelui introdus
group_id_cache = {}

def log_message(message):
    global logs
    timestamp = time.strftime("[%H:%M:%S]")
    entry = f"{timestamp} {message}"
    logs.append(entry)
    if len(logs) > 100:
        logs.pop(0)
    print(entry)

def run_instagram_bot(session_id, group_targets, messages_list, bot_name):
    client = Client()
    client.delay_range = [5, 10]

    log_message(f"[{bot_name}] Conectare securizată în curs...")
    try:
        client.login_by_sessionid(session_id.strip())
        log_message(f"[{bot_name}] Conexiune stabilită cu succes sub radar!")
    except Exception as e:
        log_message(f"[{bot_name}] ❌ Sesiune eșuată: {str(e)}")
        return

    msg_index = 0
    messages_sent_in_session = 0

    while bot_status["running"]:
        shuffled_groups = list(group_targets)
        random.shuffle(shuffled_groups)

        for target_group in shuffled_groups:
            if not bot_status["running"]:
                break
            
            target_group = target_group.strip()
            if not target_group:
                continue

            chat_thread = None
            
            # Verificăm dacă avem deja ID-ul salvat în memorie pentru acest grup
            if target_group in group_id_cache:
                saved_thread_id = group_id_cache[target_group]
                log_message(f"[{bot_name}] Folosesc ID-ul memorat pentru '{target_group}' (rezistent la schimbarea numelui)...")
                try:
                    # Încercăm direct să trimitem sau să validăm thread-ul prin ID-ul salvat
                    chat_thread = client.direct_thread(saved_thread_id)
                except Exception:
                    # Dacă ID-ul a devenit invalid din orice motiv, resetăm cache-ul și căutăm din nou
                    chat_thread = None

            # Dacă nu avem ID-ul salvat sau a eșuat, căutăm grupul prin inbox după nume
            if not chat_thread:
                log_message(f"[{bot_name}] Caut ținta în inbox: '{target_group}'...")
                try:
                    threads = client.direct_threads(amount=25)
                    for thread in threads:
                        thread_name = getattr(thread, 'thread_title', None) or getattr(thread, 'title', None) or ""
                        
                        # Dacă numele se potrivește SAU textul introdus este chiar ID-ul numeric al grupului
                        if target_group.lower() in thread_name.lower() or target_group == str(thread.id):
                            chat_thread = thread
                            # SALVĂM ID-ul AUTOMAT! Chiar dacă schimbi numele de acum înainte, tot aici va trimite
                            group_id_cache[target_group] = thread.id
                            log_message(f"[{bot_name}] 📌 ID salvat automat pentru '{target_group}' (ID: {thread.id})")
                            break
                except Exception as e:
                    log_message(f"[{bot_name}] ⚠️ Eroare la căutarea grupului: {str(e)}")
            
            # Trimiterea efectivă a mesajului dacă am găsit grupul
            if chat_thread:
                try:
                    message_text = messages_list[msg_index % len(messages_list)]
                    msg_index += 1
                    
                    client.direct_send(message_text, thread_ids=[chat_thread.id])
                    messages_sent_in_session += 1
                    log_message(f"[{bot_name}] 🎯 Lovitură reușită pe '{target_group}' (Total cont: {messages_sent_in_session})")
                except Exception as e:
                    log_message(f"[{bot_name}] ⚠️ Eroare la trimitere: {str(e)}")
            else:
                log_message(f"[{bot_name}] ⚠️ Ținta '{target_group}' nu a fost găsită în flux.")

            # Pauze stealth și de oboseală la 30 de mesaje
            stealth_sleep = random.uniform(15.0, 35.0)
            
            if messages_sent_in_session > 0 and messages_sent_in_session % 30 == 0:
                fatigue_pause = random.uniform(60.0, 120.0)
                log_message(f"[{bot_name}] 🛡️ Prag de 30 de mesaje atins! Contul ia o pauză de respirație de {int(fatigue_pause)} secunde...")
                time.sleep(fatigue_pause)
            else:
                time.sleep(stealth_sleep)
            
        time.sleep(10)

@app.route("/", methods=["GET", "POST"])
def index():
    global logs, bot_status, group_id_cache
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "start" and not bot_status["running"]:
            sessions_raw = request.form.get("sessions", "")
            groups_raw = request.form.get("groups", "")
            messages_raw = request.form.get("messages", "")
            
            sessions = [s.strip() for s in sessions_raw.split(",") if s.strip()]
            groups = [g.strip() for g in groups_raw.replace("\r", "").split("\n") if g.strip()]
            messages = [m.strip() for m in messages_raw.replace("\r", "").split("\n") if m.strip()]
            
            if not sessions:
                log_message("❌ Eroare: Lipsesc Session ID-urile!")
            elif not groups:
                log_message("❌ Eroare: Nu ai setat nicio țintă!")
            elif not messages:
                log_message("❌ Eroare: Nu ai adăugat mesaje!")
            else:
                bot_status["running"] = True
                logs.clear()
                # Curățăm cache-ul vechi la o nouă pornire completă dacă e nevoie, sau îl lăsăm
                log_message(f"🕶️ Sistemul Stealth a pornit cu {len(sessions)} conturi în paralel pe {len(groups)} grupuri.")
                
                for idx, session in enumerate(sessions, start=1):
                    bot_name = f"Agent #{idx}"
                    t = threading.Thread(target=run_instagram_bot, args=(session, groups, messages, bot_name))
                    t.daemon = True
                    t.start()
                    
        elif action == "stop":
            bot_status["running"] = False
            log_message("⏹️ S-a ordonat oprirea agenților.")

    return render_template_string(HTML_TEMPLATE, logs=logs, running=bot_status["running"])

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <title>Instagram Stealth Multi-Bot</title>
    <style>
        body { background: #090d16; color: #38bdf8; font-family: monospace; padding: 20px; }
        .container { max-width: 800px; margin: auto; background: #111827; padding: 20px; border-radius: 8px; border: 1px solid #1f2937; box-shadow: 0 0 20px rgba(0,0,0,0.8); }
        textarea, input { width: 100%; background: #030712; color: #e2e8f0; border: 1px solid #374151; padding: 10px; margin-top: 5px; margin-bottom: 15px; border-radius: 4px; box-sizing: border-box; }
        button { padding: 12px 20px; font-weight: bold; border: none; border-radius: 4px; cursor: pointer; text-transform: uppercase; }
        .btn-start { background: #10b981; color: white; }
        .btn-stop { background: #ef4444; color: white; }
        .logs { background: #020617; padding: 15px; height: 300px; overflow-y: scroll; border: 1px solid #1f2937; font-size: 12px; border-radius: 4px; white-space: pre-wrap; color: #34d399; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🕶️ Instagram Stealth Multi-Bot (Anti-Ban Mode)</h2>
        <form method="POST">
            <label><b>Session ID-uri (separate prin virgulă):</b></label>
            <textarea name="sessions" rows="2" placeholder="cookie1, cookie2..."></textarea>
            
            <label><b>Grupuri (câte unul pe rând):</b></label>
            <textarea name="groups" rows="3" placeholder="Grup 1&#10;Grup 2"></textarea>

            <label><b>Mesaje (câte unul pe rând):</b></label>
            <textarea name="messages" rows="4" placeholder="Mesaj 1&#10;Mesaj 2"></textarea>

            {% if running %}
                <button type="submit" name="action" value="stop" class="btn-stop">Oprește Toți Agenții</button>
            {% else %}
                <button type="submit" name="action" value="start" class="btn-start">Pornește Sistemul Stealth</button>
            {% endif %}
        </form>

        <h3 style="margin-top: 25px; color: #f3f4f6;">Jurnal operațional invizibil:</h3>
        <div class="logs">{% for log in logs %}{{ log }}&#10;{% endfor %}</div>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
