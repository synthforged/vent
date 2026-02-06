<div align="center">

# vent

**Voice-to-text overlay for Wayland. Click, speak, done.**

![vent states](vent-states.png)

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Linux](https://img.shields.io/badge/platform-Linux%20%2F%20Wayland-informational)

</div>

---

A small pill sits at the bottom of your screen. Click to record, click again to transcribe. The text gets typed into whatever window has focus. No GUI, no settings panels, no cloud. Runs locally on CPU with [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## Requirements

- Linux with a Wayland compositor (Hyprland, Sway, etc.)
- Python >= 3.11

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/synthforged/vent/main/install.sh | bash
```

Or from a local clone:

```bash
git clone https://github.com/synthforged/vent.git && cd vent
./install.sh
```

The installer detects your distro and handles system dependencies:

| Distro | Package manager |
|--------|----------------|
| Arch / CachyOS / Manjaro | pacman |
| Debian / Ubuntu | apt |
| Fedora | dnf |

Installs a venv at `~/.local/share/vent/` with a `vent` wrapper in `~/.local/bin/`.

<details>
<summary>Manual install</summary>

```bash
# Arch
sudo pacman -S gtk4 gtk4-layer-shell gobject-introspection cairo portaudio wtype wl-clipboard

# Debian/Ubuntu
sudo apt install build-essential python3-dev python3-venv pkg-config \
    libgirepository1.0-dev libcairo2-dev libgtk-4-dev gir1.2-gtk-4.0 \
    libportaudio2 portaudio19-dev wl-clipboard libgtk4-layer-shell-dev wtype

# Then
python -m venv .venv && source .venv/bin/activate
pip install -e .
vent
```

</details>

## Usage

Run `vent`. A small pill appears at the bottom of your screen.

| Action | Effect |
|--------|--------|
| Left-click (idle) | Start recording — red waveform bars |
| Left-click (recording/paused) | Stop and transcribe — green pulsing dots |
| Right-click (recording) | Pause — pill turns amber |
| Right-click (paused) | Resume recording |
| `q` | Quit (click pill first to focus) |

Transcribed text is copied to clipboard via `wl-copy` and typed into the focused window via `wtype`. Pause/resume cycles merge into one transcription.

## Speech recognition

Uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2 reimplementation of OpenAI Whisper). Runs on CPU, no GPU required.

| Setting | Value |
|---------|-------|
| Model | `small` (~461M params, ~500MB) |
| Quantization | `int8` |
| Audio | 16kHz mono float32 |
| Language | Auto-detected (99 languages) |

The model loads lazily on first transcription (2-5s). Subsequent calls are instant.

> English has the best accuracy. For other languages, swap to `medium` or `large-v3` in `transcriber.py`.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
ruff check .          # lint
ruff format --check . # formatting
```

CI runs on every PR. Ruff is the only gatekeeper.

## Uninstall

```bash
rm -rf ~/.local/share/vent ~/.local/bin/vent
```

## Security

See [SECURITY.md](SECURITY.md). No telemetry. No network requests (except Whisper model download on first run).

## License

[MIT](LICENSE)
