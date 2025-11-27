import subprocess
import os
import time
import sys
import re
import threading
import psutil
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string

# Load env
load_dotenv()

# Config
VIDEO_FILE = os.environ.get("VIDEO_FILE", "video.mp4")
PLATFORM = os.environ.get("PLATFORM", "facebook").lower()
STREAM_KEY = os.environ.get("STREAM_KEY")
PORT = int(os.environ.get("PORT", 10000))

# Global status
stream_status = {
    "status": "stopped",
    "start_time": None,
    "restart_count": 0,
    "last_error": None,
    "platform": PLATFORM,
    "video_file": VIDEO_FILE,
    "fps": 0.0,
    "bitrate": "0 kb/s",
    "speed": "0.0x",
    "uptime": "00:00:00"
}

app = Flask(__name__)

# === OPTIMIZED FFMPEG COMMAND (BEST FOR RENDER.COM 2025) ===
def get_ffmpeg_command():
    rtmp_url = f"rtmps://live-api-s.facebook.com:443/rtmp/{STREAM_KEY}" if PLATFORM != "youtube" else f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"

    # Use static ffmpeg from imageio_ffmpeg (works perfectly on Render)
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    cmd = [
        ffmpeg_exe,
        "-re", "-stream_loop", "-1", "-i", VIDEO_FILE,

        # VIDEO – ULTRA FAST & STABLE
        "-c:v", "libx264",
        "-preset", "superfast",      # superfast = best balance (ultrafast sometimes drops frames)
        "-tune", "zerolatency",
        "-b:v", "2200k",
        "-maxrate", "2200k",
        "-bufsize", "4400k",
        "-r", "30",
        "-g", "60",
        "-keyint_min", "30",
        "-sc_threshold", "0",
        "-pix_fmt", "yuv420p",

        # AUDIO
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-ac", "2",

        # OUTPUT
        "-f", "flv",
        "-threads", "4",             # Render free tier loves this
        rtmp_url
    ]
    return ffmpeg_exe, cmd

# === REAL-TIME FFMPEG LOG PARSER ===
def parse_ffmpeg_output(line):
    global stream_status
    # frame= 1234 fps= 25 q=23.0 size= 12345kB time=00:01:23.45 bitrate=2500.0kbits/s speed=1.0x
    match = re.search(r"frame=\s*(\d+)\sfps=\s*([\d.]+)\s.*time=(\d+:\d+:\d+\.\d+).*bitrate=\s*([\d.]+)kbits/s.*speed=\s*([\d.]+)x", line)
    if match:
        stream_status["fps"] = round(float(match.group(2)), 1)
        stream_status["bitrate"] = f"{match.group(4)} kb/s"
        stream_status["speed"] = match.group(5) + "x"
        # Clean uptime
        uptime_raw = match.group(3).split('.')[0]
        stream_status["uptime"] = uptime_raw if len(uptime_raw) == 8 else f"00:{uptime_raw}"

# === DASHBOARD 2026 STYLE (Auto-refresh every 3s) ===
@app.route('/')
def dashboard():
    return render_template_string('''
<!DOCTYPE html>
<html class="h-full">
<head>
    <title>Live Stream Dashboard 2026</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
</head>
<body class="h-full bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white">
    <div class="min-h-screen p-6">
        <div class="max-w-5xl mx-auto">
            <h1 class="text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-purple-600 mb-2">
                <i data-lucide="radio" class="inline w-12 h-12"></i> Live Stream Dashboard
            </h1>
            <p class="text-xl text-cyan-300 mb-8">Ultra-optimized • Real-time Stats • Zero Lag</p>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8" id="stats"></div>

            <div class="bg-white/10 backdrop-blur-xl rounded-2xl p-8 border border-white/20">
                <h2 class="text-2xl font-bold mb-6 flex items-center gap-3">
                    <i data-lucide="activity" class="w-8 h-8 text-emerald-400"></i>
                    Real-time FFmpeg Output
                </h2>
                <pre id="log" class="bg-black/50 rounded-lg p-4 h-96 overflow-y-auto font-mono text-sm text-green-400"></pre>
            </div>
        </div>
    </div>

    <script>
        lucide.createIcons();
        const logEl = document.getElementById('log');
        const statsEl = document.getElementById('stats');

        function update() {
            fetch('/api/status')
                .then(r => r.json())
                .then(d => {
                    statsEl.innerHTML = `
                        <div class="bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/20">
                            <div class="text-4xl font-bold text-emerald-400">${d.status.toUpperCase()}</div>
                            <div class="text-sm text-gray-400">Status</div>
                        </div>
                        <div class="bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/20">
                            <div class="text-4xl font-bold text-cyan-400">${d.uptime}</div>
                            <div class="text-sm text-gray-400">Uptime</div>
                        </div>
                        <div class="bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/20">
                            <div class="text-4xl font-bold text-purple-400">${d.fps} fps</div>
                            <div class="text-sm text-gray-400">Encoding Speed • ${d.speed}</div>
                        </div>
                    `;
                    document.title = `${d.status === 'streaming' ? '● LIVE' : '○ OFF'} ${d.fps}fps • ${d.uptime}`;
                });
        }

        setInterval(() => {
            fetch('/api/status').then(r => r.text()).then(t => {
                const lines = t.split('\\n').slice(-20);
                logEl.textContent = lines.join('\\n');
                logEl.scrollTop = logEl.scrollHeight;
            });
            update();
        }, 3000);
        update();
    </script>
</body>
</html>
    ''')

@app.route('/api/status')
def api_status():
    uptime = "00:00:00"
    if stream_status["start_time"]:
        delta = datetime.now() - stream_status["start_time"]
        uptime = str(delta).split('.')[0]

    return jsonify({
        **stream_status,
        "uptime": uptime,
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "restart_count": stream_status["restart_count"],
        "platform_url": "https://www.facebook.com/live/producer" if PLATFORM != "youtube" else "https://studio.youtube.com/live"
    })

# === MAIN STREAMING LOOP (BEST VERSION) ===
def start_stream():
    if not os.path.exists(VIDEO_FILE):
        stream_status.update({"status": "error", "last_error": f"File not found: {VIDEO_FILE}"})
        return
    if not STREAM_KEY:
        stream_status.update({"status": "error", "last_error": "STREAM_KEY missing in .env"})
        return

    print("Starting ULTRA-OPTIMIZED stream...")
    ffmpeg_exe, cmd = get_ffmpeg_command()
    print(f"Platform: {PLATFORM.upper()} | File: {VIDEO_FILE}")

    while True:
        try:
            stream_status.update({
                "status": "streaming",
                "start_time": datetime.now(),
                "last_error": None
            })

            proc = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )

            for line in proc.stderr:
                line = line.strip()
                if line:
                    parse_ffmpeg_output(line)
                    if "error" in line.lower() or "failed" in line.lower():
                        print("FFmpeg ERROR:", line)

            proc.wait()
            if proc.returncode != 0:
                stream_status["last_error"] = f"FFmpeg exited ({proc.returncode})"
                stream_status["status"] = "error"

        except Exception as e:
            stream_status.update({"status": "error", "last_error": str(e)})

        stream_status["restart_count"] += 1
        print(f"Restarting in 5s... (Attempt #{stream_status['restart_count']})")
        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=start_stream, daemon=True).start()
    print(f"Dashboard: http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)