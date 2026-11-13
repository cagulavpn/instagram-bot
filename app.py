import os
import time
import random
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
    <title>🪽𝐍ïght𝐋ÿfe #CGL Control (Mod Dinamic 250 Msj)</title>
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
            <label>Session ID-uri (separate prin virgulă):</label>
            <textarea name="sessionids" rows="3" required placeholder="cookie1, cookie2, cookie3..."></textarea>

            <label>Mesaje (separate prin virgulă):</label>
            <textarea name="messages" rows="3" required placeholder="Salut, Ce faci?"></textarea>

            <label>Numele sau ID-ul Grupului (sau parte din el):</label>
            <input type="text" name="groups" required placeholder="Ex: Numele grupului sau ID-ul">

            <label>Nume Nou Dorit pentru Grup (opțional - pentru protecție):</label>
            <input type="text" name="new_group_name" placeholder="Ex: 🪽𝐍ïght𝐋ÿfe #CGL">

            <button type="submit">🚀 Pornește Rotația Dinamică (250 msj)</button>
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
    if len(bot_logs) > 60:
        bot_logs.pop(0)

def run_bot(sessionids_raw, messages, groups, new_group_name):
    global bot_status, bot_thread_running
    bot_status = "În rulare (Mod Dinamic 250 msj)..."
    bot_thread_running = True
    
    sessions = [s.strip() for s in sessionids_raw.split(",") if s.strip()]
    if not sessions:
        log_message("❌ Niciun Session ID valid introdus!")
        bot_status = "Eroare (Fără conturi)"
        bot_thread_running = False
        return

    log_message(f"🔑 Încărcate {len(sessions)} conturi în sistem.")
    msg_list = [m.strip() for m in messages.split(",") if m.strip()]
    search_terms = [g.strip().lower() for g in groups.split(",") if g.strip()]
    
    loop_count = 1

    while bot_thread_running:
        log_message(f"--- Ciclu global nr. {loop_count} ---")
        
        for idx, sessionid in enumerate(sessions):
            if not bot_thread_running:
                break
                
            account_num = idx + 1
            log_message(f"🔄 Activare Cont #{account_num} (Țintă: 250 mesaje)...")
            
            client = Client()
            client.set_user_agent("Instagram 319.0.0.31.109 Android (33/13; 480dpi; 1080x2340; Samsung; SM-S918B; qcom; sm8550; en_US; 539583191)")
            
            # Încercăm logarea. Dacă contul a picat sau dă eroare, îl sărim automat.
            try:
                client.login_by_sessionid(sessionid)
                log_message(f"✅ Contul #{account_num} conectat cu succes!")
            except Exception as e:
                log_message(f"❌ CONTUL #{account_num} A PICAT / EROARE LOGARE: {e}. Trec la următorul!")
                continue

            try:
                threads = client.direct_threads(amount=30)
            except Exception as e:
                log_message(f"❌ Eroare la citirea chat-urilor pentru Cont #{account_num}: {e}. Trec mai departe!")
                continue

            selected_threads = []
            for thread in threads:
                t_id = str(thread.id).strip()
                title = thread.thread_title if thread.thread_title else ""
                title_lower = title.lower()
                
                for term in search_terms:
                    if term in t_id or (title and term in title_lower):
                        if thread not in selected_threads:
                            selected_threads.append(thread)

            if not selected_threads:
                log_message(f"⚠️ Contul #{account_num} nu a găsit grupul. Trecem la următorul cont.")
                continue

            messages_sent_by_account = 0
            target_limit = 250
            consecutive_errors = 0

            while messages_sent_by_account < target_limit and bot_thread_running:
                for thread in selected_threads:
                    if messages_sent_by_account >= target_limit or not bot_thread_running:
                        break
                        
                    title = thread.thread_title if thread.thread_title else thread.id
                    
                    # Protecție nume grup
                    if new_group_name and new_group_name.strip():
                        try:
                            if thread.thread_title != new_group_name.strip():
                                client.direct_thread_update_title(thread.id, new_group_name.strip())
                                log_message(f"🛡️ [Cont #{account_num}] Nume grup menținut!")
                        except Exception:
                            pass

                    msg = random.choice(msg_list)

                    try:
                        # Trimitere mesaj direct
                        client.direct_send(msg, thread_ids=[thread.id])
                        messages_sent_by_account += 1
                        consecutive_errors = 0 # Resetează contorul de erori dacă a trimis cu succes
                        log_message(f"✅ [Cont #{account_num}] Mesaj {messages_sent_by_account}/250 trimis")
                    except Exception as err:
                        consecutive_errors += 1
                        log_message(f"⚠️ [Cont #{account_num}] Eroare trimitere ({consecutive_errors}/5): {err}")
                        
                        # Dacă contul primește erori consecutive (de ex. a luat ban pe mesaje), 
                        # abandonăm acest cont ca să nu piardă timp și trecem instant la următorul!
                        if consecutive_errors >= 5:
                            log_message(f"🚨 Contul #{account_num} pare blocat/limitat (prea multe erori). Salt forțat la următorul cont!")
                            break
                    
                    # Secunde variabile/aleatoare între mesaje (1, 2, 3, 5, 7 secunde etc.)
                    # O valoare aleatorie între 1.5 și 6.5 secunde asigură că cele 250 de mesaje se duc în ~10 minute.
                    random_delay = random.uniform(1.5, 6.5)
                    time.sleep(random_delay)

                # Dacă s-au strâns prea multe erori, ieșim din bucla contului curent
                if consecutive_errors >= 5:
                    break

            log_message(f"🏁 Contul #{account_num} a terminat tura (sau a fost schimbat). Trecem la următorul...")
            time.sleep(5)

        loop_count += 1
        log_message("⏳ Rotație completă finalizată. Pauză scurtă înainte de a relua ciclul...")
        time.sleep(20)

@app.route('/', methods=['GET', 'POST', 'HEAD'])
def index():
    return render_template_string(HTML_TEMPLATE, status=bot_status, logs=bot_logs)

@app.route('/start', methods=['POST'])
def start_bot():
    global bot_thread_running
    bot_thread_running = False
    time.sleep(1)

    sessionids = request.form.get('sessionids')
    messages = request.form.get('messages')
    groups = request.form.get('groups')
    new_group_name = request.form.get('new_group_name')

    thread = threading.Thread(target=run_bot, args=(sessionids, messages, groups, new_group_name))
    thread.daemon = True
    thread.start()

    return render_template_string(HTML_TEMPLATE, status="Pornit (Mod Dinamic 250 mesaje / Fail-Safe Activ)...", logs=bot_logs)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
