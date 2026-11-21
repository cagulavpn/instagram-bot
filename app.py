import os
import time
import base64
import tempfile
import threading
from flask import Flask, render_template_string, request
from instagrapi import Client

try:
    from PIL import Image
except ImportError:
    Image = None

app = Flask(__name__)

bot_status = {
    "running": False,
    "delay": 50,
    "group_meta_running": False,
    "group_meta_delay": 5,
    "locked_group_name": "",
    "locked_group_photo_path": "",
    "locked_group_photo_name": "",
}

BG_IMAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background.jpg")
BG_IMAGE_DATA_URI = ""
if os.path.exists(BG_IMAGE_PATH):
    with open(BG_IMAGE_PATH, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("utf-8")
        BG_IMAGE_DATA_URI = f"data:image/jpeg;base64,{encoded}"


def log_message(message):
    timestamp = time.strftime("[%H:%M:%S]")
    print(f"{timestamp} {message}")


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


def create_authed_client(session_id, proxy_raw, bot_name):
    client = Client()

    proxy_url = parse_proxy(proxy_raw)
    if proxy_url:
        try:
            client.set_proxy(proxy_url)
            log_message(f"[{bot_name}] 🌐 Proxy setat cu succes.")
        except Exception as e:
            log_message(f"[{bot_name}] ⚠️ Eroare proxy: {str(e)}")

    client.delay_range = [0, 0]

    log_message(f"[{bot_name}] 🔑 Autentificare prin Session ID...")
    try:
        client.login_by_sessionid(session_id.strip())
        log_message(f"[{bot_name}] ✅ Conexiune stabilită cu succes prin Session ID!")
        return client
    except Exception as e:
        log_message(f"[{bot_name}] ❌ Eroare sesiune (467/Invalid): {str(e)}")
        return None


def resolve_group_threads(client, group_targets, bot_name):
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
                thread_name = getattr(thread, "thread_title", None) or getattr(thread, "title", None) or ""
                if target_clean.lower() in thread_name.lower() or target_clean == str(thread.id):
                    resolved_threads[target_clean] = str(thread.id)
                    log_message(f"[{bot_name}] 📌 Găsit: '{target_clean}' -> ID {thread.id}")
                    found = True
                    break
            if not found:
                log_message(f"[{bot_name}] ⚠️ Negăsit în inbox: '{target_clean}'")
    except Exception as e:
        log_message(f"[{bot_name}] ⚠️ Eroare la citirea inbox-ului: {str(e)}")
    return resolved_threads


def set_group_title(client, thread_id, desired_name):
    tid = str(thread_id)
    if hasattr(client, "direct_thread_update_title"):
        return client.direct_thread_update_title(tid, desired_name)
    if hasattr(client, "direct_update_title"):
        return client.direct_update_title(tid, desired_name)
    return client.private_request(
        f"direct_v2/threads/{tid}/update_title/",
        data={"title": desired_name},
    )


def set_group_photo(client, thread_id, photo_path, bot_name="GroupGuard"):
    tid = str(thread_id)
    if not photo_path or not os.path.exists(photo_path):
        raise FileNotFoundError(f"Fișierul foto lipsește: {photo_path}")

    for method_name in ("direct_thread_update_photo", "direct_thread_update_image", "direct_update_photo"):
        fn = getattr(client, method_name, None)
        if callable(fn):
            res = fn(tid, photo_path)
            log_message(f"[{bot_name}] 🖼️ Poză trimisă prin {method_name} pe thread {tid}")
            return res

    with open(photo_path, "rb") as f:
        img_bytes = f.read()

    last_err = None
    for endpoint in (
        f"direct_v2/threads/{tid}/update_group_image/",
        f"direct_v2/threads/{tid}/update_image/",
    ):
        try:
            res = client.private_request(
                endpoint,
                files={"image": ("group_photo.jpg", img_bytes, "image/jpeg")},
            )
            log_message(f"[{bot_name}] 🖼️ Poză trimisă prin {endpoint} pe thread {tid}")
            return res
        except Exception as e:
            last_err = e

    raise RuntimeError(f"Toate metodele de schimbare poză au eșuat: {last_err}")


def group_meta_worker(client, thread_id, target_name, bot_name):
    """Verifică și restaurează automat numele și poza grupului la intervalul setat (implicit 5s, 1 - 120s)"""
    tid = str(thread_id)
    while bot_status["running"]:
        try:
            desired_name = (bot_status.get("locked_group_name") or "").strip()
            photo_path = (bot_status.get("locked_group_photo_path") or "").strip()

            current_title = ""
            try:
                thread_obj = client.direct_thread(tid, amount=1)
                current_title = (
                    getattr(thread_obj, "thread_title", None)
                    or getattr(thread_obj, "title", None)
                    or ""
                )
            except Exception:
                current_title = ""

            if desired_name and current_title != desired_name:
                set_group_title(client, tid, desired_name)
                log_message(f"[{bot_name}] 🔒 Nume grup restaurat la '{desired_name}' pe '{target_name}'")

            if photo_path and os.path.exists(photo_path):
                set_group_photo(client, tid, photo_path, bot_name)
                log_message(f"[{bot_name}] 🖼️ Poză grup restaurată pe '{target_name}'")

            current_delay = max(1, min(120, int(bot_status.get("group_meta_delay", 5))))
            for _ in range(current_delay * 10):
                if not bot_status["running"]:
                    break
                time.sleep(0.1)
        except Exception as e:
            log_message(f"[{bot_name}] ⚠️ Eroare la actualizarea grupului '{target_name}': {str(e)}")
            time.sleep(5)


def spam_worker(client, thread_id, target_name, messages_list, bot_name, delay_seconds):
    """Worker optimizat pentru grupuri cu pauză configurabilă (1 - 120s)"""
    msg_idx = 0
    sent_count = 0
    while bot_status["running"]:
        try:
            msg = messages_list[msg_idx % len(messages_list)]
            msg_idx += 1
            client.direct_send(text=msg, thread_ids=[str(thread_id)])
            sent_count += 1
            log_message(f"[{bot_name}] 🚀 Trimis pe grupul '{target_name}' (Total: {sent_count})")

            current_delay = max(1, min(120, int(bot_status.get("delay", delay_seconds))))
            for _ in range(current_delay * 10):
                if not bot_status["running"]:
                    break
                time.sleep(0.1)
        except Exception as e:
            log_message(f"[{bot_name}] ⚠️ Eroare pe grupul '{target_name}': {str(e)}")
            time.sleep(5)


def run_instagram_suite(session_id, group_targets, messages_list, bot_name, proxy_raw, delay_seconds):
    """Pornește simultan worker-ele de mesaje și protecția de nume/poză grup pentru un cont"""
    client = create_authed_client(session_id, proxy_raw, bot_name)
    if not client:
        return

    resolved_threads = resolve_group_threads(client, group_targets, bot_name)
    if not resolved_threads:
        log_message(f"[{bot_name}] ❌ Niciun grup valid găsit. Opresc agentul.")
        return

    has_messages = bool(messages_list)
    has_group_meta = bool(
        (bot_status.get("locked_group_name") or "").strip()
        or (
            bot_status.get("locked_group_photo_path")
            and os.path.exists(bot_status.get("locked_group_photo_path"))
        )
    )

    if not has_messages and not has_group_meta:
        log_message(f"[{bot_name}] ⚠️ Nu ai setat mesaje, nume de grup sau poză de grup.")
        return

    for target_name, thread_id in resolved_threads.items():
        if has_messages:
            t_msg = threading.Thread(
                target=spam_worker,
                args=(client, thread_id, target_name, messages_list, bot_name, delay_seconds),
            )
            t_msg.daemon = True
            t_msg.start()

        if has_group_meta:
            t_meta = threading.Thread(
                target=group_meta_worker,
                args=(client, thread_id, target_name, bot_name),
            )
            t_meta.daemon = True
            t_meta.start()

    log_message(
        f"[{bot_name}] 🔥 Activ (Msg: {has_messages}, {delay_seconds}s | Grup Meta: {has_group_meta}, {bot_status.get('group_meta_delay', 5)}s)."
    )

    while bot_status["running"]:
        time.sleep(0.5)


def clamp_seconds(raw_val, default_val):
    try:
        return max(1, min(120, int((raw_val or "").strip())))
    except ValueError:
        return default_val


def save_uploaded_group_photo(file_storage):
    if not file_storage or not file_storage.filename:
        return None, None
    raw_tmp = os.path.join(tempfile.gettempdir(), "kise_group_photo_raw")
    jpg_tmp = os.path.join(tempfile.gettempdir(), "kise_group_photo.jpg")
    file_storage.save(raw_tmp)

    if Image is not None:
        try:
            with Image.open(raw_tmp) as im:
                rgb_im = im.convert("RGB")
                rgb_im.save(jpg_tmp, format="JPEG", quality=92)
            return jpg_tmp, file_storage.filename
        except Exception as e:
            log_message(f"⚠️ Conversie JPG eșuată, folosesc fișierul direct: {str(e)}")

    return raw_tmp, file_storage.filename


@app.route("/", methods=["GET", "POST"])
def index():
    global bot_status
    delay_val = bot_status.get("delay", 50)
    meta_delay_val = bot_status.get("group_meta_delay", 5)
    locked_name_val = bot_status.get("locked_group_name", "")

    if request.method == "POST":
        action = request.form.get("action")
        delay_val = clamp_seconds(request.form.get("delay_seconds"), delay_val)
        meta_delay_val = clamp_seconds(request.form.get("group_meta_delay"), meta_delay_val)
        locked_name_val = (request.form.get("locked_group_name") or "").strip()

        bot_status["delay"] = delay_val
        bot_status["group_meta_delay"] = meta_delay_val
        if locked_name_val:
            bot_status["locked_group_name"] = locked_name_val

        uploaded_photo = request.files.get("group_photo")
        saved_photo_path, uploaded_filename = save_uploaded_group_photo(uploaded_photo)
        if saved_photo_path:
            bot_status["locked_group_photo_path"] = saved_photo_path
            bot_status["locked_group_photo_name"] = uploaded_filename or "group_photo.jpg"
            log_message(f"🖼️ Poză grup încărcată: '{bot_status['locked_group_photo_name']}' -> {saved_photo_path}")

        sessions_raw = request.form.get("sessions", "")
        groups_raw = request.form.get("groups", "")
        messages_raw = request.form.get("messages", "")
        proxy_raw = (request.form.get("proxy") or "").strip()

        sessions = [s.strip() for s in sessions_raw.split(",") if s.strip()]
        groups = [g.strip() for g in groups_raw.replace("\r", "").split("\n") if g.strip()]
        messages = [m.strip() for m in messages_raw.replace("\r", "").split("\n") if m.strip()]

        has_photo = bool(
            bot_status.get("locked_group_photo_path")
            and os.path.exists(bot_status.get("locked_group_photo_path"))
        )

        if action == "start" and not bot_status["running"]:
            if sessions and groups and (messages or locked_name_val or has_photo):
                bot_status["running"] = True
                log_message(
                    f"🚀 Sistem complet pornit pe {len(sessions)} conturi (Msg: {delay_val}s | Grup: {meta_delay_val}s)."
                )

                for idx, session in enumerate(sessions, start=1):
                    bot_name = f"Agent #{idx}"
                    t = threading.Thread(
                        target=run_instagram_suite,
                        args=(session, groups, messages, bot_name, proxy_raw, delay_val),
                    )
                    t.daemon = True
                    t.start()

        elif action == "stop":
            bot_status["running"] = False
            log_message("⏹️ S-a ordonat oprirea completă a sistemului.")

    return render_template_string(
        HTML_TEMPLATE,
        running=bot_status["running"],
        delay=delay_val,
        group_meta_delay=meta_delay_val,
        locked_group_name=bot_status.get("locked_group_name", ""),
        locked_group_photo_name=bot_status.get("locked_group_photo_name", ""),
        bg_image=BG_IMAGE_DATA_URI,
    )


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🪽Kise Cagulă - Control Panel</title>
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
                linear-gradient(to bottom, rgba(5, 2, 3, 0.42), rgba(5, 2, 3, 0.72)),
                {% if bg_image %}
                url('{{ bg_image }}');
                {% else %}
                radial-gradient(circle at 50% 0%, rgba(220, 38, 38, 0.35) 0%, rgba(5, 2, 3, 0.92) 75%);
                {% endif %}
            background-size: cover;
            background-position: center center;
            background-attachment: fixed;
        }

        .font-mono { font-family: 'JetBrains Mono', monospace; }
        .font-title { font-family: 'Cinzel', serif; }

        .glass-smoke {
            background: rgba(15, 7, 9, 0.56);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(220, 38, 38, 0.35);
            box-shadow: 0 0 40px rgba(220, 38, 38, 0.2), inset 0 0 15px rgba(220, 38, 38, 0.05);
        }

        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #050203; }
        ::-webkit-scrollbar-thumb { background: #3f111a; border-radius: 4px; }
    </style>
</head>
<body class="text-slate-100 min-h-screen py-10 px-4 sm:px-6 lg:px-8 flex flex-col justify-between selection:bg-blood selection:text-white">

    <div class="max-w-2xl mx-auto w-full space-y-6">
        <!-- Header -->
        <div class="flex items-center justify-between glass-smoke p-6 rounded-2xl shadow-2xl">
            <div class="flex items-center gap-3.5">
                <span class="p-3 bg-blood/20 text-bloodglow rounded-xl border border-blood/40 text-xl shadow-lg shadow-blood/30 animate-pulse">🪽</span>
                <div>
                    <h1 class="text-lg sm:text-xl font-black tracking-wider text-white font-title drop-shadow-[0_2px_10px_rgba(239,68,68,0.8)]">🪽Kise Cagulă</h1>
                    <p class="text-[11px] text-rose-400 font-mono tracking-widest uppercase">MSG {{ delay }}s // GROUP {{ group_meta_delay }}s</p>
                </div>
            </div>
            <div class="flex items-center gap-2 px-3.5 py-1.5 rounded-full border {% if running %}bg-blood/30 border-blood/60 text-rose-200 shadow-lg shadow-blood/40{% else %}bg-black/60 border-rose-950 text-slate-400{% endif %} text-xs font-medium">
                <span class="w-2 h-2 rounded-full {% if running %}bg-bloodglow animate-ping{% else %}bg-slate-600{% endif %}"></span>
                <span>{% if running %}ACTIV{% else %}STANDBY{% endif %}</span>
            </div>
        </div>

        <!-- Main Card -->
        <div class="glass-smoke p-6 sm:p-8 rounded-2xl shadow-2xl space-y-5">
            <form method="POST" enctype="multipart/form-data" class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-rose-300 mb-1.5">Session ID (Cookie)</label>
                    <textarea name="sessions" rows="2" placeholder="introdu sessionid-ul aici..." class="w-full bg-black/60 border border-rose-900/50 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blood focus:ring-1 focus:ring-blood transition shadow-inner font-mono"></textarea>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-rose-300 mb-1.5">Grupuri Țintă (câte unul pe rând)</label>
                        <textarea name="groups" rows="3" placeholder="Grup 1&#10;Grup 2" class="w-full bg-black/60 border border-rose-900/50 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blood focus:ring-1 focus:ring-blood transition shadow-inner"></textarea>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold uppercase tracking-wider text-rose-300 mb-1.5">Mesaje de Trimis</label>
                        <textarea name="messages" rows="3" placeholder="Mesaj 1&#10;Mesaj 2" class="w-full bg-black/60 border border-rose-900/50 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blood focus:ring-1 focus:ring-blood transition shadow-inner"></textarea>
                    </div>
                </div>

                <!-- Nume Grup + Poză Grup + Secunde Grup (implicit 5s, 1 - 120s) -->
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-end pt-1">
                    <div>
                        <label for="locked_group_name" class="block text-xs font-semibold uppercase tracking-wider text-rose-300 mb-1.5">Nume Grup Dorit</label>
                        <input id="locked_group_name" type="text" name="locked_group_name" value="{{ locked_group_name }}" placeholder="ex: 🪽Kise Cagulă" class="w-full bg-black/60 border border-rose-900/50 rounded-xl px-4 py-3 text-sm text-rose-100 placeholder-slate-500 focus:outline-none focus:border-blood transition shadow-inner">
                    </div>
                    <div>
                        <label for="group_photo" class="block text-xs font-semibold uppercase tracking-wider text-rose-300 mb-1.5">Poză Grup (Fișier)</label>
                        <input id="group_photo" type="file" name="group_photo" accept="image/*" class="w-full bg-black/60 border border-rose-900/50 rounded-xl px-3 py-2.5 text-xs text-rose-200 file:mr-2 file:py-1 file:px-2.5 file:rounded-lg file:border file:border-red-500/40 file:text-xs file:font-semibold file:bg-red-900/50 file:text-rose-100 hover:file:bg-red-800/60 focus:outline-none focus:border-blood transition shadow-inner cursor-pointer">
                        {% if locked_group_photo_name %}
                            <p class="text-[11px] text-rose-300/80 font-mono mt-1 truncate">Activă: {{ locked_group_photo_name }}</p>
                        {% endif %}
                    </div>
                    <div>
                        <label for="group_meta_delay" class="block text-xs font-semibold uppercase tracking-wider text-rose-300 mb-1.5">Secunde Grup (1 - 120)</label>
                        <input id="group_meta_delay" type="number" name="group_meta_delay" min="1" max="120" value="{{ group_meta_delay }}" class="w-full bg-black/60 border border-rose-900/50 rounded-xl px-4 py-3 text-sm font-mono text-rose-200 focus:outline-none focus:border-blood transition shadow-inner">
                    </div>
                </div>

                <div>
                    <input id="group_meta_slider" type="range" min="1" max="120" value="{{ group_meta_delay }}" class="w-full accent-red-600 cursor-pointer">
                </div>

                <!-- Proxy HTTP + Secunde Mesaje -->
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-end pt-2 border-t border-rose-950/60">
                    <div class="md:col-span-2">
                        <label class="block text-xs font-semibold uppercase tracking-wider text-rose-300 mb-1.5">Proxy HTTP</label>
                        <input type="text" name="proxy" value="38.154.185.97:6370:fvuubeod:0xk9re2xi909" class="w-full bg-black/60 border border-rose-900/50 rounded-xl px-4 py-3 text-sm font-mono text-rose-200 focus:outline-none focus:border-blood transition shadow-inner">
                    </div>
                    <div>
                        <label for="delay_seconds" class="block text-xs font-semibold uppercase tracking-wider text-rose-300 mb-1.5">Secunde Msg (1 - 120)</label>
                        <input id="delay_seconds" type="number" name="delay_seconds" min="1" max="120" value="{{ delay }}" class="w-full bg-black/60 border border-rose-900/50 rounded-xl px-4 py-3 text-sm font-mono text-rose-200 focus:outline-none focus:border-blood transition shadow-inner">
                    </div>
                </div>

                <div>
                    <input id="delay_slider" type="range" min="1" max="120" value="{{ delay }}" class="w-full accent-red-600 cursor-pointer">
                </div>

                <!-- Un singur buton pentru pornirea/oprirea tuturor funcțiilor -->
                <div class="pt-3">
                    {% if running %}
                        <button type="submit" name="action" value="stop" class="w-full py-4 px-4 bg-gradient-to-r from-red-800 to-rose-700 hover:from-red-700 hover:to-rose-600 text-white font-bold tracking-wider rounded-xl shadow-lg shadow-red-900/60 transition duration-200 flex items-center justify-center gap-2 cursor-pointer text-sm font-title border border-red-500/50">
                            <span>⏹ OPREȘTE SISTEMUL</span>
                        </button>
                    {% else %}
                        <button type="submit" name="action" value="start" class="w-full py-4 px-4 bg-gradient-to-r from-red-700 via-rose-600 to-blood hover:from-red-600 hover:to-rose-500 text-white font-bold tracking-wider rounded-xl shadow-xl shadow-blood/50 transition duration-200 flex items-center justify-center gap-2 cursor-pointer text-sm font-title border border-red-400/50">
                            <span>🔥 PORNEȘTE SISTEMUL</span>
                        </button>
                    {% endif %}
                </div>
            </form>
        </div>
    </div>

    <footer class="text-center text-xs text-rose-400/70 font-mono tracking-widest mt-8 drop-shadow">
        // 🪽Kise Cagulă &bull; GENERATION OF MIRACLES //
    </footer>

    <script>
        function syncPair(inputId, sliderId, fallbackVal) {
            const inp = document.getElementById(inputId);
            const sld = document.getElementById(sliderId);
            if (!inp || !sld) return;
            sld.addEventListener('input', () => {
                inp.value = sld.value;
            });
            inp.addEventListener('input', () => {
                let val = parseInt(inp.value || String(fallbackVal), 10);
                if (val < 1) val = 1;
                if (val > 120) val = 120;
                sld.value = val;
            });
        }

        syncPair('delay_seconds', 'delay_slider', 50);
        syncPair('group_meta_delay', 'group_meta_slider', 5);

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
