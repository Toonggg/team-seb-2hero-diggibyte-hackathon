#!/usr/bin/env python3
"""Build a tiny self-contained HTML viewer to read & play transcribed SEB voice calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
DEFAULT_JSONL = HERE / "output" / "transcripts.jsonl"
DEFAULT_OUT = HERE / "output" / "viewer.html"
DEFAULT_AUDIO_DIR = HERE.parent / "SEB Kort hackathon synthetic data share/full dataset/audio"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build tiny HTML transcript + audio viewer.")
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not args.jsonl.exists():
        raise SystemExit(f"Error: {args.jsonl} not found. Run transcribe_audio.py first.")

    audio_dir_abs = args.audio_dir.resolve()
    items = [json.loads(line) for line in args.jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    for item in items:
        wav_path = (audio_dir_abs / item["audio_file"]).resolve()
        item["audio_src"] = wav_path.as_uri()

    safe_json = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SEB Kort — Voice Call Transcript Viewer</title>
  <style>
    :root {{
      --bg: #f6f8f7;
      --surface: #ffffff;
      --muted: #f0f4f1;
      --border: #dde4df;
      --text: #111827;
      --sub: #4b5563;
      --green: #007a33;
      --green-soft: #e7f6ec;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
      background: var(--bg);
      color: var(--text);
      height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr;
    }}
    header {{
      background: #112d2b;
      color: #fff;
      padding: 14px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }}
    header h1 {{ margin: 0; font-size: 1.05rem; letter-spacing: 0.01em; }}
    header span {{ font-size: 0.84rem; color: #b9dfd7; }}
    .layout {{
      display: grid;
      grid-template-columns: 310px 1fr;
      min-height: 0;
    }}
    @media (max-width: 800px) {{
      .layout {{ grid-template-columns: 1fr; grid-template-rows: 260px 1fr; }}
    }}
    aside {{
      background: var(--surface);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      min-height: 0;
    }}
    .filters {{
      padding: 12px;
      border-bottom: 1px solid var(--border);
      display: grid;
      gap: 8px;
    }}
    .filters input, .filters select {{
      font: inherit;
      font-size: 0.86rem;
      padding: 7px 10px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--surface);
      color: var(--text);
      width: 100%;
    }}
    .call-list {{
      overflow-y: auto;
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .call-btn {{
      text-align: left;
      border: 1px solid var(--border);
      background: var(--surface);
      border-radius: 8px;
      padding: 9px 11px;
      cursor: pointer;
      font: inherit;
      color: var(--text);
    }}
    .call-btn:hover {{ background: var(--muted); }}
    .call-btn[aria-current="true"] {{
      background: var(--green-soft);
      border-color: var(--green);
    }}
    .call-id {{ font-weight: 700; font-size: 0.86rem; display: block; }}
    .call-meta {{ font-size: 0.76rem; color: var(--sub); font-variant-numeric: tabular-nums; }}
    main {{
      display: flex;
      flex-direction: column;
      min-height: 0;
      padding: 18px 22px;
      gap: 14px;
    }}
    .player-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .player-top {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: baseline;
      gap: 8px;
    }}
    .player-top h2 {{ margin: 0; font-size: 1.05rem; }}
    .player-top span {{ font-size: 0.84rem; color: var(--sub); }}
    audio {{ width: 100%; height: 38px; }}
    .transcript-box {{
      flex: 1;
      overflow-y: auto;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .seg-btn {{
      display: grid;
      grid-template-columns: 64px 1fr;
      gap: 10px;
      text-align: left;
      border: 1px solid transparent;
      background: transparent;
      border-radius: 8px;
      padding: 7px 10px;
      cursor: pointer;
      font: inherit;
      font-size: 0.9rem;
      line-height: 1.45;
      color: var(--text);
    }}
    .seg-btn:hover {{ background: var(--muted); }}
    .seg-btn.active {{
      background: var(--green-soft);
      border-color: var(--green);
    }}
    .seg-time {{
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--green);
      font-variant-numeric: tabular-nums;
      padding-top: 2px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>SEB Kort &middot; Voice Call Transcript Viewer</h1>
    <span id="header-count"></span>
  </header>
  <div class="layout">
    <aside>
      <div class="filters">
        <input id="search" type="search" placeholder="Search transcripts or call ID..." aria-label="Search transcripts" />
        <select id="lang" aria-label="Filter by language">
          <option value="">All languages</option>
        </select>
      </div>
      <div class="call-list" id="call-list"></div>
    </aside>
    <main>
      <div class="player-card">
        <div class="player-top">
          <h2 id="active-title">Select a call</h2>
          <span id="active-meta">Click any timestamp below to jump the audio player</span>
        </div>
        <audio id="audio" controls preload="metadata"></audio>
      </div>
      <div class="transcript-box" id="transcript-box"></div>
    </main>
  </div>

  <script id="transcript-data" type="application/json">{safe_json}</script>
  <script>
    const CALLS = JSON.parse(document.getElementById('transcript-data').textContent);
    const callList = document.getElementById('call-list');
    const searchEl = document.getElementById('search');
    const langEl = document.getElementById('lang');
    const audioEl = document.getElementById('audio');
    const titleEl = document.getElementById('active-title');
    const metaEl = document.getElementById('active-meta');
    const boxEl = document.getElementById('transcript-box');

    document.getElementById('header-count').textContent = `${{CALLS.length}} transcribed calls`;

    for (const lang of [...new Set(CALLS.map(c => c.language))].sort()) {{
      langEl.append(new Option(lang.toUpperCase(), lang));
    }}

    let activeId = null;
    let activeSegButtons = [];

    function fmtTime(sec) {{
      const m = Math.floor(sec / 60);
      const s = Math.floor(sec % 60);
      return `${{String(m).padStart(2, '0')}}:${{String(s).padStart(2, '0')}}`;
    }}

    function openCall(call) {{
      activeId = call.conversation_id;
      titleEl.textContent = call.conversation_id;
      metaEl.textContent = `${{call.audio_file}} · Language: ${{call.language.toUpperCase()}} · Duration: ${{fmtTime(call.duration_sec)}}`;
      audioEl.src = call.audio_src;

      boxEl.replaceChildren();
      activeSegButtons = [];
      const segs = call.segments && call.segments.length
        ? call.segments
        : [{{ start: 0, end: call.duration_sec, text: call.transcript_whisper || '' }}];

      for (const seg of segs) {{
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'seg-btn';
        btn.dataset.start = String(seg.start);
        btn.dataset.end = String(seg.end);

        const tSpan = document.createElement('span');
        tSpan.className = 'seg-time';
        tSpan.textContent = fmtTime(seg.start);

        const txtSpan = document.createElement('span');
        txtSpan.textContent = seg.text;

        btn.append(tSpan, txtSpan);
        btn.addEventListener('click', () => {{
          audioEl.currentTime = seg.start;
          audioEl.play().catch(() => {{}});
        }});
        boxEl.append(btn);
        activeSegButtons.push(btn);
      }}

      renderList();
    }}

    audioEl.addEventListener('timeupdate', () => {{
      const t = audioEl.currentTime;
      for (const btn of activeSegButtons) {{
        const s = Number(btn.dataset.start);
        const e = Number(btn.dataset.end);
        btn.classList.toggle('active', t >= s && t <= e + 0.25);
      }}
    }});

    function renderList() {{
      const q = searchEl.value.trim().toLowerCase();
      const lang = langEl.value;
      callList.replaceChildren();

      const filtered = CALLS.filter(c => {{
        if (lang && c.language !== lang) return false;
        if (!q) return true;
        return (`${{c.conversation_id}} ${{c.transcript_whisper || ''}}`).toLowerCase().includes(q);
      }});

      for (const call of filtered) {{
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'call-btn';
        btn.setAttribute('aria-current', String(call.conversation_id === activeId));

        const idSpan = document.createElement('span');
        idSpan.className = 'call-id';
        idSpan.textContent = call.conversation_id;

        const mSpan = document.createElement('span');
        mSpan.className = 'call-meta';
        mSpan.textContent = `${{call.language.toUpperCase()}} · ${{fmtTime(call.duration_sec)}}`;

        btn.append(idSpan, mSpan);
        btn.addEventListener('click', () => openCall(call));
        callList.append(btn);
      }}

      if (!filtered.length) {{
        const p = document.createElement('p');
        p.style.padding = '12px';
        p.style.color = 'var(--sub)';
        p.textContent = 'No matching calls.';
        callList.append(p);
      }}
    }}

    searchEl.addEventListener('input', renderList);
    langEl.addEventListener('change', renderList);

    if (CALLS.length) openCall(CALLS[0]);
    else renderList();
  </script>
</body>
</html>
"""

    args.out.write_text(html, encoding="utf-8")
    print(f"Built transcript viewer -> {args.out} ({len(items)} calls)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
