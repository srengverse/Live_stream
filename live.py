import subprocess
import os
import time
import sys
from dotenv import load_dotenv
import imageio_ffmpeg

# Load environment variables from .env file
load_dotenv()

# Configuration
VIDEO_FILE = os.environ.get("VIDEO_FILE", "video.mp4")
PLATFORM = os.environ.get("PLATFORM", "facebook").lower()
STREAM_KEY = os.environ.get("STREAM_KEY")

# Validation
if not os.path.exists(VIDEO_FILE):
    print(f"Error: Video file '{VIDEO_FILE}' not found!")
    sys.exit(1)

if not STREAM_KEY:
    print("Error: STREAM_KEY not found! Please check your .env file or environment variables.")
    sys.exit(1)

# RTMP URL Selection
if PLATFORM == "youtube":
    RTMP_URL = f"rtmp://a.rtmp.youtube.com/live2/{STREAM_KEY}"
else:  # facebook
    RTMP_URL = f"rtmps://live-api-s.facebook.com:443/rtmp/{STREAM_KEY}"

print("Streaming Service Started 24/7")
print(f"File: {VIDEO_FILE}")
print(f"Platform: {'YouTube' if PLATFORM == 'youtube' else 'Facebook'}")

# Get FFmpeg executable path
# Try to use system ffmpeg first, as the bundled one might crash
import shutil
if shutil.which("ffmpeg"):
    FFMPEG_EXE = "ffmpeg"
else:
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

print(f"Using FFmpeg: {FFMPEG_EXE}")

# Command construction
command = [
    FFMPEG_EXE,
    "-re",                          # Read input at native frame rate
    "-stream_loop", "-1",           # Loop indefinitely
    "-i", VIDEO_FILE,               # Input file
    "-c:v", "libx264",              # Video codec
    "-preset", "fast",              # Encoding speed
    "-b:v", "2500k",                # Video bitrate
    "-maxrate", "2500k",            # Max bitrate
    "-bufsize", "5000k",            # Buffer size
    "-vf", "format=yuv420p",        # Pixel format
    "-g", "60",                     # Keyframe interval (every 2s for 30fps)
    "-c:a", "aac",                  # Audio codec
    "-b:a", "160k",                 # Audio bitrate
    "-ar", "44100",                 # Audio sample rate
    "-f", "flv",                    # Output format
    RTMP_URL                        # Destination
]

# Main Loop
while True:
    try:
        print("Starting stream...")
        subprocess.run(command)
        print("Stream process exited.")
    except KeyboardInterrupt:
        print("\nStream stopped by user.")
        break
    except Exception as e:
        print(f"An error occurred: {e}")
    
    print("Restarting stream in 5 seconds...")
    time.sleep(5)