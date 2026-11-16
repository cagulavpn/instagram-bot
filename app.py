import os
import time
import threading
from flask import Flask, render_template_string, request
from instagrapi import Client

app = Flask(__name__)

bot_status = {"running": False}

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

def spam_worker(client, thread_id, target_name, messages_list):
    """Worker paralel dedicat pentru viteză maximă absolută fără limite"""
    msg_idx = 0
    while bot_status["running"]:
        try:
            msg = messages_list[msg_idx % len(messages_list)]
            msg_idx += 1
            client.direct_send(msg, thread_ids=[thread_id])
        except Exception:
            pass
        # Fără sleep pentru viteză nelimitată

def run_instagram_bot(session_id, group_targets, messages_list, proxy_raw):
    client = Client()
    
    proxy_url = parse_proxy(proxy_raw)
    if proxy_url:
        try:
            client.set_proxy(proxy_url)
        except Exception:
            pass

    client.delay_range = [0, 0]

    try:
        client.login_by_sessionid(session_id.strip())
    except Exception:
        return

    # Pre-caching instantaneu pentru ID-urile grupurilor
    resolved_threads = {}
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
                    break
    except Exception:
        pass

    if not resolved_threads:
        return

    # Lansare fire paralele instant pe fiecare grup
    worker_threads = []
    for target_name, thread_id in resolved_threads.items():
        t = threading.Thread(target=spam_worker, args=(client, thread_id, target_name, messages_list))
        t.daemon = True
        t.start()
        worker_threads.append(t)

    while bot_status["running"]:
        time.sleep(0.5)

@app.route("/", methods=["GET", "POST"])
def index():
    global bot_status
    status_msg = ""
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
            
            if sessions and groups and messages:
                bot_status["running"] = True
                status_msg = "⚡ DEMONIC CORE ACTIVAT: Fluxul de mesaje a fost eliberat la viteză maximă!"
                
                for session in sessions:
                    t = threading.Thread(target=run_instagram_bot, args=(session, groups, messages, proxy_raw))
                    t.daemon = True
                    t.start()
                    
        elif action == "stop":
            bot_status["running"] = False
            status_msg = "🛑 S-a ordonat oprirea forțată a sistemului."

    return render_template_string(HTML_TEMPLATE, running=bot_status["running"], status_msg=status_msg)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram Bloodline Turbo Panel</title>
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
                        bordercolor: '#2a0e14'
                    }
                }
            }
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #050203; }
        .font-mono { font-family: 'JetBrains Mono', monospace; }
        .font-title { font-family: 'Cinzel', serif; }
        .smoke-glow {
            box-shadow: 0 0 35px rgba(220, 38, 38, 0.15), inset 0 0 15px rgba(220, 38, 38, 0.05);
        }
    </style>
</head>
<body class="bg-void text-slate-100 min-h-screen py-12 px-4 sm:px-6 lg:px-8 flex flex-col justify-between selection:bg-blood selection:text-white">

    <div class="max-w-xl mx-auto w-full">
        <!-- Header -->
        <div class="flex items-center justify-between bg-smoke border border-bordercolor p-6 rounded-2xl shadow-2xl mb-6 smoke-glow backdrop-blur-xl">
            <div class="flex items-center gap-3.5">
                <span class="p-3 bg-blood/10 text-bloodglow rounded-xl border border-blood/30 text-xl shadow-lg shadow-blood/20 animate-pulse">🔥</span>
                <div>
                    <h1 class="text-lg font-bold tracking-wider text-rose-100 font-title">BLOODLINE CORE</h1>
                    <p class="text-xs text-rose-500/80 font-mono tracking-tight">ANIME SHADOW ENGINE // MAX SPEED</p>
                </div>
            </div>
            <div class="flex items-center gap-2 px-3.5 py-1.5 rounded-full border {% if running %}bg-blood/20 border-blood/50 text-rose-300 shadow-lg shadow-blood/30{% else %}bg-slate-900/80 border-slate-800 text-slate-400{% endif %} text-xs font-medium">
                <span class="w-2 h-2 rounded-full {% if running %}bg-bloodglow animate-ping{% else %}bg-slate-600{% endif %}"></span>
                <span>{% if running %}ACTIV (FURIOS){% else %}STANDBY{% endif %}</span>
            </div>
        </div>

        {% if status_msg %}
        <div class="mb-6 p-4 rounded-xl border border-blood/30 bg-smoke text-xs text-rose-300 text-center font-medium shadow-md shadow-blood/10">
            {{ status_msg }}
        </div>
        {% endif %}

        <!-- Main Card -->
        <div class="bg-smoke border border-bordercolor p-6 sm:p-8 rounded-2xl shadow-2xl smoke-glow space-y-5">
            <form method="POST" class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-rose-400/80 mb-1.5">Session ID-uri (Conturi)</label>
                    <textarea name="sessions" rows="2" placeholder="cookie_1, cookie_2..." class="w-full bg-void border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-700 focus:outline-none focus:border-blood focus:ring-1 focus:ring-blood transition shadow-inner"></textarea>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-rose-400/80 mb-1.5">Grupuri Țintă (câte unul pe rând)</label>
                    <textarea name="groups" rows="3" placeholder="Grup 1&#10;Grup 2" class="w-full bg-void border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-700 focus:outline-none focus:border-blood focus:ring-1 focus:ring-blood transition shadow-inner"></textarea>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-rose-400/80 mb-1.5">Mesaje de Trimis</label>
                    <textarea name="messages" rows="3" placeholder="Mesaj 1&#10;Mesaj 2" class="w-full bg-void border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-700 focus:outline-none focus:border-blood focus:ring-1 focus:ring-blood transition shadow-inner"></textarea>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-rose-400/80 mb-1.5">Proxy HTTP</label>
                    <input type="text" name="proxy" value="191.96.254.138:6185:fvuubeod:0xk9re2xi909" class="w-full bg-void border border-bordercolor rounded-xl px-4 py-3 text-sm font-mono text-rose-200/90 focus:outline-none focus:border-blood transition shadow-inner">
                </div>

                <div class="pt-3">
                    {% if running %}
                        <button type="submit" name="action" value="stop" class="w-full py-4 px-4 bg-gradient-to-r from-red-700 to-rose-700 hover:from-red-600 hover:to-rose-600 text-white font-bold tracking-wider rounded-xl shadow-lg shadow-red-900/50 transition duration-200 flex items-center justify-center gap-2 cursor-pointer text-sm font-title border border-red-500/40">
                            <span>⏹ OPREȘTE MĂCELUL</span>
                        </button>
                    {% else %}
                        <button type="submit" name="action" value="start" class="w-full py-4 px-4 bg-gradient-to-r from-red-600 via-rose-600 to-blood hover:from-red-500 hover:to-rose-500 text-white font-bold tracking-wider rounded-xl shadow-xl shadow-blood/40 transition duration-200 flex items-center justify-center gap-2 cursor-pointer text-sm font-title border border-red-400/50">
                            <span>🔥 ACTIVEAZĂ PUTEREA MAXIMĂ (TURBO)</span>
                        </button>
                    {% endif %}
                </div>
            </form>
        </div>
    </div>

    <footer class="text-center text-xs text-rose-900/60 font-mono tracking-widest mt-8">
        // DARK ANIME EDITION &bull; UNLIMITED FLUX //
    </footer>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
