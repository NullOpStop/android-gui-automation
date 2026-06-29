---
name: android_gui
description: Provides commands to interact with the Android screen, extract UI hierarchies, and capture visual grids for autonomous GUI navigation.
---

# Android GUI Automation Skill

This skill provides you with a robust python script (`scripts/gui_helper.py`) that bridges the gap between text-based AI and Android's visual interface. It uses ADB via Shizuku (`rish`) to read the screen and simulate touches.

## The Script
You can invoke the helper script directly:
`python /data/data/com.termux/files/home/.agents/skills/android_gui/scripts/gui_helper.py <command>`

### Command 1: `dump` (Primary Method)
Extracts the UI hierarchy into a clean JSON list of clickable elements with precise X/Y coordinates.
* **Usage:** `python gui_helper.py dump`
* **When to use:** ALWAYS try this first! It is fast, precise, and gives you exact coordinates for text elements and buttons. 
* **Note:** Sometimes fails with "idle state" error if the screen has animations. The script attempts to handle this gracefully.

### Command 2: `grid` (Fallback Method)
Takes a screenshot and draws a labeled 10x10 grid over it, saving it to `screen_grid.png`.
* **Usage:** `python gui_helper.py grid`
* **When to use:** If `dump` fails or if the app blocks UI dumping (like games or secure apps), use this. You can then use your `view_file` tool to look at `screen_grid.png` and decide which grid box to tap.

### Command 3: `tap`
Simulates a touch at specific X/Y coordinates.
* **Usage:** `python gui_helper.py tap 500 1000`
* **When to use:** After identifying the correct coordinates from `dump` or `grid`.

## Best Practices for Agentic Navigation
1. Always maintain context of what app you are in.
2. If `dump` returns empty or errors out, fall back to `grid` and visual inspection.
3. Be aware that scrolling (`input swipe x1 y1 x2 y2`) may be required to find off-screen elements.
