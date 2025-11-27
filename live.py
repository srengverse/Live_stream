import subprocess
import os
import time
import sys
import signal
import atexit
from dotenv import load_dotenv
import imageio_ffmpeg
from flask import Flask, jsonify, render_template_string
import threading
import psutil
from datetime import datetime
import shutil

# Load environment variables from .env file
load_dotenv()

# Configuration
VIDEO_FILE = os.environ.get("VIDEO_FILE", "video.mp4")
PLATFORM = os.environ.get("PLATFORM", "facebook").lower()
STREAM_KEY = os.environ.get("STREAM_KEY")
PORT = int(os.environ.get("PORT", 10000))

# Flask app
app = Flask(__name__)

class StreamManager:
    def __init__(self):
        self.process = None
        self.lock = threading.Lock()
        self.should_run = True
        self.status = {
            "status": "stopped",
            "start_time": None,
            "restart_count": 0,
            "last_error": None,
            "platform": PLATFORM,
            "video_file": VIDEO_FILE
        }
        
        # Register cleanup on exit
        atexit.register(self.cleanup)

    def update_status(self, **kwargs):
        with self.lock:
            self.status.update(kwargs)

    def get_status(self):
        with self.lock:
            # Calculate uptime
            uptime = None
            if self.status["start_time"]:
                try:
                    uptime = str(datetime.now() - self.status["start_time"]).split('.')[0]
                except Exception:
                    uptime = "Error calculating uptime"

            # System information
            system_info = {
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "timestamp": datetime.now().isoformat()
            }
            
            return {
                **self.status,
                "uptime": uptime,
                "system_info": system_info
            }

    def start_stream(self):
        """Function to start the streaming process"""
        
        # Main Loop for streaming
        while self.should_run:
            # Reload environment variables to pick up changes (e.g. new STREAM_KEY)
            load_dotenv(override=True)
            
            # Get configuration from environment
            video_file = os.environ.get("VIDEO_FILE", "video.mp4")
            platform = os.environ.get("PLATFORM", "facebook").lower()
            stream_key = os.environ.get("STREAM_KEY")
            
            # Update status with current config
            self.update_status(
                platform=platform,
                video_file=video_file
            )

            # Validation
            if not os.path.exists(video_file):
                error_msg = f"Video file '{video_file}' not found!"
                print(f"Error: {error_msg}")
                self.update_status(status="error", last_error=error_msg)
                time.sleep(5)
                continue

            if not stream_key:
                error_msg = "STREAM_KEY not found! Please check your .env file or environment variables."
                print(f"Error: {error_msg}")
                self.update_status(status="error", last_error=error_msg)
                time.sleep(5)
                continue

            # RTMP URL Selection
            if platform == "youtube":
                rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
            elif platform == "facebook":
                rtmp_url = f"rtmps://live-api-s.facebook.com:443/rtmp/{stream_key}"
            else:
                error_msg = f"Unsupported platform: {platform}. Use 'youtube' or 'facebook'."
                print(f"Error: {error_msg}")
                self.update_status(status="error", last_error=error_msg)
                time.sleep(5)
                continue

            print("Streaming Service Started 24/7")
            print(f"File: {video_file}")
            print(f"Platform: {'YouTube' if platform == 'youtube' else 'Facebook'}")

            # Get FFmpeg executable path
            if shutil.which("ffmpeg"):
                ffmpeg_exe = "ffmpeg"
            else:
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

            print(f"Using FFmpeg: {ffmpeg_exe}")

            # Command construction
            command = [
                ffmpeg_exe,
                "-re",                          # Read input at native frame rate
                "-stream_loop", "-1",           # Loop indefinitely
                "-i", video_file,               # Input file
                "-c:v", "libx264",              # Video codec
                "-preset", "fast",              # Encoding speed
                "-b:v", "2500k",                # Video bitrate
                "-maxrate", "2500k",            # Max bitrate
                "-bufsize", "5000k",            # Buffer size
                "-pix_fmt", "yuv420p",          # Pixel format
                "-g", "60",                     # Keyframe interval
                "-r", "30",                     # Output frame rate
                "-c:a", "aac",                  # Audio codec
                "-b:a", "160k",                 # Audio bitrate
                "-ar", "44100",                 # Audio sample rate
                "-ac", "2",                     # Stereo audio
                "-f", "flv",                    # Output format
                rtmp_url                        # Destination
            ]

            try:
                print("Starting stream...")
                self.update_status(
                    status="streaming",
                    start_time=datetime.now(),
                    last_error=None
                )
                
                self.process = subprocess.Popen(command)
                self.process.wait()
                
                # If process was terminated intentionally (e.g. restart), don't treat as error immediately
                if not self.should_run:
                    break

                if self.process.returncode == 0:
                    print("Stream process completed normally.")
                    self.update_status(status="stopped")
                elif self.process.returncode == -9 or self.process.returncode == -15: # SIGKILL or SIGTERM
                     print("Stream process terminated.")
                     # Status update handled by restart logic or loop
                else:
                    error_msg = f"Stream process exited with code: {self.process.returncode}"
                    print(error_msg)
                    self.update_status(status="error", last_error=error_msg)
                    
            except Exception as e:
                error_msg = f"An error occurred: {e}"
                print(error_msg)
                self.update_status(status="error", last_error=error_msg)
            
            if self.should_run:
                with self.lock:
                    self.status["restart_count"] += 1
                print("Restarting stream in 5 seconds...")
                time.sleep(5)

    def restart_stream(self):
        """Terminates the current process to trigger a restart loop"""
        if self.process and self.process.poll() is None:
            print("Terminating stream process for restart...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            
            self.update_status(last_error="Manual restart triggered")
            return True
        return False

    def cleanup(self):
        """Cleanup function to kill process on exit"""
        self.should_run = False
        if self.process and self.process.poll() is None:
            print("Cleaning up stream process...")
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()

# Initialize Stream Manager
stream_manager = StreamManager()

# HTML Template for Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live Stream Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // Update status badge
                    const statusBadge = document.getElementById('status-badge');
                    statusBadge.className = `px-3 py-1 rounded-full text-sm font-semibold ${
                        data.status === 'streaming' ? 'bg-green-100 text-green-800' : 
                        data.status === 'error' ? 'bg-red-100 text-red-800' : 
                        'bg-yellow-100 text-yellow-800'
                    }`;
                    statusBadge.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);
                    
                    // Update platform
                    document.getElementById('platform').textContent = data.platform;
                    
                    // Update video file
                    document.getElementById('video-file').textContent = data.video_file;
                    
                    // Update restart count
                    document.getElementById('restart-count').textContent = data.restart_count;
                    
                    // Update uptime
                    document.getElementById('uptime').textContent = data.uptime || 'N/A';
                    
                    // Update last error
                    const lastErrorEl = document.getElementById('last-error');
                    lastErrorEl.textContent = data.last_error || 'No errors';
                    lastErrorEl.className = data.last_error ? 'text-red-600' : 'text-gray-500';
                    
                    // Update system info
                    document.getElementById('cpu-usage').textContent = data.system_info.cpu_usage + '%';
                    document.getElementById('memory-usage').textContent = data.system_info.memory_usage + '%';
                    document.getElementById('timestamp').textContent = new Date(data.timestamp).toLocaleString();
                })
                .catch(error => {
                    console.error('Error fetching status:', error);
                });
        }
        
        function restartStream() {
            if (!confirm('Are you sure you want to restart the stream?')) return;
            
            fetch('/api/restart', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    updateStatus();
                });
        }
        
        // Update status every 5 seconds
        setInterval(updateStatus, 5000);
        document.addEventListener('DOMContentLoaded', updateStatus);
    </script>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <div class="text-center mb-8">
            <h1 class="text-4xl font-bold text-gray-800 mb-2">
                <i class="fas fa-broadcast-tower text-blue-500 mr-3"></i>
                Live Stream Dashboard
            </h1>
            <p class="text-gray-600">Monitor and manage your 24/7 live stream</p>
        </div>

        <!-- Main Dashboard -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <!-- Stream Status Card -->
            <div class="bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold text-gray-800 mb-4">
                    <i class="fas fa-info-circle text-blue-500 mr-2"></i>
                    Stream Information
                </h2>
                <div class="space-y-3">
                    <div class="flex justify-between">
                        <span class="text-gray-600">Status:</span>
                        <span id="status-badge" class="px-3 py-1 rounded-full text-sm font-semibold bg-yellow-100 text-yellow-800">
                            Loading...
                        </span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-600">Platform:</span>
                        <span id="platform" class="font-medium">Loading...</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-600">Video File:</span>
                        <span id="video-file" class="font-medium">Loading...</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-600">Restart Count:</span>
                        <span id="restart-count" class="font-medium">0</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-600">Uptime:</span>
                        <span id="uptime" class="font-medium">Loading...</span>
                    </div>
                </div>
            </div>

            <!-- System Info Card -->
            <div class="bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold text-gray-800 mb-4">
                    <i class="fas fa-server text-green-500 mr-2"></i>
                    System Information
                </h2>
                <div class="space-y-3">
                    <div class="flex justify-between">
                        <span class="text-gray-600">CPU Usage:</span>
                        <span id="cpu-usage" class="font-medium">Loading...</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-600">Memory Usage:</span>
                        <span id="memory-usage" class="font-medium">Loading...</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-600">Last Updated:</span>
                        <span id="timestamp" class="font-medium text-sm">Loading...</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Error Display -->
        <div class="bg-white rounded-lg shadow-md p-6 mb-8">
            <h2 class="text-xl font-semibold text-gray-800 mb-4">
                <i class="fas fa-exclamation-triangle text-orange-500 mr-2"></i>
                Last Error
            </h2>
            <div class="bg-gray-50 rounded-lg p-4">
                <p id="last-error" class="text-gray-500">No errors</p>
            </div>
        </div>

        <!-- Actions -->
        <div class="bg-white rounded-lg shadow-md p-6">
            <h2 class="text-xl font-semibold text-gray-800 mb-4">
                <i class="fas fa-cogs text-purple-500 mr-2"></i>
                Actions
            </h2>
            <div class="flex space-x-4">
                <button onclick="restartStream()" 
                        class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg transition duration-200">
                    <i class="fas fa-redo mr-2"></i>
                    Restart Stream
                </button>
                <button onclick="updateStatus()" 
                        class="bg-gray-500 hover:bg-gray-600 text-white px-6 py-2 rounded-lg transition duration-200">
                    <i class="fas fa-sync mr-2"></i>
                    Refresh Status
                </button>
            </div>
        </div>

        <!-- Footer -->
        <div class="text-center mt-8 text-gray-500">
            <p>Live Stream Dashboard • Auto-restart every 5 seconds on errors</p>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/status')
def api_status():
    return jsonify(stream_manager.get_status())

@app.route('/api/restart', methods=['POST'])
def api_restart():
    success = stream_manager.restart_stream()
    if success:
        return jsonify({"message": "Restart command sent. Stream restarting...", "status": "restarting"})
    else:
        return jsonify({"message": "Stream is not running or could not be restarted.", "status": "error"}), 400

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "live-stream-dashboard"})

if __name__ == "__main__":
    # Start streaming in a separate thread
    stream_thread = threading.Thread(target=stream_manager.start_stream, daemon=True)
    stream_thread.start()
    
    # Start Flask app (this binds to the port)
    print(f"Starting web service on port {PORT}")
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False)
    except KeyboardInterrupt:
        stream_manager.cleanup()