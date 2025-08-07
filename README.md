## desktop-tetra (macOS Accessibility Agent)

A minimal functional macOS desktop automation agent that uses the Accessibility API to:

- Find UI elements by semantic attributes (title, role, app)
- Click, type, focus/open apps
- Record human actions (basic) and play them back
- Provide a CLI for simple high-level tasks

This targets macOS (requires Accessibility permissions). No GUI; CLI only.

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

Grant terminal (or your Python app) Accessibility permission:
- System Settings → Privacy & Security → Accessibility → enable your Terminal app (iTerm2/Terminal) and/or Python.

### Quick check

```bash
python -m desktop_tetra.cli info
```

### Usage examples

```bash
# Click a button with title "OK" in the frontmost app
python -m desktop_tetra.cli click --title "OK"

# Type text into the focused field
python -m desktop_tetra.cli type --text "Hello world"

# Focus an app and then click a menu item
python -m desktop_tetra.cli focus-app --app "Notes"
python -m desktop_tetra.cli click --role "AXMenuItem" --title "New Note"

# Record actions (Ctrl+C to stop), then play
python -m desktop_tetra.cli record --out actions.json
python -m desktop_tetra.cli play --in actions.json
```

### Notes
- Tested on macOS 14/15. Uses PyObjC and AX APIs.
- Recording is basic (mouse/key events) and not perfect; intended as scaffolding.
- Running from a signed app bundle may require additional entitlements.
