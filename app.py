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

def run_instagram_bot(session_id, group_targets, messages_list, bot_name, proxy_raw):
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
                    
                    client.direct_send(message_text, thread_ids=[chat_thread.id])
                    messages_sent_in_session += 1
                    log_message(f"[{bot_name}] 🎯 Trimis pe '{target_group}' (Total: {messages_sent_in_session})")

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
                log_message(f"🚀 Bot pornit la viteză rapidă (3-5s) cu {len(sessions)} conturi.")
                
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
    <title>Instagram Multi-Bot Dashboard</title>
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
        ::-webkit-scrollbar-thumb:hover { background: #334155; }
    </style>
</head>
<body class="bg-darker text-slate-100 min-h-screen py-8 px-4 sm:px-6 lg:px-8 flex flex-col justify-between">

    <div class="max-w-4xl mx-auto w-full">
        <!-- Header -->
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between bg-card border border-bordercolor p-6 rounded-2xl shadow-2xl mb-6 backdrop-blur-xl">
            <div>
                <div class="flex items-center gap-3">
                    <span class="p-2.5 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20 text-xl">⚡</span>
                    <h1 class="text-xl font-bold tracking-tight text-white">Instagram Control Center</h1>
                </div>
                <p class="text-xs text-slate-400 mt-1">Sistem ultra-rapid de trimitere directă (3-5s) prin Proxy HTTP</p>
            </div>
            <div class="mt-4 sm:mt-0 flex items-center gap-2.5 px-3.5 py-1.5 rounded-full border {% if running %}bg-emerald-500/10 border-emerald-500/30 text-emerald-400{% else %}bg-slate-800/50 border-slate-700 text-slate-400{% endif %} text-xs font-medium">
                <span class="w-2 h-2 rounded-full {% if running %}bg-emerald-400 animate-pulse{% else %}bg-slate-500{% endif %}"></span>
                <span>{% if running %}Sistem Activ (Rulează){% else %}Sistem Oprit{% endif %}</span>
            </div>
        </div>

        <!-- Main Card -->
        <div class="bg-card border border-bordercolor p-6 sm:p-8 rounded-2xl shadow-2xl space-y-6">
            <form method="POST" class="space-y-5">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Session ID-uri (separate prin virgulă)</label>
                    <textarea name="sessions" rows="2" placeholder="cookie_1, cookie_2..." class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"></textarea>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Grupuri Țintă (câte un grup pe rând)</label>
                        <textarea name="groups" rows="3" placeholder="Grup 1&#10;Grup 2" class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"></textarea>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Mesaje de Trimis (câte un mesaj pe rând)</label>
                        <textarea name="messages" rows="3" placeholder="Mesaj 1&#10;Mesaj 2" class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition"></textarea>
                    </div>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Proxy HTTP (IP:Port:User:Pass)</label>
                    <input type="text" name="proxy" value="191.96.254.138:6185:fvuubeod:0xk9re2xi909" class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm font-mono text-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition">
                </div>

                <div class="pt-2">
                    {% if running %}
                        <button type="submit" name="action" value="stop" class="w-full py-3.5 px-4 bg-rose-500 hover:bg-rose-600 text-white font-semibold rounded-xl shadow-lg shadow-rose-500/20 transition duration-200 flex items-center justify-center gap-2 cursor-pointer">
                            <span>⏹ Oprește Toți Agenții</span>
                        </button>
                    {% else %}
                        <button type="submit" name="action" value="start" class="w-full py-3.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl shadow-lg shadow-indigo-600/20 transition duration-200 flex items-center justify-center gap-2 cursor-pointer">
                            <span>🚀 Pornește Botul la Viteză Maximă</span>
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

    <!-- Footer -->
    <footer class="text-center text-xs text-slate-600 mt-8">
        Instagram Multi-Bot Engine &bull; Secure Proxy Protocol
    </footer>

    <script>
        // Auto-scroll la ultimul log în timp real
        const logBox = document.getElementById('logBox');
        if (logBox) {
            logBox.scrollTop = logBox.scrollHeight;
        }

        // Auto-refresh la pagină la fiecare 3 secunde dacă botul rulează pentru a vedea jurnalele live
        {% if running %}
        setTimeout(() => {
            location.reload();
        }, 3000);
        {% endif %}
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
