#!/usr/bin/env python3
"""
gui_helper.py — Android GUI automation helper for an AI agent.

Bridges to the device via Shizuku ('rish'). Sub-commands:
  dump    - UIAutomator dump -> JSON list of clickable elements.
  grid    - Screenshot -> 10x10 labeled grid overlay (screen_grid.png).
  tap X Y - Inject a tap at the given coordinates.

Standard library + Pillow only.
"""

import argparse
import io
import json
import re
import subprocess
import sys

RISH = "rish"
REMOTE_DUMP = "/data/local/tmp/window_dump.xml"
LOCAL_SCREEN = "screen.png"
LOCAL_GRID = "screen_grid.png"
RISH_TIMEOUT = 30

BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


# --- rish helpers ----------------------------------------------------------

def run_rish(remote_cmd, capture_binary=False):
    """Run `rish -c '<remote_cmd>'`. Raises RuntimeError on launch failure."""
    try:
        return subprocess.run(
            [RISH, "-c", remote_cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=RISH_TIMEOUT,
            text=not capture_binary,
        )
    except FileNotFoundError:
        raise RuntimeError(
            f"'{RISH}' not found on PATH. Is Shizuku/rish installed and exported?"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"rish timed out after {RISH_TIMEOUT}s: {remote_cmd}")


def stderr_text(proc):
    err = proc.stderr
    if isinstance(err, bytes):
        err = err.decode("utf-8", "replace")
    return (err or "").strip()


# --- dump ------------------------------------------------------------------

def cmd_dump(_args):
    """
    Dump the window hierarchy, print clickable elements as JSON.

    uiautomator quirks handled:
      - "could not get idle state" prints to stdout/stderr but the dump
        usually still succeeds, so it is NOT treated as fatal on its own.
      - The "dumped to: <path>" line goes to stdout, so stdout is NOT the
        XML; we always re-read the file from the device.
      - A "null root node" means a secure/non-dumpable window -> hard fail.
    """
    dump_proc = run_rish(f"uiautomator dump --compressed {REMOTE_DUMP}")
    noise = (dump_proc.stdout or "") + " " + stderr_text(dump_proc)
    if "null root node returned by UiTestAutomationBridge" in noise:
        fail("UIAutomator returned a null root node. The current screen is "
             "likely a secure window (keyboard, FLAG_SECURE app) and cannot be dumped.")

    xml = read_remote_xml()
    print(json.dumps(parse_clickables(xml), indent=2, ensure_ascii=False))


def read_remote_xml():
    """Read the dump back from the device, trimming idle-state noise. One retry."""
    for attempt in range(2):
        proc = run_rish(f"cat {REMOTE_DUMP}")
        text = proc.stdout or ""
        start = text.find("<?xml")
        if start == -1:
            start = text.find("<hierarchy")
        if start != -1:
            return text[start:]
        if attempt == 0:
            continue
        fail(f"Could not read {REMOTE_DUMP}: "
             f"{stderr_text(proc) or 'no XML content found in dump file'}")


def parse_clickables(xml_text):
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        fail(f"Failed to parse UIAutomator XML: {exc}")

    results = []
    for node in root.iter("node"):
        if node.get("clickable") != "true":
            continue
        parsed = parse_bounds(node.get("bounds", ""))
        if parsed is None:
            continue
        (cx, cy), (x1, y1, x2, y2) = parsed
        results.append({
            "text": (node.get("text") or "").strip(),
            "content_desc": (node.get("content-desc") or "").strip(),
            "resource_id": node.get("resource-id", ""),
            "class": node.get("class", ""),
            "bounds": [x1, y1, x2, y2],
            "center": {"x": cx, "y": cy},
        })
    return results


def parse_bounds(bounds_str):
    """'[x1,y1][x2,y2]' -> ((cx,cy),(x1,y1,x2,y2)) or None for zero-area/malformed."""
    m = BOUNDS_RE.search(bounds_str or "")
    if not m:
        return None
    x1, y1, x2, y2 = (int(v) for v in m.groups())
    if x2 <= x1 or y2 <= y1:
        return None
    return (((x1 + x2) // 2, (y1 + y2) // 2), (x1, y1, x2, y2))


# --- grid ------------------------------------------------------------------

def cmd_grid(_args):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        fail("Pillow is required for 'grid'. Install with: pip install Pillow")

    remote_png = "/sdcard/screen_temp.png"
    proc = run_rish(f"screencap -p {remote_png}")
    if proc.returncode != 0:
        fail(f"screencap failed: {stderr_text(proc)}")
        
    try:
        with open(remote_png, "rb") as fh:
            data = fh.read()
    except Exception as e:
        fail(f"Could not read {remote_png}: {e}")

    with open(LOCAL_SCREEN, "wb") as fh:
        fh.write(data)

    img = Image.open(io.BytesIO(data)).convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    cols = rows = 10
    cell_w, cell_h = w / cols, h / rows
    font = _load_font(ImageFont, max(12, int(min(cell_w, cell_h) * 0.22)))

    line_color = (255, 0, 0, 160)
    box_fill = (0, 0, 0, 90)
    text_color = (255, 255, 0, 230)

    for c in range(1, cols):
        x = round(c * cell_w)
        draw.line([(x, 0), (x, h)], fill=line_color, width=2)
    for r in range(1, rows):
        y = round(r * cell_h)
        draw.line([(0, y), (w, y)], fill=line_color, width=2)

    cell = 0
    for r in range(rows):
        for c in range(cols):
            label = str(cell)
            tx, ty = c * cell_w + 4, r * cell_h + 4
            tw, th = _text_size(draw, label, font)
            draw.rectangle([tx - 2, ty - 2, tx + tw + 2, ty + th + 2], fill=box_fill)
            draw.text((tx, ty), label, fill=text_color, font=font)
            cell += 1

    Image.alpha_composite(img, overlay).convert("RGB").save(LOCAL_GRID)
    print(json.dumps({
        "status": "ok",
        "screenshot": LOCAL_SCREEN,
        "grid_image": LOCAL_GRID,
        "size": {"width": w, "height": h},
        "cells": cols * rows,
        "cell_size": {"width": round(cell_w, 1), "height": round(cell_h, 1)},
    }, indent=2))


def _load_font(ImageFont, size):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/system/fonts/DroidSans.ttf",
        "/system/fonts/Roboto-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _text_size(draw, text, font):
    if hasattr(draw, "textbbox"):
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        return r - l, b - t
    return draw.textsize(text, font=font)  # Pillow < 8


# --- tap -------------------------------------------------------------------

def cmd_tap(args):
    if args.x < 0 or args.y < 0:
        fail(f"Coordinates must be non-negative, got ({args.x}, {args.y})")
    proc = run_rish(f"input tap {args.x} {args.y}")
    if proc.returncode != 0:
        fail(f"input tap failed: {stderr_text(proc) or 'unknown error'}")
    print(json.dumps({"status": "ok", "action": "tap", "x": args.x, "y": args.y}))


# --- error handling --------------------------------------------------------

def fail(message):
    """Emit a machine-parseable JSON error and exit non-zero."""
    print(json.dumps({"status": "error", "message": message}))
    sys.exit(1)


# --- CLI -------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Android GUI automation helper (via Shizuku/rish)."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("dump", help="Dump clickable UI elements as JSON.")
    sub.add_parser("grid", help="Screenshot with a 10x10 labeled grid overlay.")
    p_tap = sub.add_parser("tap", help="Tap at screen coordinates.")
    p_tap.add_argument("x", type=int)
    p_tap.add_argument("y", type=int)

    args = parser.parse_args()
    try:
        {"dump": cmd_dump, "grid": cmd_grid, "tap": cmd_tap}[args.command](args)
    except RuntimeError as exc:
        fail(str(exc))


if __name__ == "__main__":
    main()
