#!/usr/bin/env python3
"""
Local transcription engine for SEB Kort synthetic voice calls (.wav).

Uses faster-whisper (multilingual: sv, en, no, da) with a pure wave/numpy
16 kHz decoder. Saves per-call .txt files and `transcription/output/transcripts.jsonl`
(including clickable segment timestamps for the HTML viewer).
"""

from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path

DEFAULT_AUDIO_DIR = Path("SEB Kort hackathon synthetic data share/full dataset/audio")
DEFAULT_OUT_DIR = Path("transcription/output")


def load_wav_16k(path: Path):
    """Decode a 16-bit PCM .wav file to 16 kHz mono float32 numpy array."""
    import numpy as np

    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if ch > 1:
            pcm = pcm.reshape(-1, ch).mean(axis=1)
    if sr != 16000:
        new_len = int(round(len(pcm) * 16000 / sr))
        pcm = np.interp(np.linspace(0, len(pcm) - 1, new_len), np.arange(len(pcm)), pcm).astype(np.float32)
    return pcm


def load_manifest(audio_dir: Path) -> dict[str, dict]:
    manifest_path = audio_dir / "audio_manifest.jsonl"
    meta: dict[str, dict] = {}
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                meta[row["audio_file"]] = row
    return meta


def load_existing(jsonl_path: Path) -> dict[str, dict]:
    existing: dict[str, dict] = {}
    if jsonl_path.exists():
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                # Only reuse entries that already have structured segments
                if row.get("segments"):
                    existing[row["audio_file"]] = row
    return existing


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe SEB Kort .wav voice calls locally.")
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR)
    parser.add_argument("--file", type=str, default=None, help="Single .wav filename to transcribe.")
    parser.add_argument("--limit", type=int, default=None, help="Max number of .wav files to transcribe.")
    parser.add_argument("--model", type=str, default="base", help="Whisper model size: tiny, base, small, medium.")
    parser.add_argument("--force", action="store_true", help="Re-transcribe files even if already transcribed.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print(
            "Error: faster-whisper is not installed.\n"
            "Run: /Users/tony/.local/bin/python3.12 -m venv .venv && .venv/bin/pip install faster-whisper",
            file=sys.stderr,
        )
        return 1

    if not args.audio_dir.exists():
        print(f"Error: audio directory not found: {args.audio_dir}", file=sys.stderr)
        return 1

    manifest = load_manifest(args.audio_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.out_dir / "transcripts.jsonl"
    existing = {} if args.force else load_existing(jsonl_path)

    if args.file:
        wav_files = [args.audio_dir / args.file]
        if not wav_files[0].exists():
            print(f"Error: file not found: {wav_files[0]}", file=sys.stderr)
            return 1
    else:
        wav_files = sorted(args.audio_dir.glob("*.wav"))
        if args.limit:
            wav_files = wav_files[: args.limit]

    to_process = [w for w in wav_files if w.name not in existing]
    model = None
    if to_process:
        print(f"Loading Whisper model '{args.model}' (CPU int8)...")
        model = WhisperModel(args.model, device="cpu", compute_type="int8")

    results_map: dict[str, dict] = dict(existing)

    for idx, wav in enumerate(wav_files, start=1):
        if wav.name in existing:
            print(f"[{idx}/{len(wav_files)}] Cached: {wav.name} (use --force to re-run)")
            continue

        info_meta = manifest.get(wav.name, {})
        lang_hint = info_meta.get("language")
        conv_id = info_meta.get("conversation_id", wav.stem)

        print(f"[{idx}/{len(wav_files)}] Transcribing {wav.name} (lang={lang_hint or 'auto'})...")
        segments_iter, info = model.transcribe(
            load_wav_16k(wav),
            language=lang_hint,
            beam_size=5,
            vad_filter=True,
        )

        segments_list = []
        lines = []
        for seg in segments_iter:
            text = seg.text.strip()
            if text:
                segments_list.append({"start": round(seg.start, 2), "end": round(seg.end, 2), "text": text})
                lines.append(f"[{seg.start:05.1f}s - {seg.end:05.1f}s] {text}")

        full_text = "\n".join(lines)
        plain_text = " ".join(s["text"] for s in segments_list)

        txt_path = args.out_dir / f"{conv_id}.txt"
        txt_path.write_text(
            f"Conversation: {conv_id}\n"
            f"Audio file:   {wav.name}\n"
            f"Language:     {info.language} (prob={info.language_probability:.2f})\n"
            f"Duration:     {info.duration:.1f}s\n"
            f"{'-' * 60}\n"
            f"{full_text}\n",
            encoding="utf-8",
        )

        results_map[wav.name] = {
            "conversation_id": conv_id,
            "audio_file": wav.name,
            "language": info.language,
            "duration_sec": round(info.duration, 1),
            "transcript_whisper": plain_text,
            "transcript_timestamped": full_text,
            "segments": segments_list,
        }

        # Persist incrementally so progress is never lost
        ordered = [results_map[k] for k in sorted(results_map)]
        with jsonl_path.open("w", encoding="utf-8") as f:
            for row in ordered:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\nReady: {len(results_map)} transcripts saved in {jsonl_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
