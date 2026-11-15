import os
import time
import random
import threading
from flask import Flask, render_template_string, request
from instagrapi import Client

app = Flask(__name__)

logs = []
bot_status = {"running": False}

group_id_cache = {}

def log_message(message):
    global logs
    timestamp = time.strftime("[%H:%M:%S]")
    entry = f"{timestamp} {message}"
    logs.append(entry)
    if len(logs) > 100:
        logs.pop(0)
    print(entry)

def parse_proxy(proxy_raw):
    if not proxy_raw:
        return None
    proxy_raw = proxy_raw.strip()
    parts = proxy_raw.split(":")
    if len(parts) == 4:
        ip, port, user, pwd = parts
        return f"http://{user}:{pwd}@{ip}:{port}"
    elif len(parts) == 2:
        return f"http://{parts[0]}:{parts[1]}"
    return proxy_raw

def run_instagram_bot(session_id, group_targets, messages_list, bot_name, emoji_choice, proxy_raw):
    client = Client()
    
    proxy_url = parse_proxy(proxy_raw)
    if proxy_url:
        try:
            client.set_proxy(proxy_url)
            log_message(f"[{bot_name}] 🌐 Proxy HTTP configurat cu succes!")
        except Exception as e:
            log_message(f"[{bot_name}] ⚠️ Eroare setare proxy: {str(e)}")

    client.delay_range = [2, 4]

    log_message(f"[{bot_name}] Conectare securizată în curs...")
    try:
        client.login_by_sessionid(session_id.strip())
        log_message(f"[{bot_name}] Conexiune stabilită cu succes!")
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
            
            if target_group in group_id_cache:
                saved_thread_id = group_id_cache[target_group]
                try:
                    chat_thread = client.direct_thread(saved_thread_id)
                except Exception:
                    chat_thread = None

            if not chat_thread:
                log_message(f"[{bot_name}] Caut ținta în inbox: '{target_group}'...")
                try:
                    threads = client.direct_threads(amount=25)
                    for thread in threads:
                        thread_name = getattr(thread, 'thread_title', None) or getattr(thread, 'title', None) or ""
                        if target_group.lower() in thread_name.lower() or target_group == str(thread.id):
                            chat_thread = thread
                            group_id_cache[target_group] = thread.id
                            log_message(f"[{bot_name}] 📌 ID salvat automat pentru '{target_group}' (ID: {thread.id})")
                            break
                except Exception as e:
                    log_message(f"[{bot_name}] ⚠️ Eroare la căutarea grupului: {str(e)}")
            
            if chat_thread:
                try:
                    message_text = messages_list[msg_index % len(messages_list)]
                    msg_index += 1
                    
                    sent_msg = client.direct_send(message_text, thread_ids=[chat_thread.id])
                    messages_sent_in_session += 1
                    log_message(f"[{bot_name}] 🎯 Trimis pe '{target_group}' (Total: {messages_sent_in_session})")
                    
                    if emoji_choice:
                        try:
                            msg_id = None
                            if isinstance(sent_msg, list) and len(sent_msg) > 0:
                                first_item = sent_msg[0]
                                msg_id = getattr(first_item, 'id', None) or (first_item.get('id') if isinstance(first_item, dict) else None)
                            elif hasattr(sent_msg, 'id'):
                                msg_id = sent_msg.id
                            elif isinstance(sent_msg, dict):
                                msg_id = sent_msg.get('id')

                            if not msg_id:
                                messages_in_chat = client.direct_messages(chat_thread.id, amount=1)
                                if messages_in_chat:
                                    msg_id = messages_in_chat[0].id

                            if msg_id:
                                client.private_request(
                                    f"direct_v2/threads/{chat_thread.id}/reactions/item/{msg_id}/",
                                    data={"reaction_type": "emoji", "reaction_value": emoji_choice, "node_type": "item"}
                                )
                                log_message(f"[{bot_name}] ⭐ Autoreact aplicat cu succes: {emoji_choice}")
                            else:
                                log_message(f"[{bot_name}] ⚠️ Nu s-a putut identifica ID-ul mesajului pentru react.")
                        except Exception as react_err:
                            log_message(f"[{bot_name}] ⚠️ Eroare detaliată autoreact: {str(react_err)}")

                except Exception as e:
                    log_message(f"[{bot_name}] ⚠️ Eroare la trimitere: {str(e)}")
            else:
                log_message(f"[{bot_name}] ⚠️ Ținta '{target_group}' nu a fost găsită.")

            stealth_sleep = random.uniform(3.0, 5.0)
            
            if messages_sent_in_session > 0 and messages_sent_in_session % 30 == 0:
                fatigue_pause = random.uniform(30.0, 60.0)
                log_message(f"[{bot_name}] 🛡️ S-au trimis 30 de mesaje. Pauză scurtă de {int(fatigue_pause)} secunde...")
                time.sleep(fatigue_pause)
            else:
                time.sleep(stealth_sleep)
            
        time.sleep(5)

@app.route("/", methods=["GET", "POST"])
def index():
    global logs, bot_status, group_id_cache
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "start" and not bot_status["running"]:
            sessions_raw = request.form.get("sessions", "")
            groups_raw = request.form.get("groups", "")
            messages_raw = request.form.get("messages", "")
            emoji_choice = request.form.get("emoji", "").strip()
            proxy_raw = request.form.get("proxy", "").strip()
            
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
                log_message(f"🚀 Test pornit cu Autoreact complet funcțional (3-5s) cu {len(sessions)} conturi.")
                
                for idx, session in enumerate(sessions, start=1):
                    bot_name = f"Agent #{idx}"
                    t = threading.Thread(target=run_instagram_bot, args=(session, groups, messages, bot_name, emoji_choice, proxy_raw))
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
    <title>Instagram Fast Test Bot</title>
    <style>
        body { background: #090d16; color: #38bdf8; font-family: monospace; padding: 20px; }
        .container { max-width: 800px; margin: auto; background: #111827; padding: 20px; border-radius: 8px; border: 1px solid #1f2937; box-shadow: 0 0 20px rgba(0,0,0,0.8); }
        textarea, input { width: 100%; background: #030712; color: #e2e8f0; border: 1px solid #374151; padding: 10px; margin-top: 5px; margin-bottom: 15px; border-radius: 4px; box-sizing: border-box; }
        button { padding: 12px 20px; font-weight: bold; border: none; border-radius: 4px; cursor: pointer; text-transform: uppercase; }
        .btn-start { background: #10b981; color: white; width: 100%; }
        .btn-stop { background: #ef4444; color: white; width: 100%; }
        .logs { background: #020617; padding: 15px; height: 300px; overflow-y: scroll; border: 1px solid #1f2937; font-size: 12px; border-radius: 4px; white-space: pre-wrap; color: #34d399; }
    </style>
</head>
<body>
    <div class="container">
        <h2>⚡ Instagram Test Bot (Autoreact Fix 2)</h2>
        <form method="POST">
            <label><b>Session ID-uri:</b></label>
            <textarea name="sessions" rows="2" placeholder="cookie1, cookie2..."></textarea>
            
            <label><b>Grupuri:</b></label>
            <textarea name="groups" rows="3" placeholder="Grup 1&#10;Grup 2"></textarea>

            <label><b>Mesaje:</b></label>
            <textarea name="messages" rows="4" placeholder="Mesaj 1&#10;Mesaj 2"></textarea>

            <label><b>Proxy:</b></label>
            <input type="text" name="proxy" value="191.96.254.138:6185:fvuubeod:0xk9re2xi909">

            <label><b>Emoji pentru Autoreact:</b></label>
            <input type="text" name="emoji" placeholder="Ex: 🔥">

            {% if running %}
                <button type="submit" name="action" value="stop" class="btn-stop">Oprește Toți Agenții</button>
            {% else %}
                <button type="submit" name="action" value="start" class="btn-start">Pornește Testul</button>
            {% endif %}
        </form>

        <h3 style="margin-top: 25px; color: #f3f4f6;">Jurnal:</h3>
        <div class="logs">{% for log in logs %}{{ log }}&#10;{% endfor %}</div>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
