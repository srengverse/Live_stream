# 24/7 Live Stream to Facebook

A lightweight Python application for continuous 24/7 live streaming to Facebook, optimized for **Render Free Tier** (0.1 vCPU).

## Features

- 🎥 **Optimized Streaming**: Pre-rendered video with `ffmpeg copy mode` for minimal CPU usage
- 📱 **Vertical Format**: 720x1280 (9:16 aspect ratio) perfect for mobile viewing
- 🔄 **Infinite Loop**: Automatically restarts video playback for 24/7 streaming
- 📊 **Real-time Dashboard**: Web interface with live statistics (FPS, bitrate, uptime, CPU/RAM usage)
- ☁️ **Cloud Ready**: Designed to run on Render Free Tier with minimal resource consumption
- 🔐 **Secure**: Sensitive credentials stored in environment variables

## Quick Start

### Local Testing

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Srengnx007/Live_stream.git
   cd Live_stream
   ```

2. **Set up Python environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   - Copy `.env.example` to `.env` (or create `.env`):
   ```bash
   PLATFORM=facebook
   STREAM_KEY=your-facebook-stream-key-here
   VIDEO_FILE=video_optimized.mp4
   ```

4. **Run the application**:
   ```bash
   python live.py
   ```

5. **Access dashboard**: Open `http://localhost:10000` in your browser

## Deployment to Render

### Prerequisites
- GitHub account
- [Render account](https://render.com) (free)
- Facebook Live Stream Key

### Steps

1. **Fork or clone this repository to your GitHub account**

2. **Create a new Web Service on Render**:
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click **New** → **Blueprint**
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml`

3. **Set Environment Variables** in Render:
   - `STREAM_KEY`: Your Facebook persistent stream key
   - `PLATFORM`: `facebook` (default)
   - `VIDEO_FILE`: `video_optimized.mp4` (default)

4. **Deploy**: Render will automatically build and deploy your app

5. **Prevent Sleep** (Important for Free Tier):
   - Get your Render app URL (e.g., `https://your-app.onrender.com`)
   - Sign up at [UptimeRobot](https://uptimerobot.com) (free)
   - Create a new HTTP(s) monitor with your Render URL
   - Set interval to **5 minutes**
   - This prevents Render from spinning down after 15 minutes of inactivity

## How It Works

### Optimization for Free Tier

The key to running on Render's 0.1 vCPU is using **copy mode streaming**:

- **Pre-rendered Video**: `video_optimized.mp4` is already in the target format (720x1280)
- **No Transcoding**: FFmpeg uses `-c:v copy -c:a copy` to stream without re-encoding
- **CPU Usage**: Near 0% since no computational work is done
- **Memory**: < 100MB typical usage

### Architecture

```
┌─────────────────┐
│  video_optimized│
│      .mp4       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     FFmpeg      │
│  (copy mode)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RTMPS Stream   │
│   to Facebook   │
└─────────────────┘

┌─────────────────┐
│  Flask Server   │
│   Dashboard     │
│  localhost:10000│
└─────────────────┘
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PLATFORM` | Streaming platform (`facebook` or `youtube`) | `facebook` |
| `STREAM_KEY` | Your platform's stream key | *Required* |
| `VIDEO_FILE` | Video file to stream | `video_optimized.mp4` |
| `PORT` | Web server port | `10000` |
| `FFMPEG_PRESET` | FFmpeg preset (unused in copy mode) | `ultrafast` |
| `SCALING_ALGO` | Scaling algorithm (unused in copy mode) | `bilinear` |

## Getting a Facebook Stream Key

1. Go to [Facebook Live Producer](https://www.facebook.com/live/producer/)
2. Click **"Go Live"**
3. Under **"Streaming Software Setup"**, enable **"Persistent Stream Key"**
4. Copy the stream key shown

## Dashboard Features

The web dashboard (`http://localhost:10000`) displays:

- ✅ Stream Status (streaming/error/starting)
- ⏱️ Uptime
- 🎬 FPS and Speed
- 📊 Bitrate
- 💻 CPU and RAM usage
- 🔄 Restart count

## Troubleshooting

### Stream not connecting
- Verify your `STREAM_KEY` is correct
- Check if your Facebook account is verified for live streaming
- Ensure the stream key is a **persistent key**, not a single-use key

### High CPU usage
- Make sure you're using `video_optimized.mp4` (not `video.mp4`)
- Verify FFmpeg is using copy mode (check logs for `Stream mapping: copy`)

### Render app sleeping
- Add an UptimeRobot monitor pinging every 5 minutes
- Free tier spins down after 15 min of inactivity

## Tech Stack

- **Backend**: Python 3.11+, Flask
- **Streaming**: FFmpeg
- **Frontend**: HTML, TailwindCSS, JavaScript
- **Deployment**: Render, Gunicorn
- **Monitoring**: psutil

## License

MIT License - feel free to use and modify

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues or questions, please [open an issue](https://github.com/Srengnx007/Live_stream/issues) on GitHub.
