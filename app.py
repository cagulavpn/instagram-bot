import os
import time
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
    """Worker optimizat pentru trimitere rapidă în grupuri"""
    msg_idx = 0
    sent_count = 0
    while bot_status["running"]:
        try:
            msg = messages_list[msg_idx % len(messages_list)]
            msg_idx += 1
            client.direct_send(msg, thread_ids=[thread_id])
            sent_count += 1
            log_message(f"[{bot_name}] 🚀 Trimis pe '{target_name}' (Total: {sent_count})")
            time.sleep(0.3)
        except Exception as e:
            log_message(f"[{bot_name}] ⚠️ Eroare pe '{target_name}': {str(e)}")
            time.sleep(1)

def run_instagram_bot(account_line, group_targets, messages_list, bot_name, proxy_raw):
    client = Client()
    
    # Amprentă Android (Samsung Galaxy S9)
    client.set_device({
        "app_version": "269.0.0.18.75",
        "android_version": 26,
        "android_release": "8.0.0",
        "dpi": "480dpi",
        "resolution": "1080x1920",
        "manufacturer": "Samsung",
        "device": "Galaxy S9",
        "model": "SM-G960F",
        "cpu": "exynos9810",
        "version_code": "314853275"
    })

    proxy_url = parse_proxy(proxy_raw)
    if proxy_url:
        try:
            client.set_proxy(proxy_url)
            log_message(f"[{bot_name}] 🌐 Proxy setat cu succes.")
        except Exception as e:
            log_message(f"[{bot_name}] ⚠️ Eroare proxy: {str(e)}")

    client.delay_range = [0, 0]

    # Separăm username și parolă (format: username:parola)
    parts = account_line.split(":")
    if len(parts) < 2:
        log_message(f"[{bot_name}] ❌ Format cont invalid. Folosește: username:parola")
        return
    
    username = parts[0].strip()
    password = parts[1].strip()

    log_message(f"[{bot_name}] 🔑 Autentificare pentru @{username}...")
    try:
        client.login(username, password)
        log_message(f"[{bot_name}] ✅ Conexiune stabilită cu succes pentru @{username}!")
    except Exception as e:
        log_message(f"[{bot_name}] ❌ Eroare la logare: {str(e)}")
        return

    resolved_threads = {}
    try:
        log_message(f"[{bot_name}] 🔍 Caut grupurile țintă în inbox...")
        threads = client.direct_threads(amount=40)
        for target in group_targets:
            target_clean = target.strip()
            if not target_clean:
                continue
            found = False
            for thread in threads:
                thread_name = getattr(thread, 'thread_title', None) or getattr(thread, 'title', None) or ""
                if target_clean.lower() in thread_name.lower() or target_clean == str(thread.id):
                    resolved_threads[target_clean] = thread.id
                    log_message(f"[{bot_name}] 📌 Găsit: '{target_clean}' -> ID {thread.id}")
                    found = True
                    break
            if not found:
                log_message(f"[{bot_name}] ⚠️ Negăsit în inbox: '{target_clean}'")
    except Exception as e:
        log_message(f"[{bot_name}] ⚠️ Eroare la citirea inbox-ului: {str(e)}")

    if not resolved_threads:
        log_message(f"[{bot_name}] ❌ Niciun grup valid găsit. Opresc agentul.")
        return

    log_message(f"[{bot_name}] 🔥 Pornesc fluxul paralel optimizat...")
    worker_threads = []
    for target_name, thread_id in resolved_threads.items():
        t = threading.Thread(target=spam_worker, args=(client, thread_id, target_name, messages_list, bot_name))
        t.daemon = True
        t.start()
        worker_threads.append(t)

    while bot_status["running"]:
        time.sleep(0.5)

@app.route("/", methods=["GET", "POST"])
def index():
    global logs, bot_status
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "start" and not bot_status["running"]:
            accounts_raw = request.form.get("accounts", "")
            groups_raw = request.form.get("groups", "")
            messages_raw = request.form.get("messages", "")
            proxy_raw = request.form.get("proxy", "").strip()
            
            accounts = [a.strip() for a in accounts_raw.replace("\r", "").split("\n") if a.strip()]
            groups = [g.strip() for g in groups_raw.replace("\r", "").split("\n") if g.strip()]
            messages = [m.strip() for m in messages_raw.replace("\r", "").split("\n") if m.strip()]
            
            if not accounts:
                log_message("❌ Eroare: Introdu conturile (username:parola)!")
            elif not groups:
                log_message("❌ Eroare: Nu ai setat nicio țintă!")
            elif not messages:
                log_message("❌ Eroare: Nu ai adăugat mesaje!")
            else:
                bot_status["running"] = True
                logs.clear()
                log_message(f"🚀 Sistem pornit cu {len(accounts)} conturi în paralel.")
                
                for idx, account in enumerate(accounts, start=1):
                    bot_name = f"Agent #{idx}"
                    t = threading.Thread(target=run_instagram_bot, args=(account, groups, messages, bot_name, proxy_raw))
                    t.daemon = True
                    t.start()
                    
        elif action == "stop":
            bot_status["running"] = False
            log_message("⏹️ S-a ordonat oprirea sistemului.")

    return render_template_string(HTML_TEMPLATE, logs=logs, running=bot_status["running"])

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🪽KISE CAGULA🪽 - Turbo Panel</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        void: '#050203',
                        smoke: '#0f0709',
                        blood: '#dc2626',
                        bloodglow: '#ef4444',
                        bordercolor: '#3f111a'
                    }
                }
            }
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
        
        body { 
            font-family: 'Plus Jakarta Sans', sans-serif; 
            background-color: #050203;
            background-image: 
                radial-gradient(circle at 50% 0%, rgba(220, 38, 38, 0.35) 0%, rgba(5, 2, 3, 0.88) 75%),
                linear-gradient(to bottom, rgba(5, 2, 3, 0.65), rgba(5, 2, 3, 0.95)),
                url('https://wallpapercave.com/wp/wp1837544.jpg');
            background-size: cover;
            background-position: center top;
            background-attachment: fixed;
        }
        
        .font-mono { font-family: 'JetBrains Mono', monospace; }
        .font-title { font-family: 'Cinzel', serif; }
        
        .glass-smoke {
            background: rgba(15, 7, 9, 0.82);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow: 0 0 40px rgba(220, 38, 38, 0.25), inset 0 0 20px rgba(220, 38, 38, 0.08);
        }
        
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #050203; }
        ::-webkit-scrollbar-thumb { background: #3f111a; border-radius: 4px; }
    </style>
</head>
<body class="text-slate-100 min-h-screen py-10 px-4 sm:px-6 lg:px-8 flex flex-col justify-between selection:bg-blood selection:text-white">

    <div class="max-w-2xl mx-auto w-full space-y-6">
        <!-- Header -->
        <div class="flex items-center justify-between glass-smoke border border-bordercolor p-6 rounded-2xl shadow-2xl">
            <div class="flex items-center gap-3.5">
                <span class="p-3 bg-blood/20 text-bloodglow rounded-xl border border-blood/40 text-xl shadow-lg shadow-blood/30 animate-pulse">🔥</span>
                <div>
                    <h1 class="text-lg sm:text-xl font-black tracking-wider text-white font-title drop-shadow-[0_2px_10px_rgba(239,68,68,0.8)]">🪽KISE CAGULA🪽</h1>
                    <p class="text-[11px] text-rose-400 font-mono tracking-widest uppercase">GENERATION OF MIRACLES // LOGIN DIRECT</p>
                </div>
            </div>
            <div class="flex items-center gap-2 px-3.5 py-1.5 rounded-full border {% if running %}bg-blood/30 border-blood/60 text-rose-200 shadow-lg shadow-blood/40{% else %}bg-black/60 border-rose-950 text-slate-400{% endif %} text-xs font-medium">
                <span class="w-2 h-2 rounded-full {% if running %}bg-bloodglow animate-ping{% else %}bg-slate-600{% endif %}"></span>
                <span>{% if running %}ACTIV{% else %}STANDBY{% endif %}</span>
            </div>
        </div>

        <!-- Main Card -->
        <div class="glass-smoke border border-bordercolor p-6 sm:p-8 rounded-2xl shadow-2xl space-y-5">
            <form method="POST" class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-rose-400 mb-1.5">Conturi (Format: username:parola)</label>
                    <textarea name="accounts" rows="2" placeholder="utilizator:parola" class="w-full bg-black/75 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blood focus:ring-1 focus:ring-blood transition shadow-inner"></textarea>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-rose-400 mb-1.5">Grupuri Țintă (câte unul pe rând)</label>
                        <textarea name="groups" rows="3" placeholder="Grup 1&#10;Grup 2" class="w-full bg-black/75 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blood focus:ring-1 focus:ring-blood transition shadow-inner"></textarea>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-rose-400 mb-1.5">Mesaje de Trimis</label>
                        <textarea name="messages" rows="3" placeholder="Mesaj 1&#10;Mesaj 2" class="w-full bg-black/75 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blood focus:ring-1 focus:ring-blood transition shadow-inner"></textarea>
                    </div>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-rose-400 mb-1.5">Proxy HTTP</label>
                    <input type="text" name="proxy" value="38.154.185.97:6370:fvuubeod:0xk9re2xi909" class="w-full bg-black/75 border border-bordercolor rounded-xl px-4 py-3 text-sm font-mono text-rose-200 focus:outline-none focus:border-blood transition shadow-inner">
                </div>

                <div class="pt-3">
                    {% if running %}
                        <button type="submit" name="action" value="stop" class="w-full py-4 px-4 bg-gradient-to-r from-red-800 to-rose-700 hover:from-red-700 hover:to-rose-600 text-white font-bold tracking-wider rounded-xl shadow-lg shadow-red-900/60 transition duration-200 flex items-center justify-center gap-2 cursor-pointer text-sm font-title border border-red-500/50">
                            <span>⏹ OPREȘTE SISTEMUL</span>
                        </button>
                    {% else %}
                        <button type="submit" name="action" value="start" class="w-full py-4 px-4 bg-gradient-to-r from-red-700 via-rose-600 to-blood hover:from-red-600 hover:to-rose-500 text-white font-bold tracking-wider rounded-xl shadow-xl shadow-blood/50 transition duration-200 flex items-center justify-center gap-2 cursor-pointer text-sm font-title border border-red-400/50">
                            <span>🔥 PORNEȘTE CU USER & PAROLĂ</span>
                        </button>
                    {% endif %}
                </div>
            </form>

            <!-- Live Console Box -->
            <div class="space-y-2 pt-4 border-t border-bordercolor">
                <div class="flex items-center justify-between">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-rose-400">Jurnal Live (Consolă)</h3>
                    <span class="text-[10px] text-rose-500 font-mono">Auto-scroll activ</span>
                </div>
                <div id="logBox" class="bg-black/90 border border-bordercolor rounded-xl p-4 h-48 overflow-y-auto font-mono text-xs text-rose-400 leading-relaxed shadow-inner space-y-1">
                    {% for log in logs %}
                        <div>{{ log }}</div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>

    <footer class="text-center text-xs text-rose-400/60 font-mono tracking-widest mt-8 drop-shadow">
        // 🪽KISE CAGULA🪽 &bull; GENERATION OF MIRACLES //
    </footer>

    <script>
        const logBox = document.getElementById('logBox');
        if (logBox) {
            logBox.scrollTop = logBox.scrollHeight;
        }

        {% if running %}
        setTimeout(() => {
            location.reload();
        }, 2000);
        {% endif %}
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
