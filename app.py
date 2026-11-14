import os
import time
import random
import asyncio
import threading
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
    if len(logs) > 150:
        logs.pop(0)
    print(entry)

async def async_send_message(client, thread_id, message_text, bot_name):
    try:
        # Rulăm cererea blocantă în background asincron prin asyncio.to_thread
        await asyncio.to_thread(client.direct_send, message_text, thread_ids=[thread_id])
        log_message(f"[{bot_name}] ⚡ ASYNC-FIRE: Mesaj livrat instant!")
    except Exception as e:
        log_message(f"[{bot_name}] ⚠️ Instagram Firewall / Limit: {str(e)}")

async def run_async_bot(session_id, group_targets, messages_list, bot_name):
    client = Client()
    client.delay_range = [0, 0]

    log_message(f"[{bot_name}] Conectare Async Engine...")
    try:
        await asyncio.to_thread(client.login_by_sessionid, session_id.strip())
        log_message(f"[{bot_name}] Conexiune Async stabilită cu succes!")
    except Exception as e:
        log_message(f"[{bot_name}] ❌ Sesiune eșuată: {str(e)}")
        return

    # Colectarea rapidă a ID-urilor
    active_threads = []
    for target_group in group_targets:
        target_group = target_group.strip()
        if not target_group:
            continue
        
        chat_thread = None
        if target_group in group_id_cache:
            try:
                chat_thread = await asyncio.to_thread(client.direct_thread, group_id_cache[target_group])
            except:
                pass
        
        if not chat_thread:
            try:
                threads = await asyncio.to_thread(client.direct_threads, amount=30)
                for thread in threads:
                    thread_name = getattr(thread, 'thread_title', None) or getattr(thread, 'title', None) or ""
                    if target_group.lower() in thread_name.lower() or target_group == str(thread.id):
                        chat_thread = thread
                        group_id_cache[target_group] = thread.id
                        break
            except Exception as e:
                log_message(f"[{bot_name}] Eroare căutare: {str(e)}")
        
        if chat_thread:
            active_threads.append(chat_thread.id)
            log_message(f"[{bot_name}] 🎯 Țintă pregătită async: {target_group}")

    if not active_threads:
        log_message(f"[{bot_name}] ❌ Nicio țintă validă.")
        return

    log_message(f"[{bot_name}] 🚀 Lansare flux Async Masiv (Batch Concurrency)...")
    
    msg_index = 0
    while bot_status["running"] and msg_index < len(messages_list) * len(active_threads) * 10:
        tasks = []
        # Construim un batch complet de mesaje trimise simultan
        for thread_id in active_threads:
            if not bot_status["running"]:
                break
            
            message_text = messages_list[msg_index % len(messages_list)]
            msg_index += 1
            
            # Adăugăm task-ul în lista asincronă
            tasks.append(async_send_message(client, thread_id, message_text, bot_name))
        
        if tasks:
            # Lansăm toate cererile în același timp prin asyncio.gather
            await asyncio.gather(*tasks)
            # Pauză microscopică între batch-uri (10 milisecunde)
            await asyncio.sleep(0.01)

    log_message(f"[{bot_name}] 🏁 Sesiunea Async s-a încheiat.")

def start_async_loop(session_id, groups, messages, bot_name):
    asyncio.run(run_async_bot(session_id, groups, messages, bot_name))

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
                log_message(f"⚡ ATENȚIE: S-a pornit Motorul Asyncio (Viteză Cuantică)!")
                
                for idx, session in enumerate(sessions, start=1):
                    bot_name = f"AsyncAgent #{idx}"
                    # Pornim bucla async într-un thread dedicat pentru a nu bloca Flask
                    t = threading.Thread(target=start_async_loop, args=(session, groups, messages, bot_name))
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
    <title>Instagram Asyncio Bot</title>
    <style>
        body { background: #080314; color: #a855f7; font-family: monospace; padding: 20px; }
        .container { max-width: 800px; margin: auto; background: #130722; padding: 20px; border-radius: 8px; border: 1px solid #3b0764; box-shadow: 0 0 30px rgba(168,85,247,0.3); }
        textarea { width: 100%; background: #03000a; color: #c084fc; border: 1px solid #581c87; padding: 10px; margin-top: 5px; margin-bottom: 15px; border-radius: 4px; box-sizing: border-box; }
        button { padding: 12px 20px; font-weight: bold; border: none; border-radius: 4px; cursor: pointer; text-transform: uppercase; }
        .btn-start { background: #9333ea; color: white; width: 100%; font-size: 16px; }
        .btn-stop { background: #4c1d95; color: white; width: 100%; font-size: 16px; }
        .logs { background: #03000a; padding: 15px; height: 350px; overflow-y: scroll; border: 1px solid #2e1065; font-size: 11px; border-radius: 4px; white-space: pre-wrap; color: #e879f9; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🔮 Instagram Asyncio Bot (High-Concurrency Engine)</h2>
        <form method="POST">
            <label><b>Session ID-uri:</b></label>
            <textarea name="sessions" rows="2" placeholder="cookie..."></textarea>
            
            <label><b>Grupuri:</b></label>
            <textarea name="groups" rows="3" placeholder="Grup..."></textarea>

            <label><b>Mesaje:</b></label>
            <textarea name="messages" rows="4" placeholder="Mesaj..."></textarea>

            {% if running %}
                <button type="submit" name="action" value="stop" class="btn-stop">Oprește Motorul Async</button>
            {% else %}
                <button type="submit" name="action" value="start" class="btn-start">LANSEAZĂ ASYNCIO 🔮</button>
            {% endif %}
        </form>

        <h3 style="margin-top: 25px; color: #e9d5ff;">Jurnal Async Engine:</h3>
        <div class="logs">{% for log in logs %}{{ log }}&#10;{% endfor %}</div>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
