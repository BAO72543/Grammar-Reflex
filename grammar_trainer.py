#!/usr/bin/env python3
"""
Grammar Reflex Trainer
A minimalist desktop app for drilling subject-verb "to be" agreement.
Built with CustomTkinter for a modern, native-looking UI.

Adaptive Text Sizing: Automatically scales text to fit the card,
wraps to multiple lines for very long subjects, and maintains
sharp, crisp rendering at all sizes.
"""

import customtkinter as ctk
import json
import random
import os
import io
import math
import struct
from tkinter import messagebox, font as tkfont

# ---------------------------------------------------------------------------
# Optional audio backend (pygame). Falls back gracefully if unavailable.
# ---------------------------------------------------------------------------
try:
    import pygame.mixer
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


# ---------------------------------------------------------------------------
# Audio helper: generate an in-memory WAV beep so no external assets are needed.
# ---------------------------------------------------------------------------
def generate_beep(frequency: int = 1000, duration_ms: int = 120,
                  volume: float = 0.4, sample_rate: int = 44100) -> io.BytesIO:
    """Return a BytesIO containing a mono 16-bit PCM WAV sine-wave beep."""
    num_samples = int(sample_rate * duration_ms / 1000.0)
    data_size = num_samples * 2  # 16-bit samples

    buf = io.BytesIO()

    # RIFF / WAVE header
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")

    # fmt chunk
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))               # Subchunk1Size
    buf.write(struct.pack("<H", 1))                 # AudioFormat (PCM)
    buf.write(struct.pack("<H", 1))                 # NumChannels (Mono)
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", sample_rate * 2))  # ByteRate
    buf.write(struct.pack("<H", 2))                 # BlockAlign
    buf.write(struct.pack("<H", 16))                # BitsPerSample

    # data chunk
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))

    # Sine-wave PCM data
    for i in range(num_samples):
        t = i / sample_rate
        sample = volume * 32767 * math.sin(2.0 * math.pi * frequency * t)
        buf.write(struct.pack("<h", int(sample)))

    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Adaptive Text Label — automatically scales font and wraps text to fit
# ---------------------------------------------------------------------------
class AdaptiveLabel(ctk.CTkFrame):
    """
    A label that automatically adjusts its font size to fit available width.
    Supports multi-line wrapping for very long text.
    """

    def __init__(self, master, text_color="white", font_family="SF Pro Display",
                 max_font_size=80, min_font_size=24, weight="bold",
                 wrap_threshold=0.85, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._text_color = text_color
        self._font_family = font_family
        self._max_font_size = max_font_size
        self._min_font_size = min_font_size
        self._weight = weight
        self._wrap_threshold = wrap_threshold  # % of width before wrapping
        self._current_text = ""
        self._current_font_size = max_font_size

        # The actual label widget
        self._label = ctk.CTkLabel(
            self,
            text="",
            text_color=text_color,
            font=ctk.CTkFont(family=font_family, size=max_font_size, weight=weight),
            wraplength=0,
            justify="center",
        )
        self._label.pack(expand=True, fill="both", padx=20, pady=10)

        # Track resize events
        self.bind("<Configure>", self._on_configure)
        self._pending_resize = None

    def _on_configure(self, event=None):
        """Debounce resize events to avoid excessive recalculation."""
        if self._pending_resize:
            self.after_cancel(self._pending_resize)
        self._pending_resize = self.after(50, self._refit_text)

    def set_text(self, text: str):
        """Set new text and trigger refitting."""
        self._current_text = text
        self._refit_text()

    def _refit_text(self):
        """Calculate optimal font size and wrap length for the current text."""
        if not self._current_text:
            self._label.configure(text="")
            return

        # Available dimensions (with padding)
        avail_width = max(self.winfo_width() - 60, 200)
        avail_height = max(self.winfo_height() - 40, 50)

        if avail_width < 50 or avail_height < 30:
            # Widget not ready yet, retry shortly
            self.after(100, self._refit_text)
            return

        # Binary search for best font size
        best_size = self._min_font_size
        best_wrap = 0

        for size in range(self._max_font_size, self._min_font_size - 1, -1):
            # Create a temporary font to measure text
            test_font = tkfont.Font(family=self._font_family, size=size, weight=self._weight)

            # Check if text fits on one line
            text_width = test_font.measure(self._current_text)

            if text_width <= avail_width * self._wrap_threshold:
                # Fits on one line, check height
                line_height = test_font.metrics("linespace")
                if line_height <= avail_height:
                    best_size = size
                    best_wrap = 0  # No wrapping needed
                    break
            else:
                # Would need wrapping — estimate lines needed
                wrap_at = int(avail_width * 0.9)
                # Rough line count estimate
                chars_per_line = max(wrap_at // max(test_font.measure("M"), 1), 1)
                estimated_lines = max(len(self._current_text) // chars_per_line, 1)
                total_height = estimated_lines * test_font.metrics("linespace") * 1.2

                if total_height <= avail_height and size >= best_size:
                    best_size = size
                    best_wrap = wrap_at

        # Apply the best settings
        self._current_font_size = best_size
        self._label.configure(
            text=self._current_text,
            font=ctk.CTkFont(family=self._font_family, size=best_size, weight=self._weight),
            wraplength=best_wrap if best_wrap > 0 else 0,
        )

    def get_text(self) -> str:
        return self._current_text


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------
class GrammarReflexTrainer(ctk.CTk):
    """Main application window."""

    # ----------------------------- Constants -------------------------------
    BG_COLOR = "#0f172a"          # slate-900
    CARD_BG = "#1e293b"           # slate-800
    CARD_BORDER = "#334155"       # slate-700
    ACCENT_BLUE = "#3b82f6"       # blue-500
    ACCENT_BLUE_HOVER = "#2563eb" # blue-600
    ACCENT_EMERALD = "#34d399"    # emerald-400
    ACCENT_RED = "#ef4444"        # red-500
    ACCENT_RED_HOVER = "#dc2626"  # red-600
    TEXT_MUTED = "#94a3b8"        # slate-400
    TEXT_PRIMARY = "#f8fafc"      # slate-50

    def __init__(self):
        super().__init__()

        # Window setup
        self.title("Grammar Reflex Trainer")
        self.geometry("1000x780")
        self.minsize(900, 700)
        self.configure(fg_color=self.BG_COLOR)

        # CustomTkinter theme
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        # Data file (same directory as script)
        self.data_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "subjects.json"
        )
        self.subjects: list[dict] = []
        self.load_data()

        # Session state
        self.session_active = False
        self.session_time_remaining = 0
        self.cards_shown = 0
        self.current_card: dict | None = None
        self._after_card: str | None = None
        self._after_timer: str | None = None

        # Audio state
        self.audio_enabled = True
        self.auto_reveal = True
        self._beep_sound = None
        self._init_audio()

        # Build UI
        self.build_ui()
        self.bind_keyboard_shortcuts()

    # ========================= Audio =======================================
    def _init_audio(self):
        """Initialise the metronome beep (pygame) or mark audio unavailable."""
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                beep_buf = generate_beep(frequency=1000, duration_ms=120, volume=0.4)
                self._beep_sound = pygame.mixer.Sound(file=beep_buf)
            except Exception:
                self._beep_sound = None
        else:
            self._beep_sound = None

    def play_beep(self):
        """Play the metronome click if audio is enabled and available."""
        if not self.audio_enabled:
            return
        if self._beep_sound:
            self._beep_sound.play()
        else:
            # Fallback: system bell (always works, but quieter)
            self.bell()

    # ========================= Data I/O ==================================
    def load_data(self):
        """Load subject/tense/answer pairs from JSON."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.subjects = json.load(f)
            except Exception as exc:
                messagebox.showerror("Data Error", f"Failed to load subjects.json:\n{exc}")
                self.subjects = self._default_data()
        else:
            self.subjects = self._default_data()
            self.save_data()

    def save_data(self):
        """Persist current subject list back to JSON."""
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.subjects, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            messagebox.showerror("Save Error", f"Failed to write subjects.json:\n{exc}")

    @staticmethod
    def _default_data() -> list[dict]:
        """Return a starter dataset if no JSON exists yet."""
        return [
            {"subject": "I", "tense": "Present", "answer": "am"},
            {"subject": "You", "tense": "Present", "answer": "are"},
            {"subject": "He", "tense": "Present", "answer": "is"},
            {"subject": "She", "tense": "Present", "answer": "is"},
            {"subject": "It", "tense": "Present", "answer": "is"},
            {"subject": "We", "tense": "Present", "answer": "are"},
            {"subject": "They", "tense": "Present", "answer": "are"},
            {"subject": "The dog", "tense": "Present", "answer": "is"},
            {"subject": "The dogs", "tense": "Present", "answer": "are"},
            {"subject": "The economy", "tense": "Present", "answer": "is"},
            {"subject": "The children", "tense": "Present", "answer": "are"},
            {"subject": "My friend", "tense": "Present", "answer": "is"},
            {"subject": "My friends", "tense": "Present", "answer": "are"},
            {"subject": "Water", "tense": "Present", "answer": "is"},
            {"subject": "The apples", "tense": "Present", "answer": "are"},
            {"subject": "I", "tense": "Past", "answer": "was"},
            {"subject": "You", "tense": "Past", "answer": "were"},
            {"subject": "He", "tense": "Past", "answer": "was"},
            {"subject": "She", "tense": "Past", "answer": "was"},
            {"subject": "It", "tense": "Past", "answer": "was"},
            {"subject": "We", "tense": "Past", "answer": "were"},
            {"subject": "They", "tense": "Past", "answer": "were"},
            {"subject": "The dog", "tense": "Past", "answer": "was"},
            {"subject": "The dogs", "tense": "Past", "answer": "were"},
            {"subject": "The economy", "tense": "Past", "answer": "was"},
            {"subject": "The children", "tense": "Past", "answer": "were"},
            {"subject": "My friend", "tense": "Past", "answer": "was"},
            {"subject": "My friends", "tense": "Past", "answer": "were"},
            {"subject": "Water", "tense": "Past", "answer": "was"},
            {"subject": "The apples", "tense": "Past", "answer": "were"},
        ]

    # ========================= UI Construction ==============================
    def build_ui(self):
        """Assemble all widgets."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)   # Header
        self.grid_rowconfigure(1, weight=1)   # Card
        self.grid_rowconfigure(2, weight=0)   # Controls

        # --- Header ------------------------------------------------------
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=30, pady=(25, 10))
        hdr.grid_columnconfigure(0, weight=1)
        hdr.grid_columnconfigure(1, weight=0)
        hdr.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            hdr,
            text="Grammar Reflex Trainer",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=self.TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        self.timer_lbl = ctk.CTkLabel(
            hdr,
            text="Session: 03:00",
            font=ctk.CTkFont(size=18),
            text_color=self.TEXT_MUTED,
        )
        self.timer_lbl.grid(row=0, column=1)

        self.counter_lbl = ctk.CTkLabel(
            hdr,
            text="Cards: 0",
            font=ctk.CTkFont(size=18),
            text_color=self.TEXT_MUTED,
        )
        self.counter_lbl.grid(row=0, column=2, sticky="e")

        # --- Flashcard ---------------------------------------------------
        self.card = ctk.CTkFrame(
            self,
            fg_color=self.CARD_BG,
            border_color=self.CARD_BORDER,
            border_width=2,
            corner_radius=24,
        )
        self.card.grid(row=1, column=0, sticky="nsew", padx=50, pady=20)
        self.card.grid_columnconfigure(0, weight=1)
        self.card.grid_rowconfigure(0, weight=1)   # Top spacer
        self.card.grid_rowconfigure(1, weight=0)   # Subject
        self.card.grid_rowconfigure(2, weight=0)   # Tense
        self.card.grid_rowconfigure(3, weight=0)   # Answer
        self.card.grid_rowconfigure(4, weight=1)   # Bottom spacer

        # Subject — adaptive sizing label
        self.subject_lbl = AdaptiveLabel(
            self.card,
            text_color=self.TEXT_PRIMARY,
            max_font_size=80,
            min_font_size=28,
            weight="bold",
            wrap_threshold=0.85,
            height=160,
        )
        self.subject_lbl.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 4))
        self.subject_lbl.set_text("Ready?")

        # Tense marker
        self.tense_lbl = AdaptiveLabel(
            self.card,
            text_color=self.TEXT_MUTED,
            max_font_size=32,
            min_font_size=16,
            weight="normal",
            wrap_threshold=0.9,
            height=50,
        )
        self.tense_lbl.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 8))
        self.tense_lbl.set_text("Press START to begin")

        # Answer — adaptive sizing
        self.answer_lbl = AdaptiveLabel(
            self.card,
            text_color=self.ACCENT_EMERALD,
            max_font_size=56,
            min_font_size=24,
            weight="bold",
            wrap_threshold=0.9,
            height=90,
        )
        self.answer_lbl.grid(row=3, column=0, sticky="ew", padx=30, pady=(0, 20))
        self.answer_lbl.set_text("")

        # --- Controls toolbar --------------------------------------------
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=2, column=0, sticky="ew", padx=30, pady=(10, 25))
        for c in range(7):
            toolbar.grid_columnconfigure(c, weight=1)

        # BPM slider
        bpm_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        bpm_box.grid(row=0, column=0, padx=8, sticky="nsew")
        ctk.CTkLabel(bpm_box, text="Speed (BPM)", font=ctk.CTkFont(size=13)).pack()
        self.bpm_lbl = ctk.CTkLabel(bpm_box, text="45", font=ctk.CTkFont(size=14, weight="bold"))
        self.bpm_lbl.pack()
        self.bpm_slider = ctk.CTkSlider(
            bpm_box,
            from_=15,
            to=75,
            number_of_steps=45,
            command=self._on_bpm_change,
        )
        self.bpm_slider.set(45)
        self.bpm_slider.pack(fill="x", padx=5)

        # Duration
        dur_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        dur_box.grid(row=0, column=1, padx=8, sticky="nsew")
        ctk.CTkLabel(dur_box, text="Duration", font=ctk.CTkFont(size=13)).pack()
        self.dur_var = ctk.StringVar(value="3 min")
        ctk.CTkOptionMenu(
            dur_box,
            values=["2 min", "3 min", "5 min"],
            variable=self.dur_var,
            width=110,
        ).pack()

        # Audio toggle
        aud_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        aud_box.grid(row=0, column=2, padx=8, sticky="nsew")
        ctk.CTkLabel(aud_box, text="Audio", font=ctk.CTkFont(size=13)).pack()
        self.aud_sw = ctk.CTkSwitch(
            aud_box,
            text="",
            onvalue=True,
            offvalue=False,
            command=self._on_audio_toggle,
        )
        self.aud_sw.select()
        self.aud_sw.pack()

        # Auto-reveal toggle
        rev_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        rev_box.grid(row=0, column=3, padx=8, sticky="nsew")
        ctk.CTkLabel(rev_box, text="Auto Reveal", font=ctk.CTkFont(size=13)).pack()
        self.rev_sw = ctk.CTkSwitch(
            rev_box,
            text="",
            onvalue=True,
            offvalue=False,
            command=self._on_reveal_toggle,
        )
        self.rev_sw.select()
        self.rev_sw.pack()

        # Manual reveal button (only useful when auto-reveal is OFF)
        self.manual_rev_btn = ctk.CTkButton(
            toolbar,
            text="Reveal",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            command=self._manual_reveal,
            width=90,
            height=32,
        )
        self.manual_rev_btn.grid(row=0, column=4, padx=8)
        self.manual_rev_btn.configure(state="disabled")

        # Start / Stop
        self.start_btn = ctk.CTkButton(
            toolbar,
            text="START",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=self.ACCENT_BLUE,
            hover_color=self.ACCENT_BLUE_HOVER,
            command=self.toggle_session,
            width=130,
            height=42,
        )
        self.start_btn.grid(row=0, column=5, padx=8)

        # Edit data
        ctk.CTkButton(
            toolbar,
            text="Edit Data",
            font=ctk.CTkFont(size=13),
            fg_color="#475569",
            hover_color="#334155",
            command=self.open_editor,
            width=100,
            height=42,
        ).grid(row=0, column=6, padx=8)

    # ========================= Event Handlers ============================
    def _on_bpm_change(self, value):
        self.bpm_lbl.configure(text=f"{int(value)}")

    def _on_audio_toggle(self):
        self.audio_enabled = self.aud_sw.get()

    def _on_reveal_toggle(self):
        self.auto_reveal = self.rev_sw.get()
        if self.auto_reveal:
            self.manual_rev_btn.configure(state="disabled")
            if self.current_card:
                self._show_answer()
        else:
            self.manual_rev_btn.configure(state="normal")
            self.answer_lbl.set_text("")

    def _manual_reveal(self):
        if self.current_card:
            self._show_answer()

    def _show_answer(self):
        if self.current_card:
            self.answer_lbl.set_text(self.current_card.get("answer", ""))

    def _hide_answer(self):
        self.answer_lbl.set_text("")

    # ========================= Session Logic ===============================
    def toggle_session(self):
        if self.session_active:
            self.stop_session()
        else:
            self.start_session()

    def start_session(self):
        if not self.subjects:
            messagebox.showwarning("No Data", "Add at least one subject/tense pair first.")
            return

        self.session_active = True
        self.cards_shown = 0
        self.start_btn.configure(
            text="STOP",
            fg_color=self.ACCENT_RED,
            hover_color=self.ACCENT_RED_HOVER,
        )

        # Parse duration
        raw = self.dur_var.get()
        minutes = int(raw.split()[0])
        self.session_time_remaining = minutes * 60
        self._update_timer_display()

        # Kick off
        self._next_card()
        self._schedule_timer_tick()

    def stop_session(self):
        self.session_active = False
        self.start_btn.configure(
            text="START",
            fg_color=self.ACCENT_BLUE,
            hover_color=self.ACCENT_BLUE_HOVER,
        )

        if self._after_card:
            self.after_cancel(self._after_card)
            self._after_card = None
        if self._after_timer:
            self.after_cancel(self._after_timer)
            self._after_timer = None

        self.subject_lbl.set_text("Paused")
        self.tense_lbl.set_text("Press START to resume")
        self._hide_answer()
        self.current_card = None

    def _schedule_timer_tick(self):
        if not self.session_active:
            return
        self._after_timer = self.after(1000, self._timer_tick)

    def _timer_tick(self):
        if not self.session_active:
            return

        self.session_time_remaining -= 1
        self._update_timer_display()

        if self.session_time_remaining <= 0:
            self._finish_session()
            return

        self._schedule_timer_tick()

    def _update_timer_display(self):
        m, s = divmod(self.session_time_remaining, 60)
        self.timer_lbl.configure(text=f"Session: {m:02d}:{s:02d}")

    def _finish_session(self):
        self.stop_session()
        self.subject_lbl.set_text("Session Complete!")
        self.tense_lbl.set_text("Nice work.")
        self.answer_lbl.set_text(f"Total cards: {self.cards_shown}")

    def _next_card(self):
        if not self.session_active:
            return

        self.current_card = random.choice(self.subjects)
        self.cards_shown += 1

        self.subject_lbl.set_text(self.current_card["subject"])
        self.tense_lbl.set_text(f"({self.current_card['tense']})")
        self.counter_lbl.configure(text=f"Cards: {self.cards_shown}")

        if self.auto_reveal:
            self._show_answer()
        else:
            self._hide_answer()

        self.play_beep()
        self._schedule_next_card()

    def _schedule_next_card(self):
        if not self.session_active:
            return
        bpm = self.bpm_slider.get()
        interval_ms = int((60.0 / bpm) * 1000)
        self._after_card = self.after(interval_ms, self._next_card)

    # ========================= Editor ======================================
    def open_editor(self):
        """Open the data-editing modal."""
        was_running = self.session_active
        if was_running:
            self.stop_session()

        editor = DataEditor(self, self.subjects, self._on_editor_save)
        editor.grab_set()

    def _on_editor_save(self, new_data: list[dict]):
        self.subjects = new_data
        self.save_data()
        self.load_data()

    # ========================= Keyboard ==================================
    def bind_keyboard_shortcuts(self):
        self.bind("<space>", lambda e: self.toggle_session())
        self.bind("<m>", lambda e: self.aud_sw.toggle())
        self.bind("<r>", lambda e: self._manual_reveal())
        self.bind("<Escape>", lambda e: self.stop_session() if self.session_active else None)


# ---------------------------------------------------------------------------
# Data Editor (Modal Toplevel)
# ---------------------------------------------------------------------------
class DataEditor(ctk.CTkToplevel):
    """Simple scrollable editor for the subjects.json records."""

    def __init__(self, parent, data: list[dict], on_save_callback):
        super().__init__(parent)
        self.on_save = on_save_callback
        self.title("Edit Training Data")
        self.geometry("720x520")
        self.minsize(650, 400)
        self.configure(fg_color=GrammarReflexTrainer.BG_COLOR)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # Scrollable list
        scroll = ctk.CTkScrollableFrame(self, fg_color=GrammarReflexTrainer.CARD_BG)
        scroll.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        scroll.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Header row
        ctk.CTkLabel(scroll, text="Subject", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=6, pady=6
        )
        ctk.CTkLabel(scroll, text="Tense", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=1, padx=6, pady=6
        )
        ctk.CTkLabel(scroll, text="Answer", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=2, padx=6, pady=6
        )
        ctk.CTkLabel(scroll, text="Del", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=3, padx=6, pady=6
        )

        self.rows: list[tuple[ctk.CTkEntry, ctk.CTkEntry, ctk.CTkEntry, ctk.BooleanVar]] = []

        for idx, item in enumerate(data, start=1):
            self._add_row(scroll, idx, item)

        self.scroll_frame = scroll  # keep ref for dynamic adding
        self.next_row_idx = len(data) + 1

        # Bottom buttons
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        btn_bar.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            btn_bar, text="+ Add Row", command=self._add_empty_row
        ).grid(row=0, column=0, padx=6)
        ctk.CTkButton(
            btn_bar,
            text="Save Changes",
            fg_color="#10b981",
            hover_color="#059669",
            command=self._save,
        ).grid(row=0, column=1, padx=6)
        ctk.CTkButton(
            btn_bar,
            text="Cancel",
            fg_color="#6b7280",
            hover_color="#4b5563",
            command=self.destroy,
        ).grid(row=0, column=2, padx=6)

    def _add_row(self, parent, row_idx: int, item: dict):
        subj = ctk.CTkEntry(parent, placeholder_text="e.g. The cat")
        subj.insert(0, item.get("subject", ""))
        subj.grid(row=row_idx, column=0, padx=6, pady=3, sticky="ew")

        tense = ctk.CTkEntry(parent, placeholder_text="Present / Past")
        tense.insert(0, item.get("tense", ""))
        tense.grid(row=row_idx, column=1, padx=6, pady=3, sticky="ew")

        ans = ctk.CTkEntry(parent, placeholder_text="e.g. is")
        ans.insert(0, item.get("answer", ""))
        ans.grid(row=row_idx, column=2, padx=6, pady=3, sticky="ew")

        del_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(parent, text="", variable=del_var, width=20).grid(
            row=row_idx, column=3, padx=6, pady=3
        )

        self.rows.append((subj, tense, ans, del_var))

    def _add_empty_row(self):
        self._add_row(self.scroll_frame, self.next_row_idx, {"subject": "", "tense": "", "answer": ""})
        self.next_row_idx += 1

    def _save(self):
        new_data = []
        for subj_e, tense_e, ans_e, del_var in self.rows:
            if del_var.get():
                continue
            s = subj_e.get().strip()
            t = tense_e.get().strip()
            a = ans_e.get().strip()
            if s and t and a:
                new_data.append({"subject": s, "tense": t, "answer": a})

        self.on_save(new_data)
        self.destroy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = GrammarReflexTrainer()
    app.mainloop()
