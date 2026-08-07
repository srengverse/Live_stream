# 🚀 Advanced 24/7 Live Streamer

A robust, optimized Python-based tool for continuous live streaming to Facebook, YouTube, or any custom RTMP target. Designed for stability and performance.

## ✨ Features

- **24/7 Continuous Streaming**: Automatic loop and restart on failure.
- **Multi-Platform Support**: Built-in presets for Facebook and YouTube, plus custom RTMP support.
- **Optimized Performance**: Uses stream copy by default for zero CPU overhead, with optional transcoding.
- **Real-time Dashboard**: Web-based monitor for bitrate, FPS, speed, and system resources.
- **Docker Ready**: Easy deployment using Docker and Docker Compose.
- **Improved Logging**: Structured logging for easier troubleshooting.

## 🛠️ Installation

### Using Docker (Recommended)

1. Clone the repository:
   \`\`\`bash
   git clone https://github.com/srengverse/Live_stream.git
   cd Live_stream
   \`\`\`

2. Create a \`.env\` file from the example:
   \`\`\`bash
   cp .env.example .env
   \`\`\`
   Edit \`.env\` and add your \`STREAM_KEY\`.

3. Start the stream:
   \`\`\`bash
   docker-compose up -d
   \`\`\`

### Manual Installation

1. Install dependencies:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

2. Install FFmpeg on your system.

3. Run the application:
   \`\`\`bash
   python live.py
   \`\`\`

## ⚙️ Configuration (.env)

| Variable | Description | Default |
| :--- | :--- | :--- |
| \`PLATFORM\` | \`facebook\` or \`youtube\` | \`facebook\` |
| \`STREAM_KEY\` | Your live stream key | - |
| \`RTMP_URL\` | Custom RTMP destination | - |
| \`VIDEO_FILE\` | Path to your video file | \`video_optimized.mp4\` |
| \`FORCE_TRANSCODE\` | Force re-encoding (true/false) | \`false\` |
| \`FFMPEG_PRESET\` | FFmpeg encoding preset | \`ultrafast\` |
| \`PORT\` | Dashboard port | \`10000\` |

## 📊 Dashboard

Access the monitor at \`http://localhost:10000\`. It provides real-time stats:
- **Status**: Current stream state.
- **Uptime**: How long the current stream has been running.
- **Bitrate/FPS**: Real-time encoding stats.
- **System**: CPU and RAM usage.

## 📝 License

MIT License. Feel free to use and modify!
