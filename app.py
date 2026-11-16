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
    """Worker paralel dedicat pentru viteză maximă, cu afișare de erori în consolă"""
    msg_idx = 0
    while bot_status["running"]:
        try:
            msg = messages_list[msg_idx % len(messages_list)]
            msg_idx += 1
            client.direct_send(msg, thread_ids=[thread_id])
            print(f"[SUCCESS] Trimis pe '{target_name}'")
        except Exception as e:
            print(f"[ERROR LA TRIMITERE] Pe '{target_name}': {str(e)}")
        # O micro-pauză de securitate de 0.05s ca să nu blocheze nucleul complet
        time.sleep(0.05)

def run_instagram_bot(session_id, group_targets, messages_list, proxy_raw):
    client = Client()
    
    proxy_url = parse_proxy(proxy_raw)
    if proxy_url:
        try:
            client.set_proxy(proxy_url)
            print(f"[PROXY] Setat cu succes pentru sesiune.")
        except Exception as e:
            print(f"[PROXY ERROR] {str(e)}")

    client.delay_range = [0, 0]

    print(f"[LOGIN] Încercare de autentificare cu sesiune...")
    try:
        client.login_by_sessionid(session_id.strip())
        print(f"[LOGIN] Autentificare reușită!")
    except Exception as e:
        print(f"[LOGIN ERROR] Eroare sesiune: {str(e)}")
        return

    # Pre-caching instantaneu pentru ID-urile grupurilor
    resolved_threads = {}
    try:
        print(f"[CACHE] Caut grupurile țintă în inbox...")
        threads = client.direct_threads(amount=40)
        for target in group_targets:
            target_clean = target.strip()
            if not target_clean:
                continue
            for thread in threads:
                thread_name = getattr(thread, 'thread_title', None) or getattr(thread, 'title', None) or ""
                if target_clean.lower() in thread_name.lower() or target_clean == str(thread.id):
                    resolved_threads[target_clean] = thread.id
                    print(f"[FOUND] Grup găsit: '{target_clean}' -> ID: {thread.id}")
                    break
    except Exception as e:
        print(f"[CACHE ERROR] {str(e)}")

    if not resolved_threads:
        print(f"[EROARE] Niciun grup țintă valid nu a fost găsit în inbox-ul acestui cont!")
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
                status_msg = "⚡ KISE CAGULA CORE ACTIVAT: Fluxul a fost eliberat!"
                
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
            background: rgba(15, 7, 9, 0.78);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow: 0 0 40px rgba(220, 38, 38, 0.25), inset 0 0 20px rgba(220, 38, 38, 0.08);
        }
    </style>
</head>
<body class="text-slate-100 min-h-screen py-10 px-4 sm:px-6 lg:px-8 flex flex-col justify-between selection:bg-blood selection:text-white">

    <div class="max-w-xl mx-auto w-full">
        <!-- Header -->
        <div class="flex items-center justify-between glass-smoke border border-bordercolor p-6 rounded-2xl shadow-2xl mb-6">
            <div class="flex items-center gap-3.5">
                <span class="p-3 bg-blood/20 text-bloodglow rounded-xl border border-blood/40 text-xl shadow-lg shadow-blood/30 animate-pulse">🔥</span>
                <div>
                    <h1 class="text-lg sm:text-xl font-black tracking-wider text-white font-title drop-shadow-[0_2px_10px_rgba(239,68,68,0.8)]">🪽KISE CAGULA🪽</h1>
                    <p class="text-[11px] text-rose-400 font-mono tracking-widest uppercase">GENERATION OF MIRACLES // TURBO</p>
                </div>
            </div>
            <div class="flex items-center gap-2 px-3.5 py-1.5 rounded-full border {% if running %}bg-blood/30 border-blood/60 text-rose-200 shadow-lg shadow-blood/40{% else %}bg-black/60 border-rose-950 text-slate-400{% endif %} text-xs font-medium">
                <span class="w-2 h-2 rounded-full {% if running %}bg-bloodglow animate-ping{% else %}bg-slate-600{% endif %}"></span>
                <span>{% if running %}ACTIV{% else %}STANDBY{% endif %}</span>
            </div>
        </div>

        {% if status_msg %}
        <div class="mb-6 p-4 rounded-xl border border-blood/40 glass-smoke text-xs text-rose-200 text-center font-medium shadow-md shadow-blood/20">
            {{ status_msg }}
        </div>
        {% endif %}

        <!-- Main Card -->
        <div class="glass-smoke border border-bordercolor p-6 sm:p-8 rounded-2xl shadow-2xl space-y-5">
            <form method="POST" class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-rose-400 mb-1.5">Session ID-uri (Conturi)</label>
                    <textarea name="sessions" rows="2" placeholder="cookie_1, cookie_2..." class="w-full bg-black/75 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blood focus:ring-1 focus:ring-blood transition shadow-inner"></textarea>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-rose-400 mb-1.5">Grupuri Țintă (câte unul pe rând)</label>
                    <textarea name="groups" rows="3" placeholder="Grup 1&#10;Grup 2" class="w-full bg-black/75 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blood focus:ring-1 focus:ring-blood transition shadow-inner"></textarea>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-rose-400 mb-1.5">Mesaje de Trimis</label>
                    <textarea name="messages" rows="3" placeholder="Mesaj 1&#10;Mesaj 2" class="w-full bg-black/75 border border-bordercolor rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blood focus:ring-1 focus:ring-blood transition shadow-inner"></textarea>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-rose-400 mb-1.5">Proxy HTTP</label>
                    <input type="text" name="proxy" value="191.96.254.138:6185:fvuubeod:0xk9re2xi909" class="w-full bg-black/75 border border-bordercolor rounded-xl px-4 py-3 text-sm font-mono text-rose-200 focus:outline-none focus:border-blood transition shadow-inner">
                </div>

                <div class="pt-3">
                    {% if running %}
                        <button type="submit" name="action" value="stop" class="w-full py-4 px-4 bg-gradient-to-r from-red-800 to-rose-700 hover:from-red-700 hover:to-rose-600 text-white font-bold tracking-wider rounded-xl shadow-lg shadow-red-900/60 transition duration-200 flex items-center justify-center gap-2 cursor-pointer text-sm font-title border border-red-500/50">
                            <span>⏹ OPREȘTE SISTEMUL</span>
                        </button>
                    {% else %}
                        <button type="submit" name="action" value="start" class="w-full py-4 px-4 bg-gradient-to-r from-red-700 via-rose-600 to-blood hover:from-red-600 hover:to-rose-500 text-white font-bold tracking-wider rounded-xl shadow-xl shadow-blood/50 transition duration-200 flex items-center justify-center gap-2 cursor-pointer text-sm font-title border border-red-400/50">
                            <span>🔥 ACTIVEAZĂ VITEZA MAXIMĂ (TURBO)</span>
                        </button>
                    {% endif %}
                </div>
            </form>
        </div>
    </div>

    <footer class="text-center text-xs text-rose-400/60 font-mono tracking-widest mt-8 drop-shadow">
        // 🪽KISE CAGULA🪽 &bull; GENERATION OF MIRACLES //
    </footer>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
