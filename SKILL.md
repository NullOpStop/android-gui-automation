---
name: android_gui
description: Provides commands to interact with the Android screen, extract UI hierarchies, run OCR, and navigate using native shortcuts.
---

# Android GUI Automation Skill

This skill provides you with a robust python script (`scripts/gui_helper.py`) that bridges the gap between text-based AI and Android's visual interface. It uses ADB via Shizuku (`rish`) to read the screen, extract text, and simulate touches.

## The Script
You can invoke the helper script directly:
`python /data/data/com.termux/files/home/.agents/skills/android_gui/scripts/gui_helper.py <command>`

### Command 1: `dump` (Native UI Tree)
Extracts the UI hierarchy into a clean JSON list of clickable elements with precise X/Y coordinates.
* **Usage:** `python gui_helper.py dump`
* **When to use:** Try this first! It gives you exact coordinates for native Android UI elements.
* **Note:** This often fails on WebViews or heavily customized apps. If it returns an empty node, use `ocr` or `grid`.

### Command 2: `ocr` (Visual Text Extraction)
Takes a screenshot and runs OCR (Optical Character Recognition) to find text on the screen, returning bounding boxes grouped by lines.
* **Usage:** `python gui_helper.py ocr`
* **When to use:** When `dump` fails (e.g. inside WebViews or Games). This perfectly extracts text labels and their center coordinates for tapping.

### Command 3: `tap_text` (Safe Selector Tapping)
Instantly runs OCR, finds the specified text, and taps its exact center point.
* **Usage:** `python gui_helper.py tap_text "Bet Now"`
* **When to use:** This is the PREFERRED way to click buttons when `dump` fails. Unlike hardcoding coordinates (which break if the keyboard opens or screen rotates), this searches for the text dynamically on every run, ensuring it never clicks the wrong spot.

### Command 4: `nav` (System Navigation)
Triggers native hardware keyevents for robust system navigation.
* **Usage:** `python gui_helper.py nav <home|back|recents|power|enter|tab>`
* **When to use:** ALWAYS use this for system navigation instead of trying to tap the navigation bar coordinates, as coordinates break with gestures and rotation. Note: `nav recents` opens the app switcher, it does not instantly jump to the last app.

### Command 5: `grid` (Visual Fallback)
Takes a screenshot and draws a labeled 10x10 grid over it, saving it to `screen_grid.png`.
* **Usage:** `python gui_helper.py grid`
* **When to use:** If both `dump` and `ocr` fail (e.g. for graphical icons without text), use this. You can then use your `view_file` tool to look at `screen_grid.png` and decide which grid box to tap.

### Command 6: `tap` (Raw Coordinate Tapping)
Simulates a touch at specific X/Y coordinates.
* **Usage:** `python gui_helper.py tap 500 1000`
* **When to use:** After identifying the correct coordinates from `grid`, `dump`, or `ocr`. (Prefer `tap_text` over manual `tap` when dealing with text).

## Best Practices for Agentic Navigation
1. **Never Cache Raw Coordinates:** Do not hardcode X/Y coordinates in your plans or scripts. Elements move due to keyboards, ads, scrolling, and rotations. Always use `dump` or `ocr` / `tap_text` to find elements dynamically.
2. Always maintain context of what app you are in.
