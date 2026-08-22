# HEVC Player

A free, standalone HEVC/H.265 video player for Windows. No paid codecs, no Microsoft Store tax — it ships with its own FFmpeg-based decoder.

![platform](https://img.shields.io/badge/platform-Windows-blue) ![license](https://img.shields.io/badge/license-MIT-green)

## Download & run

1. Go to [Releases](../../releases) and download **`HEVCPlayer.exe`**
2. Double-click it

That's it. It's fully portable — a brand new Windows 10/11 PC needs **nothing installed**: no Python, no codecs, no installer.

## Features

- Plays HEVC/H.265 (plus H.264, AV1, VP9, AAC, MP3, FLAC, etc.) via bundled FFmpeg
- Standalone single-file `.exe` (~56 MB)
- Dark themed UI with gradient seek bar, glow buttons, OSD feedback
- Auto-hiding controls in fullscreen
- Codec/resolution/fps badge overlay
- A/V sync driven by the audio clock
- Registerable as your system default player (see below)

## Set as default media player

1. Right-click any video → **Open with** → **Choose another app**
2. Pick **HEVC Player** and tick **Always**

Or: **Settings → Apps → Default apps → HEVC Player**, then set each format (`.mp4`, `.mkv`, `.mov`, `.ts`, `.hevc`, `.h265`, `.avi`, `.webm`, `.m4v`).

To register the app with Windows (one-time), add these registry keys, pointing at your exe path:

```
HKCU\Software\Classes\Applications\HEVCPlayer.exe\shell\open\command  ->  "<path>\HEVCPlayer.exe" "%1"
HKCU\Software\HEVCPlayer\Capabilities\FileAssociations\.mp4           ->  HEVCPlayer.Video
HKCU\Software\RegisteredApplications : "HEVC Player" = "Software\HEVCPlayer\Capabilities"
```

(Repeat the FileAssociations value for each extension you want.)

## Controls

| Key / Action | Function |
|---|---|
| `Space` | Play / Pause |
| `←` / `→` | Seek ∓10s |
| `↑` / `↓` | Volume |
| Mouse wheel | Volume |
| `F` / double-click | Fullscreen |
| `Esc` | Exit fullscreen |
| `O` | Open file |
| Click on video | Play / Pause |
| `Q` | Quit |

## Building the exe from the code

The entire app is `hevc_player.py`. To rebuild the exe yourself (needs Python 3.11+ once, only for building — users never need it):

```bat
pip install -r requirements.txt pyinstaller
python make_icon.py
python -m PyInstaller --noconfirm --clean --windowed --onefile --name HEVCPlayer --icon icon.ico --collect-all av --collect-all sounddevice hevc_player.py
```

Output: `dist\HEVCPlayer.exe`

## How it works

The app decodes video/audio through **PyAV** (FFmpeg bindings) in a background demux thread. Audio PCM is played through a PortAudio callback whose sample counter acts as the master clock; video frames are displayed when their PTS is due, keeping lipsync. Seek resets queues, flushes decoders, and re-syncs both streams.

## License

MIT
