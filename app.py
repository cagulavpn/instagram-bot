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

def account_worker(session_id, group_targets, messages_list, proxy_raw):
    """Worker independent pentru fiecare cont în parte, rulat în paralel absolut"""
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

    # Căutare rapidă a ID-urilor grupurilor la pornire
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

    # Sub-workeri paraleli pentru fiecare grup al acestui cont
    def group_spam_loop(thread_id):
        msg_idx = 0
        while bot_status["running"]:
            try:
                msg = messages_list[msg_idx % len(messages_list)]
                msg_idx += 1
                client.direct_send(msg, thread_ids=[thread_id])
            except Exception:
                pass

    group_threads = []
    for _, thread_id in resolved_threads.items():
        gt = threading.Thread(target=group_spam_loop, args=(thread_id,))
        gt.daemon = True
        gt.start()
        group_threads.append(gt)

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
                status_msg = f"Sistem pornit cu succes pe {len(sessions)} conturi în paralel!"
                
                # Porneste un fir separat pentru FIECARE cont în parte
                for session in sessions:
                    t = threading.Thread(target=account_worker, args=(session, groups, messages, proxy_raw))
                    t.daemon = True
                    t.start()
                    
        elif action == "stop":
            bot_status["running"] = False
            status_msg = "Sistemul a fost oprit."

    return render_template_string(HTML_TEMPLATE, running=bot_status["running"], status_msg=status_msg)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram Flash Multi-Account Panel</title>
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
    </style>
</head>
<body class="bg-darker text-slate-100 min-h-screen py-12 px-4 sm:px-6 lg:px-8 flex flex-col justify-between">

    <div class="max-w-xl mx-auto w-full">
        <!-- Header -->
        <div class="flex items-center justify-between bg-card border border-bordercolor p-6 rounded-2xl shadow-2xl mb-6">
            <div class="flex items-center gap-3">
                <span class="p-2.5 bg-rose-500/10 text-rose-400 rounded-xl border border-rose-500/20 text-xl">⚡</span>
                <div>
                    <h1 class="text-lg font-bold tracking-tight text-white">Instagram Flash Panel</h1>
                    <p class="text-xs text-slate-400">Viteză maximă multi-account</p>
                </div>
            </div>
            <div class="flex items-center gap-2 px-3.5 py-1.5 rounded-full border {% if running %}bg-emerald-500/10 border-emerald-500/30 text-emerald-400{% else %}bg-slate-800/50 border-slate-700 text-slate-400{% endif %} text-xs font-medium">
                <span class="w-2 h-2 rounded-full {% if running %}bg-emerald-400 animate-pulse{% else %}bg-slate-500{% endif %}"></span>
                <span>{% if running %}Activ{% else %}Oprit{% endif %}</span>
            </div>
        </div>

        {% if status_msg %}
        <div class="mb-6 p-4 rounded-xl border border-bordercolor bg-card text-xs text-slate-300 text-center font-medium">
            {{ status_msg }}
        </div>
        {% endif %}

        <!-- Main Card -->
        <div class="bg-card border border-bordercolor p-6 sm:p-8 rounded-2xl shadow-2xl space-y-5">
            <form method="POST" class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">Session ID-uri (mai multe conturi separate prin virgulă)</label>
                    <textarea name="sessions" rows="2" placeholder="cookie_1, cookie_2..." class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-rose-500 transition"></textarea>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">Grupuri Țintă (câte unul pe rând)</label>
                    <textarea name="groups" rows="3" placeholder="Grup 1&#10;Grup 2" class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-rose-500 transition"></textarea>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">Mesaje de Trimis</label>
                    <textarea name="messages" rows="3" placeholder="Mesaj 1&#10;Mesaj 2" class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-rose-500 transition"></textarea>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">Proxy HTTP</label>
                    <input type="text" name="proxy" value="191.96.254.138:6185:fvuubeod:0xk9re2xi909" class="w-full bg-darker/70 border border-bordercolor rounded-xl px-4 py-3 text-sm font-mono text-slate-200 focus:outline-none focus:border-rose-500 transition">
                </div>

                <div class="pt-3">
                    {% if running %}
                        <button type="submit" name="action" value="stop" class="w-full py-3.5 px-4 bg-rose-500 hover:bg-rose-600 text-white font-semibold rounded-xl shadow-lg shadow-rose-500/20 transition duration-200 flex items-center justify-center gap-2 cursor-pointer text-sm">
                            <span>⏹ Oprește Sistemul</span>
                        </button>
                    {% else %}
                        <button type="submit" name="action" value="start" class="w-full py-3.5 px-4 bg-rose-600 hover:bg-rose-500 text-white font-semibold rounded-xl shadow-lg shadow-rose-600/20 transition duration-200 flex items-center justify-center gap-2 cursor-pointer text-sm">
                            <span>🚀 Pornește Flash Multi-Account (Viteză Maximă)</span>
                        </button>
                    {% endif %}
                </div>
            </form>
        </div>
    </div>

    <footer class="text-center text-xs text-slate-600 mt-8">
        Instagram Flash Multi-Account Control &bull; Full Parallel Engine
    </footer>
</body>
</html>
