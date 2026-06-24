# Grammar Reflex Trainer

A minimalist desktop application for drilling subject-verb "to be" agreement across tenses. Built with **CustomTkinter** for a modern, native-looking dark-mode UI.

---

## Features

- **Flashcard Drill** — Randomly flashes a subject + tense pair on every metronome beat.
- **Metronome Audio** — A clean, non-intrusive beep synced to card transitions (with mute toggle).
- **BPM Control** — Adjustable speed from 30 BPM (2 s/card) to 75 BPM (0.8 s/card).
- **Session Timer** — Choose 2, 3, or 5 minute sessions with a live countdown.
- **Auto Reveal** — Instantly shows the correct answer, or hide it for self-testing.
- **Data Editor** — Add, edit, or delete subject/tense pairs directly in the app.
- **Keyboard Shortcuts** — Space to start/stop, `M` to toggle audio, `R` to reveal, `Esc` to stop.

---

## Installation

### 1. Clone or download the files

Ensure these three files are in the same directory:
- `grammar_trainer.py`
- `subjects.json`
- `README.md` (this file)

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv
```

Activate it:
- **Windows:** `.venv\Scripts\activate`
- **macOS/Linux:** `source .venv/bin/activate`

### 3. Install dependencies

```bash
pip install customtkinter
```

*(Optional but recommended for better audio)*
```bash
pip install pygame
```

If `pygame` is not installed, the app will fall back to the system bell.

---

## Running the App

```bash
python grammar_trainer.py
```

The app will automatically create a default `subjects.json` if one does not exist.

---

## Project Structure

```
.
├── grammar_trainer.py   # Main application
├── subjects.json        # Training data (auto-created if missing)
└── README.md            # This file
```

---

## Customizing the Data

Click **Edit Data** in the app to open the built-in editor. You can add, modify, or remove subject/tense pairs. Changes are saved back to `subjects.json` automatically.

### JSON Format

```json
[
  {
    "subject": "The economy",
    "tense": "Present",
    "answer": "is"
  },
  {
    "subject": "The children",
    "tense": "Past",
    "answer": "were"
  }
]
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Start / Stop session |
| `M` | Toggle audio metronome |
| `R` | Reveal answer (manual mode) |
| `Esc` | Stop session |

---

## Requirements

- Python 3.10+
- `customtkinter` (required)
- `pygame` (optional, for audio)

---

## License

MIT — feel free to modify and share.
