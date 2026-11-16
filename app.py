import os
import time
import random
import threading
from flask import Flask, render_template_string, request
from instagrapi import Client

app = Flask(__name__)

logs = []
bot_status = {"running": False}

def log_message(message):
    global logs
    timestamp = time.strftime("[%H:%M:%S]")
    entry = f"{timestamp} {message}"
    logs.append(entry)
    if len(logs) > 150:
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

def spam_worker(client, thread_id, target_name, messages_list, bot_name):
    """Worker paralel dedicat fiecărui grup în parte pentru viteză maximă fără blocaje"""
    msg_idx = 0
    sent_count = 0
    while bot_status["running"]:
        try:
            msg = messages_list[msg_idx % len(messages_list)]
            msg_idx += 1
            client.direct_send(msg, thread_ids=[thread_id])
            sent_count += 1
            log_message(f"[{bot_name}] 🚀 [TURBO] Trimis pe '{target_name}' (Total: {sent_count})")
        except Exception as e:
            log_message(f"[{bot_name}] ⚠️ Eroare turbo pe '{target_name}': {str(e)}")
        
        # Fără sleep sau cu o pauză infimă de 0.01s pentru a forța limita maximă
        time.sleep(0.01)

def run_instagram_bot(session_id, group_targets, messages_list, bot_name, proxy_raw):
    client = Client()
    
    proxy_url = parse_proxy(proxy_raw)
    if proxy_url:
        try:
            client.set_proxy(proxy_url)
            log_message(f"[{bot_name}] 🌐 Proxy HTTP configurat cu succes!")
        except Exception as e:
            log_message(f"[{bot_name}] ⚠️ Eroare setare proxy: {str(e)}")

    client.delay_range = [0, 0]

    log_message(f"[{bot_name}] Conectare securizată în curs...")
    try:
        client.login_by_sessionid(session_id.strip())
        log_message(f"[{bot_name}] Conexiune stabilită cu succes!")
    except Exception as e:
        log_message(f"[{bot_name}] ❌ Sesiune eșuată: {str(e)}")
        return

    # Pre-caching rapid pentru toate grupurile
    resolved_threads = {}
    log_message(f"[{bot_name}] 🔍 Caut ID-urile grupurilor...")
    try:
        threads = client.direct_threads(amount=40)
        for target in group_targets:
            target_clean = target.strip()
            if not target_clean:
                continue
            for thread in threads:
                thread_name = getattr(thread, 'thread_title', None) or getattr(thread, 'title', None) or ""
                if target_clean.lower() in thread_name.lower() or target_clean == str(thread.id):
                    resolved_threads[target_clean] = thread.id
                    log_message(f"[{bot_name}] 📌 Memorat: '{target_clean}' -> ID {thread.id}")
                    break
    except Exception as e:
        log_message(f"[{bot_name}] ⚠️ Eroare cache: {str(e)}")

    if not resolved_threads:
        log_message(f"[{bot_name}] ❌ Niciun grup valid găsit. Opresc agentul.")
        return

    log_message(f"[{bot_name}] 🔥 Lantzhez sub-fire paralele pentru fiecare grup (TURBO MAX)...")
    
    # Pornim câte un sub-fir paralel (worker) pentru fiecare grup în parte!
    worker_threads = []
    for target_name, thread_id in resolved_threads.items():
        t = threading.Thread(target=spam_worker, args=(client, thread_id, target_name, messages_list, bot_name))
        t.daemon = True
        t.start()
        worker_threads.append(t)

    # Menținem agentul activ cât timp rulează botul
    while bot_status["running"]:
        time.sleep(1)

@app.route("/", methods=["GET", "POST"])
def index():
    global logs, bot_status
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "start" and not bot_status["running"]:
            sessions_raw = request.form.get("sessions", "")
            groups_raw = request.form.get("groups", "")
            messages_raw = request.form.get("messages", "")
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
                log_message(f"🚀 Pornire motor TURBO MAX cu {len(sessions)} conturi paralele.")
                
                for idx, session in enumerate(sessions, start=1):
                    bot_name = f"Agent #{idx}"
                    t = threading.Thread(target=run_instagram_bot, args=(session, groups, messages, bot_name, proxy_raw))
                    t.daemon = True
                    t.start()
                    
        elif action == "stop":
            bot_status["running"] = False
            log_message("⏹️ S-a ordonat oprirea agenților.")

    return render_template_string(HTML_TEMPLATE, logs=logs, running=bot_status["running"])

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram Turbo Max Bot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        darker: '#030712',
                        card: '#0b0f19',
                        bordercolor: '#1e293b'
                    }
                }
            }
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        body { font-family: 'Plus Jakarta Sans', sans-serif; }
        .font-mono { font-family: 'JetBrains Mono', monospace; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #030712; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
    </style>
</head>
<body class="bg-darker text-slate-100 min-h-screen py-8 px-4 sm:px-6 lg:px-8 flex flex-col justify-between">

    <div class="max-w-4xl mx-auto w-full">
        <!-- Header -->
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between bg-card border border-bordercolor p-6 rounded-2xl shadow-2xl mb-6 backdrop-blur-xl">
            <div>
                <div class="flex items-center gap-3">
                    <span class="p-2.5 bg-rose-500/10 text-rose-400 rounded-xl border border-rose-500/20 text-xl">🔥</span>
                    <h1 class="text-xl font-bold tracking-tight text-white">Instagram Turbo Max Control</h1>
                </div>
                <p class="text-xs text-slate-400 mt-1">Motor paralel cu sub-fire multiple per grup (Viteză maximă nelimitată)</p>
            </div>
            <div class="mt-4 sm:mt-0 flex items-center gap-2.5 px-3.5 py-1.5 rounded-full border {% if running %}bg-emerald-500/10 border-emerald-500/30 text-emerald-400{% else %}bg-slate-800/50 border-slate-700 text-slate-400{% endif %} text-xs font-medium">
                <span class="w-2 h-2 rounded-full {% if running %}bg-emerald-400 animate-pulse{% else %}bg-slate-500{% endif %}"></span>
                <span>{% if running %}Sistem Turbo Activ{% else %}Sistem Oprit{% endif %}</span>
            </div>
        </div>

        <!-- Main Card -->
        <div class="bg-card border border-bordercolor p-6 sm:p-8 rounded-2xl shadow-2xl space-y-6">
            <form method="POST" class="space-y-5">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Session ID-uri (separate prin virgulă)</label>
                    <textarea name="sessions" rows="2" placeholder="cookie_1, cookie_2..." class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500 transition"></textarea>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Grupuri Țintă (câte un grup pe rând)</label>
                        <textarea name="groups" rows="3" placeholder="Grup 1&#10;Grup 2" class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500 transition"></textarea>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Mesaje de Trimis (câte un mesaj pe rând)</label>
                        <textarea name="messages" rows="3" placeholder="Mesaj 1&#10;Mesaj 2" class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500 transition"></textarea>
                    </div>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Proxy HTTP (IP:Port:User:Pass)</label>
                    <input type="text" name="proxy" value="191.96.254.138:6185:fvuubeod:0xk9re2xi909" class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm font-mono text-slate-200 focus:outline-none focus:border-rose-500 transition">
                </div>

                <div class="pt-2">
                    {% if running %}
                        <button type="submit" name="action" value="stop" class="w-full py-3.5 px-4 bg-rose-500 hover:bg-rose-600 text-white font-semibold rounded-xl shadow-lg shadow-rose-500/20 transition duration-200 flex items-center justify-center gap-2 cursor-pointer">
                            <span>⏹ Oprește Toți Agenții</span>
                        </button>
                    {% else %}
                        <button type="submit" name="action" value="start" class="w-full py-3.5 px-4 bg-rose-600 hover:bg-rose-500 text-white font-semibold rounded-xl shadow-lg shadow-rose-600/20 transition duration-200 flex items-center justify-center gap-2 cursor-pointer">
                            <span>🔥 PORNEȘTE TURBO MAX (Fără Limite)</span>
                        </button>
                    {% endif %}
                </div>
            </form>

            <!-- Logs Section -->
            <div class="space-y-3 pt-4 border-t border-bordercolor">
                <div class="flex items-center justify-between">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-400">Jurnal Activ (Live Console)</h3>
                    <span class="text-xs text-slate-500 font-mono">Auto-scroll activ</span>
                </div>
                <div id="logBox" class="bg-darker border border-bordercolor rounded-xl p-4 h-64 overflow-y-auto font-mono text-xs text-emerald-400 leading-relaxed shadow-inner space-y-1">
                    {% for log in logs %}
                        <div>{{ log }}</div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>

    <footer class="text-center text-xs text-slate-600 mt-8">
        Instagram Turbo Max Bot &bull; Multi-threaded Parallel Engine
    </footer>

    <script>
        const logBox = document.getElementById('logBox');
        if (logBox) {
            logBox.scrollTop = logBox.scrollHeight;
        }

        {% if running %}
        setTimeout(() => {
            location.reload();
        }, 1200);
        {% endif %}
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
