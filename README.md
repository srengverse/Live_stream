# 24/7 Live Stream to Facebook

A lightweight Python app that loops a video file and streams it 24/7 to Facebook (or YouTube) via FFmpeg, with a live status dashboard.

## How to run

The app starts automatically via the **Start application** workflow (`python live.py`).  
Open the preview pane to see the live dashboard.

## Environment variables / secrets

| Key | Where | Notes |
|-----|-------|-------|
| `STREAM_KEY` | Secret | Facebook/YouTube persistent stream key (required) |
| `PLATFORM` | Shared env | `facebook` or `youtube` (default: `facebook`) |
| `VIDEO_FILE` | Shared env | Video file to stream (default: `video_optimized.mp4`) |
| `PORT` | Shared env | Web server port — set to `5000` for Replit preview |

## Stack

- **Backend**: Python 3, Flask
- **Streaming**: FFmpeg (copy mode — near-zero CPU)
- **Frontend**: HTML + TailwindCSS (served by Flask)

## Notes

- `video_optimized.mp4` is already included (720×1280, h264/aac, copy-mode ready)
- FFmpeg streams in copy mode (`-c:v copy -c:a copy`) — no transcoding
- The video loops infinitely with `-stream_loop -1`
- To switch to YouTube: change the `PLATFORM` env var to `youtube`
