# Self-Contained Voice Call Transcription & Viewer

Drop or download any folder of `.wav` voice calls anywhere on your computer and run `./run` — it sets up Python dependencies automatically if needed, transcribes the calls with `faster-whisper` (`sv`, `en`, `no`, `da`), and opens an interactive HTML transcript + audio viewer.

## Usage

```bash
cd transcription

# Interactive: opens arrow-key CLI folder browser to pick your .wav folder
./run

# Or pass a downloaded folder directly (skips folder browser)
./run ~/Downloads/seb-audio-wavs

# Useful options:
./run --model small          # Higher accuracy for Swedish/Nordic calls
./run --limit 5              # Quick test on the first 5 calls
./run --skip-transcribe      # Rebuild & open viewer from existing output/transcripts.jsonl
./run --force                # Re-transcribe all files from scratch
```

## Files

- `run` — Self-contained executable entrypoint (CLI folder browser + auto-venv setup + transcribe + build & open viewer).
- `pick_folder.py` — Arrow-key terminal folder browser (`curses`, stdlib only) showing `.wav` counts per folder.
- `transcribe_audio.py` — Local `faster-whisper` CLI (pure `wave`/`numpy` 16 kHz decoder, incremental caching).
- `build_viewer.py` — Builds `output/viewer.html` with clickable timestamps synced to the local `.wav` files.
- `requirements.txt` — Python dependency (`faster-whisper`).
- `output/` *(gitignored)* — Generated `viewer.html`, `transcripts.jsonl`, and per-call `.txt` files.
