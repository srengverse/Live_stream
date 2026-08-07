import subprocess
import os
import time
import re
import threading
import psutil
import logging
import signal
import shutil
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template
import imageio_ffmpeg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

load_dotenv()

# Configuration from environment variables
VIDEO_FILE = os.environ.get("VIDEO_FILE", "video_optimized.mp4")
PLATFORM = os.environ.get("PLATFORM", "facebook").lower()
STREAM_KEY = os.environ.get("STREAM_KEY")
RTMP_URL = os.environ.get("RTMP_URL")  # Custom RTMP URL if provided
PORT = int(os.environ.get("PORT", 10000))
FFMPEG_PRESET = os.environ.get("FFMPEG_PRESET", "ultrafast")
SCALING_ALGO = os.environ.get("SCALING_ALGO", "bilinear")
FORCE_TRANSCODE = os.environ.get("FORCE_TRANSCODE", "false").lower() == "true"

stream_status = {
    "status": "starting",
    "start_time": None,
    "restart_count": 0,
    "last_error": None,
    "platform": PLATFORM,
    "video_file": VIDEO_FILE,
    "fps": 0.0,
    "speed": "0.0x",
    "bitrate": "0 kb/s",
    "uptime": "00:00:00"
}

app = Flask(__name__)
ffmpeg_process = None

def get_rtmp_url():
    if RTMP_URL:
        return RTMP_URL
    
    if PLATFORM == "youtube":
        return f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
    else:
        # Default to Facebook
        return f"rtmps://live-api-s.facebook.com:443/rtmp/{STREAM_KEY}"

def get_ffmpeg_command():
    rtmp_url = get_rtmp_url()
    
    ffmpeg_exe = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()

    cmd = [
        ffmpeg_exe,
        "-re",
        "-stream_loop", "-1",
        "-i", VIDEO_FILE
    ]

    if FORCE_TRANSCODE:
        # Transcode to standard RTMP settings if forced
        cmd += [
            "-c:v", "libx264",
            "-preset", FFMPEG_PRESET,
            "-b:v", "2500k",
            "-maxrate", "2500k",
            "-bufsize", "5000k",
            "-pix_fmt", "yuv420p",
            "-g", "60",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100"
        ]
    else:
        # Stream copy (efficient)
        cmd += [
            "-c:v", "copy",
            "-c:a", "copy",
            "-bsf:a", "aac_adtstoasc"
        ]

    cmd += [
        "-f", "flv",
        "-tls_verify", "0",
        "-rtmp_live", "live",
        rtmp_url
    ]
    
    return cmd

def parse_stats(line):
    try:
        if "speed=" in line:
            fps_match = re.search(r"fps=\s*([\d.]+)", line)
            if fps_match:
                stream_status["fps"] = round(float(fps_match.group(1)), 1)
            
            br_match = re.search(r"bitrate=\s*([\d.kbits/sN/A]+)", line)
            if br_match:
                br_val = br_match.group(1)
                if "kbits/s" in br_val:
                    stream_status["bitrate"] = br_val.replace("kbits/s", " kb/s")
                else:
                    stream_status["bitrate"] = br_val
            
            spd_match = re.search(r"speed=\s*([\d.]+)x", line)
            if spd_match:
                stream_status["speed"] = spd_match.group(1) + "x"
    except Exception as e:
        logger.debug(f"Error parsing stats: {e}")

@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    uptime = "00:00:00"
    if stream_status["start_time"]:
        delta = datetime.now() - stream_status["start_time"]
        uptime = str(delta).split('.')[0]
    
    return jsonify({
        **stream_status,
        "uptime": uptime,
        "cpu": round(psutil.cpu_percent(), 1),
        "ram": round(psutil.virtual_memory().percent, 1),
        "restarts": stream_status["restart_count"],
        "preset": FFMPEG_PRESET,
        "scaling_algo": SCALING_ALGO
    })

def streaming_loop():
    global ffmpeg_process
    
    if not os.path.exists(VIDEO_FILE):
        error_msg = f"Video file not found: {VIDEO_FILE}"
        stream_status.update({"status": "error", "last_error": error_msg})
        logger.error(error_msg)
        return

    if not STREAM_KEY and not RTMP_URL:
        error_msg = "Missing STREAM_KEY or RTMP_URL"
        stream_status.update({"status": "error", "last_error": error_msg})
        logger.error(error_msg)
        return

    logger.info(f"Starting stream loop for platform: {PLATFORM}")
    
    while True:
        cmd = get_ffmpeg_command()
        logger.info(f"Executing FFmpeg command: {' '.join(cmd)}")
        
        try:
            stream_status.update({
                "status": "streaming",
                "start_time": datetime.now(),
                "last_error": None
            })
            
            ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Efficiently read stderr line by line
            for line in iter(ffmpeg_process.stderr.readline, ''):
                if line:
                    parse_stats(line.strip())
                    # Log non-stat lines that might be errors
                    if "frame=" not in line and "speed=" not in line:
                        logger.info(f"FFmpeg: {line.strip()}")

            ffmpeg_process.wait()
            
            if ffmpeg_process.returncode != 0:
                error_msg = f"FFmpeg exited with code {ffmpeg_process.returncode}"
                stream_status["status"] = "error"
                stream_status["last_error"] = error_msg
                logger.error(error_msg)
            
        except Exception as e:
            stream_status.update({"status": "error", "last_error": str(e)})
            logger.exception("Exception in streaming loop")

        stream_status["restart_count"] += 1
        logger.info(f"Restarting in 5s... (Count: {stream_status['restart_count']})")
        time.sleep(5)

def signal_handler(sig, frame):
    logger.info("Shutdown signal received. Cleaning up...")
    if ffmpeg_process:
        ffmpeg_process.terminate()
    os._exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start streaming thread
    threading.Thread(target=streaming_loop, daemon=True).start()
    
    logger.info(f"Dashboard running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
