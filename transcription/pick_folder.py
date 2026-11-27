#!/usr/bin/env python3
"""Interactive terminal folder selector (arrow keys + Enter) for choosing a .wav directory."""

from __future__ import annotations

import curses
import os
import sys
from pathlib import Path


def count_wavs(directory: Path) -> int:
    try:
        return sum(1 for p in directory.iterdir() if p.is_file() and p.suffix.lower() == ".wav")
    except OSError:
        return 0


def list_subdirs(directory: Path) -> list[Path]:
    try:
        return sorted(
            [p for p in directory.iterdir() if p.is_dir() and not p.name.startswith(".")],
            key=lambda p: p.name.lower(),
        )
    except OSError:
        return []


def run_picker(stdscr, start_dir: Path) -> Path | None:
    curses.curs_set(0)
    stdscr.keypad(True)

    current = start_dir.resolve()
    cursor = 0
    scroll = 0

    while True:
        wav_here = count_wavs(current)
        subdirs = list_subdirs(current)

        entries: list[tuple[str, str, Path | None]] = []
        if wav_here > 0:
            entries.append(("select", f"[✓] Select THIS folder ({wav_here} .wav files)", current))
        if current.parent != current:
            entries.append(("dir", "../  (parent folder)", current.parent))
        for d in subdirs:
            n = count_wavs(d)
            suffix = f"  ({n} .wav)" if n else ""
            entries.append(("dir", f"{d.name}/{suffix}", d))

        if not entries:
            entries.append(("select", "[✓] Select THIS folder (0 .wav files)", current))

        cursor = max(0, min(cursor, len(entries) - 1))
        h, w = stdscr.getmaxyx()
        list_top = 4
        visible_rows = max(1, h - list_top - 2)

        if cursor < scroll:
            scroll = cursor
        elif cursor >= scroll + visible_rows:
            scroll = cursor - visible_rows + 1

        stdscr.erase()
        title = "Select folder containing .wav voice files"
        stdscr.addnstr(0, 1, title, w - 2, curses.A_BOLD)
        stdscr.addnstr(1, 1, f"Current: {current}  ({wav_here} .wav files here)", w - 2)
        stdscr.addnstr(2, 1, "↑/↓ move  ·  Enter open/select  ·  s select current  ·  q cancel", w - 2, curses.A_DIM)

        for row_idx in range(visible_rows):
            idx = scroll + row_idx
            if idx >= len(entries):
                break
            kind, label, _ = entries[idx]
            prefix = "▸ " if idx == cursor else "  "
            attr = curses.A_REVERSE if idx == cursor else (curses.A_BOLD if kind == "select" else curses.A_NORMAL)
            stdscr.addnstr(list_top + row_idx, 1, prefix + label, w - 2, attr)

        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_UP, ord("k")):
            cursor = (cursor - 1) % len(entries)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = (cursor + 1) % len(entries)
        elif key in (ord("q"), ord("Q"), 27):  # q or Esc
            return None
        elif key in (ord("s"), ord("S")):
            return current
        elif key in (curses.KEY_BACKSPACE, 127, 8, curses.KEY_LEFT):
            if current.parent != current:
                current = current.parent
                cursor = 0
                scroll = 0
        elif key in (10, 13, curses.KEY_ENTER, curses.KEY_RIGHT):
            kind, _, target = entries[cursor]
            if kind == "select":
                return target
            if target is not None:
                current = target
                cursor = 0
                scroll = 0


def main() -> int:
    start = Path(sys.argv[1]) if len(sys.argv) > 1 and Path(sys.argv[1]).is_dir() else Path.cwd()

    # Bind curses to /dev/tty so stdout cleanly returns only the selected path
    tty_in = open("/dev/tty", "r")
    tty_out = open("/dev/tty", "w")
    saved_stdin = os.dup(0)
    saved_stdout = os.dup(1)
    try:
        os.dup2(tty_in.fileno(), 0)
        os.dup2(tty_out.fileno(), 1)
        chosen = curses.wrapper(run_picker, start)
    finally:
        os.dup2(saved_stdin, 0)
        os.dup2(saved_stdout, 1)
        os.close(saved_stdin)
        os.close(saved_stdout)
        tty_in.close()
        tty_out.close()

    if chosen is None:
        return 1
    print(str(chosen))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
