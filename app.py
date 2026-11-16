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

def run_instagram_bot(session_id, group_targets, messages_list, bot_name, proxy_raw, speed_mode):
    client = Client()
    
    proxy_url = parse_proxy(proxy_raw)
    if proxy_url:
        try:
            client.set_proxy(proxy_url)
            log_message(f"[{bot_name}] 🌐 Proxy HTTP configurat cu succes!")
        except Exception as e:
            log_message(f"[{bot_name}] ⚠️ Eroare setare proxy: {str(e)}")

    client.delay_range = [0.05, 0.2]

    log_message(f"[{bot_name}] Conectare securizată în curs...")
    try:
        client.login_by_sessionid(session_id.strip())
        log_message(f"[{bot_name}] Conexiune stabilită cu succes!")
    except Exception as e:
        log_message(f"[{bot_name}] ❌ Sesiune eșuată: {str(e)}")
        return

    # Pre-caching inteligent pentru eliminarea lag-ului
    resolved_threads = {}
    log_message(f"[{bot_name}] 🔍 Caut și memorez ID-urile grupurilor țintă...")
    try:
        threads = client.direct_threads(amount=30)
        for target in group_targets:
            target_clean = target.strip()
            if not target_clean:
                continue
            found = False
            for thread in threads:
                thread_name = getattr(thread, 'thread_title', None) or getattr(thread, 'title', None) or ""
                if target_clean.lower() in thread_name.lower() or target_clean == str(thread.id):
                    resolved_threads[target_clean] = thread.id
                    log_message(f"[{bot_name}] 📌 Memorat: '{target_clean}' -> ID {thread.id}")
                    found = True
                    break
            if not found:
                log_message(f"[{bot_name}] ⚠️ Nu s-a găsit în inbox: '{target_clean}'")
    except Exception as e:
        log_message(f"[{bot_name}] ⚠️ Eroare la cache-ul grupurilor: {str(e)}")

    valid_targets = list(resolved_threads.keys())
    if not valid_targets:
        log_message(f"[{bot_name}] ❌ Niciun grup valid găsit. Opresc agentul.")
        return

    msg_index = 0
    messages_sent_in_session = 0

    mode_name = "⚡ FLASH MODE (10 msgs/s)" if speed_mode == "flash" else "Standard Speed"
    log_message(f"[{bot_name}] 🚀 Pornit în mod: {mode_name}")

    while bot_status["running"]:
        shuffled_groups = list(valid_targets)
        random.shuffle(shuffled_groups)

        for target_group in shuffled_groups:
            if not bot_status["running"]:
                break
            
            thread_id = resolved_threads.get(target_group)
            if not thread_id:
                continue

            try:
                message_text = messages_list[msg_index % len(messages_list)]
                msg_index += 1
                
                client.direct_send(message_text, thread_ids=[thread_id])
                messages_sent_in_session += 1
                log_message(f"[{bot_name}] 🎯 Trimis pe '{target_group}' (Total: {messages_sent_in_session})")

            except Exception as e:
                log_message(f"[{bot_name}] ⚠️ Eroare la trimitere: {str(e)}")

            # Setarea vitezei în funcție de opțiunea aleasă
            if speed_mode == "flash":
                time.sleep(random.uniform(0.08, 0.12))  # ~8-10 mesaje pe secundă
            else:
                time.sleep(random.uniform(0.3, 0.5))    # viteză standard rapidă
            
            # Pauză de protecție automată
            fatigue_limit = 50 if speed_mode == "flash" else 30
            if messages_sent_in_session > 0 and messages_sent_in_session % fatigue_limit == 0:
                fatigue_pause = random.uniform(5.0, 10.0) if speed_mode == "flash" else random.uniform(10.0, 20.0)
                log_message(f"[{bot_name}] 🛡️ Pauză scurtă de protecție ({int(fatigue_pause)}s)...")
                time.sleep(fatigue_pause)

        time.sleep(0.1)

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
            speed_mode = request.form.get("speed_mode", "normal")
            
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
                log_message(f"🚀 Pornire motor cu {len(sessions)} conturi (Mod: {speed_mode.upper()}).")
                
                for idx, session in enumerate(sessions, start=1):
                    bot_name = f"Agent #{idx}"
                    t = threading.Thread(target=run_instagram_bot, args=(session, groups, messages, bot_name, proxy_raw, speed_mode))
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
    <title>Instagram Flash Speed Bot</title>
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
                    <span class="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20 text-xl">⚡</span>
                    <h1 class="text-xl font-bold tracking-tight text-white">Instagram Flash Control Center</h1>
                </div>
                <p class="text-xs text-slate-400 mt-1">Alege viteza de trimitere: Standard sau ⚡ Flash (10 msgs/s)</p>
            </div>
            <div class="mt-4 sm:mt-0 flex items-center gap-2.5 px-3.5 py-1.5 rounded-full border {% if running %}bg-emerald-500/10 border-emerald-500/30 text-emerald-400{% else %}bg-slate-800/50 border-slate-700 text-slate-400{% endif %} text-xs font-medium">
                <span class="w-2 h-2 rounded-full {% if running %}bg-emerald-400 animate-pulse{% else %}bg-slate-500{% endif %}"></span>
                <span>{% if running %}Sistem Activ{% else %}Sistem Oprit{% endif %}</span>
            </div>
        </div>

        <!-- Main Card -->
        <div class="bg-card border border-bordercolor p-6 sm:p-8 rounded-2xl shadow-2xl space-y-6">
            <form method="POST" class="space-y-5">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Session ID-uri (separate prin virgulă)</label>
                    <textarea name="sessions" rows="2" placeholder="cookie_1, cookie_2..." class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition"></textarea>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Grupuri Țintă (câte un grup pe rând)</label>
                        <textarea name="groups" rows="3" placeholder="Grup 1&#10;Grup 2" class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition"></textarea>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Mesaje de Trimis (câte un mesaj pe rând)</label>
                        <textarea name="messages" rows="3" placeholder="Mesaj 1&#10;Mesaj 2" class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition"></textarea>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Proxy HTTP (IP:Port:User:Pass)</label>
                        <input type="text" name="proxy" value="191.96.254.138:6185:fvuubeod:0xk9re2xi909" class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm font-mono text-slate-200 focus:outline-none focus:border-amber-500 transition">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-amber-400 mb-2">Mod Viteză</label>
                        <select name="speed_mode" class="w-full bg-darker/70 border border-amber-500/50 rounded-xl px-4 py-3 text-sm text-slate-200 focus:outline-none focus:border-amber-500 transition">
                            <option value="normal">Standard (Sigur / Rapid)</option>
                            <option value="flash">⚡ Flash Mode (~10 msgs/s - EXTREM)</option>
                        </select>
                    </div>
                </div>

                <div class="pt-2">
                    {% if running %}
                        <button type="submit" name="action" value="stop" class="w-full py-3.5 px-4 bg-rose-500 hover:bg-rose-600 text-white font-semibold rounded-xl shadow-lg shadow-rose-500/20 transition duration-200 flex items-center justify-center gap-2 cursor-pointer">
                            <span>⏹ Oprește Toți Agenții</span>
                        </button>
                    {% else %}
                        <button type="submit" name="action" value="start" class="w-full py-3.5 px-4 bg-amber-600 hover:bg-amber-500 text-white font-semibold rounded-xl shadow-lg shadow-amber-600/20 transition duration-200 flex items-center justify-center gap-2 cursor-pointer">
                            <span>🚀 Pornește Botul</span>
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
        Instagram Flash Speed Bot &bull; Dual Mode Engine
    </footer>

    <script>
        const logBox = document.getElementById('logBox');
        if (logBox) {
            logBox.scrollTop = logBox.scrollHeight;
        }

        {% if running %}
        setTimeout(() => {
            location.reload();
        }, 1500);
        {% endif %}
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
