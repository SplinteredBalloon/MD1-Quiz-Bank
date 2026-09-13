#!/usr/bin/env python3
"""
CSV Quiz Player
A standalone Tkinter quiz reader with resumable attempts.

Recommended CSV format:
    Question,Answer 1,Answer 2,Answer 3,Answer 4,Correct,Image
    What is 2 + 2?,3,4,5,6,2,math-example.png

Optional explanation-enabled format:
    Question,Answer 1,Answer 2,Answer 3,Answer 4,Correct,Image,Explanation
The Explanation field is short per-question rationale text. It is ignored unless
present in the CSV and is displayed only after that question is answered wrong.

The optional Image value is a filename or relative path resolved from the
folder containing the CSV file. Leave it blank for questions without images.
Image display is disabled by default and can be enabled from the gear menu.
Question and answer randomization are disabled by default. When enabled, the
program randomizes question order and/or answer order without changing the CSV
file. Saved progress stores the exact active question and answer patterns.
Program options are stored in config.json beside this PYW file. V16.1 also
supports an optional per-question timer. The timer is mutually exclusive with
Free Question Navigation. Timed quizzes wait for Start Quiz / Continue before
counting down, can be paused, and automatically mark expired questions wrong
without revealing the correct answer. Its enabled state, duration value, and
seconds/minutes unit are stored in config.json.

The Correct value may be:
- one 1-based answer number, such as 2
- multiple 1-based answer numbers separated by commas, such as "1,3,5"
- the exact answer text, such as 4
- an answer-column header, such as Answer 2

Questions with multiple Correct numbers automatically become multi-select
questions. Every correct choice, and no incorrect choice, must be selected for
the response to count as correct.

Alternative:
- Omit the Correct column and place * at the start of the correct answer.
- If neither method is used, the first answer is treated as correct.
"""

from __future__ import annotations

import csv
import json
import re
import random
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable, Optional

try:
    from PIL import Image, ImageTk
except ImportError:  # The app still supports Tk-compatible PNG/GIF images.
    Image = None
    ImageTk = None


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
DEFAULT_CONFIG = {
    "image_display": False,
    "free_question_navigation": False,
    "randomize_questions": False,
    "randomize_answers": False,
    "timer_enabled": False,
    "timer_value": 30,
    "timer_unit": "s",
    "show_correct_after_wrong": False,
}
QUESTION_HEADER_NAMES = {"question", "prompt", "quiz question"}
CORRECT_HEADER_NAMES = {
    "correct", "correct answer", "correct_answer", "answer key",
    "answer_key", "key"
}
IMAGE_HEADER_NAMES = {
    "image", "image file", "image filename", "image path", "picture",
    "picture file", "picture path", "illustration"
}
EXPLANATION_HEADER_NAMES = {
    "explanation", "answer explanation", "correct answer explanation",
    "why correct", "why the correct answer is correct", "rationale"
}
TOOLBAR_ICON_SAVE_PNG = """iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAYAAADEtGw7AAABzklEQVR42rVVsY4TMRB987zeXIqARJ0yHR8AoklHcwVHgUSFxCfxEychIaq7nlQU194JiRKRrVAKgtCi2Ds048i38S6hyEgjW+uZN+M341nglOKce0+yIfmd5DeSTV3Xr9JxbltV1RPn3IvJZLKo6/rC/NYkrxaLxeQeMMkfADRXkm8Tlq1itjcAVETe1XV9Yfad+Xycz+dTAKA5tZnBLtuXJORgpgFA7LruZdM0H/rZSGFfEu2tyZ4W7GmecUlogfe6XC4rAFMDOiv4E8DvPOMDEZGtXTGkb6vVCs65LyLyUES+isivgYSKwASAruvOvfcPVNWLSNzzoHrjnLsF8CeE8Dr3OUQi14WC/K+mzliPUaEAYlageyxlNmJ9flDsIWAZ4/8YqQqZCoAgIhvb60hwVdVHhqN55iVgeO/fzGaz6xijc87FEmo6226357vd7rKfQDXA391ms/l5zJW993c932GOVXWaFSYOzS4A0WxxbPH6bTfUOYMzhacaxWMt5fqzuHD+T+D8WuK9lxBCHOEX6cx7ryGEvW+iJgGf5Y+ibdtLEbk1qsb6uGvb9nHvQU1z4E8kn6Wo1vTPRWSUR1UFgJZkYwkQwOeT/kf/AnSRsy7kt0KQAAAAAElFTkSuQmCC"""
TOOLBAR_ICON_EYE_PNG = """iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAYAAADEtGw7AAAB8UlEQVR42u1TPYsTURS959z7JjPDzoyJpBCTQhCL2AhLEPIzFuNHIdiICquFv0Gw30IIsv9AKxG0E4S1CqxFdCWl4m7j57K4IYFn82YdY0RbZS88mJl77pl77nlX5DD+m2D50Gg0jpvZKslHAD4A8OF8JPnYzG4lSdJaVDsfKiLSbDaXVPUOgB0R8QC8mb10zq0559ZUdROAD7kdVb3baDTyKscvpGmaniE5EhEvIl5Vd/M8vzAPjqJoBcDnEkdyK03T5YXkaZouA/gUwPsAfJZll0VEzOwGySHJoZmtBvJ+6Hw/dP8lSZKz86THALwLpBMR8WY2EhEheaWUXo6mVqtdD7nNag2A7Xq93v4xdfJZAMxEZBqI1733ALARvk/Cmanq0HsPVb0X6qYB40luVJ38Oj9H7305q1nAlV2D5DTkbMH8dw9eiqI4QnKrKovkuGKUrxjl8zy/FJS+Kj0JKsfdbvfoT3/KsuwUybdV80qjkiRZcc49cc49LYrinIiIc+7qHOl2u90+vfC6FUVxguTziuxJSV4NM7sG4FtpZhRFL1qt1snf3WWKiPT7fTWzmyTfVBbhPYCHAB6UtycoGmdZdnswGLg/bd9BotPpLMVxfN7M7qvqyMz2zGxPVV/Hcbye5/nFXq+X/c1KH8Y/Ft8Bo1GNc1eICbwAAAAASUVORK5CYII="""
TOOLBAR_ICON_EYE_OFF_PNG = """iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAYAAADEtGw7AAACzklEQVR42u2VTYgURxTH/++9etVV3dN0yzojA9kF1wRyWRbZi0FxIuhBwyYGHU96CJsEclAvi6AXEcGoiAoh5GQuueiAASEgXkUvifiBIOaikQX1EKKXDU62eyqXHmk/Rjx58kFBdX386/devVcNvLe6NZvNhjHmonNuXTVkANBbbB25TgAgyzKzuLi4viiKU6r612AwuAEA3W5XFhYWPgKwhpk3iMhqVW0lSYJ+v/8PgEFNJ4w+3pjviKgUkdMTExMrReQmEQUiCswcmDnUvv8wxsxnWZbXIV82qtxCmqazzHyPma865+ZV9dckSXZMT0/nk5OTLefcTma+WxEGZr7vvd8+SlwAQER+IqL7cRzPMfMFInqQ5/l0NTdrjPkEANrtdszMVwAsAQhEFFT1UC3uNWWRE0MKAKVzbp+qHgcQnHP7rbW/VCH4vdlsNqIo+pCIngEoACwRUbDWHnhBVFW/qgSXAPQBBFW9BADOuV1E9ERVf/Te7wEQjDFnAICZL9f2FZX45wDAAFCW5ZHqhrlqgZlvdTodUxTFJufc/rIs1/b7/a3e+90iIp1OxxDRvTpgCCEMBoPDzweiKPqaiIYnL1VU5yuqSwCexXE8JyJniehRmqZbAICIrldA/wEomDnkef7FyzE+WbnVB1Ay89N2u708juO2iPxJRME5d0pVj1Uuz6vq0eG9EFFoNBoHRmXFDxV5AFAaY34LIRAAJEnyaRzHm6v+Rmb+2xjzs/d+NzM/9N5//7qsoGG8oyiaY+bHtTy9Zq39MsuyZVmW5aq6U0TOWWv3MvMdZr6R5/n6YR6MKj4BgFartcJae1BEbg8rrd6YOVhrL09NTX0gIueI6F9r7bYa5GhxAOj1ejI2Nvax9342iqJvoyj6Jk3Tz8bHx1f1ej2pPQXzRBRE5NjMzIy+6dWiVypo9DoBAGvtNmvtxW63a9//L96N/Q99k7WwA1/ikwAAAABJRU5ErkJggg=="""
TOOLBAR_ICON_GEAR_PNG = """iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAYAAADEtGw7AAACqklEQVR42r1Vv2sUQRT+3o+d3b3NWuydJhzkkBiwimBxJIVYWAUsBBHEQvAfSJtOFguFFCIiiIhiEwicgpJC7NKYVIIRKwsLQYSoSPSEGMnd2Myuk80lxkIfDAyz730z773vfQv8R2MABEAAGAAkIleZeY2ZP4VheMP5Bc6HXMyeRgMPiT4AsACsiHyZmZkJ9xtbvBSqOsvMK8aYc3Ect0Vk3oH2APSIyKrqwziOp4wxZ5j5uape9jF2pK+qs0Rki9d5+15lWSIqvxORNcbkeZ5zFZzzPGdmfg2gD2CzAHB7W1mbzq8H4CeAXhRFb5eWlrRaEgVAxpizXkDxUhsEwWYURathGL4UkQ3/G4AtZu6PjIxc9LBKMwCQJMkxItoqwInIpmk6PzExcbRwHB0dPaKq9/wSMXM/y7IpH6u04eHhREQWXMAPADZN04VK18s0ReS+X6ogCJ6Mj48f2AYqIteI6J1z7APoq+rG5OTkYQemlbJxkiSHiOibXxYieu/xHGDmbqX7Noqi1T34yS5uuahzEWeM6ZUO1todkdba/j6m1A6I+31Wq9VuqupHPy1m/l6v15vucr8UAoDTNK0T0XoR47j8Ocuyu9tuarfbdVV95DdPVR9U0mevL7f95qVp+mx6evpgNYPAvfy4o1tZaxG5G0VRq3CM47gpIreqdBsbGzsxiG7qVOy0D+p1u8vMK8y8TERfqwNCRP0kSc4PYBDYWkvMvOqN9Ja3/+NIq+qbTqcjVRaxG+ncFyBm9kVoy6cVM5cixMw2y7I5ay3vpnAIguBKHMevms3mpUajcTIMw8cOoJTNoaGhp61W61SSJBeMMS8ajcbcoOncU6w7nY4Q0VqRSRAE64uLi7W/EXpUxFqLX1MYhteNMV1jTDfLsjte93U3gf9n9gutr+nfuxUSRAAAAABJRU5ErkJggg=="""
TOOLBAR_ICON_RESET_PNG = """iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAYAAADEtGw7AAABq0lEQVR42tXVzYuNYRgG8N9552AlK1aTJKHkY4EyFrLQREopjeysbaz8ATb+ABtlpYiyEStjyYJSNCVNEc3Y+JgFcxZTzDk211vvPOa8cyznqafn6f643ut+7o+X9b7GGvdJ3MEsFtHDB9zHuSE+raC78QSDNfYz7F8LvMo5ge8N56e4ijOJ4Erx0V+RDwXvYAcW4vAJp1uiO4n3se1hX0FwxXocwznsbLDo5mzeYRwf4/Miug0l6An0s2umG1sY1wAHwniAU5F1m4a3o3w+Yqa7OIRjeBdCM3iEW03DmQBfy3t3W0CrML4Xnz8BrhM60TT+FuH51cJZJdGdPNV0/JZy3iiNv0ZxYQTgZvY341V857Gl1tUGX3LuGbFD+/FdxNlUx3X8LEvuZr76etQ2LXKxDZsiW7GO4HfAL41QbmP/M4DuBvgHjhasmrtmdRAP0kzVsK6rEs7ngC/g8hBmHUwlLwO8yTNUpVEN3MfeDJldkb/NIJrFcibfJA5HP4eLeBmsflsJbU0n9lpG5lIaZLwg+A9jBXNp2Skcx/bYzofdw9Rvncjldf+L8xfhpXEX/fzgagAAAABJRU5ErkJggg=="""
ANSWER_HIDE_FILL = "#d9d9d9"
ANSWER_HIDE_DOT = "#c7c7c7"
DEFAULT_ANSWER_BORDER = "#555555"
CORRECT_ANSWER_BORDER = "#21a642"
WRONG_ANSWER_BORDER = "#c92b2b"
# Very restrained feedback fills: close to neutral gray, with only a slight tint.
CORRECT_ANSWER_FILL = "#e1e5e2"
WRONG_ANSWER_FILL = "#e5e1e1"
# A revealed correct answer keeps the normal answer border and is marked with a check.


@dataclass
class QuizQuestion:
    prompt: str
    answers: list[str]
    correct_indices: list[int]
    image_path: Optional[Path] = None
    explanation: str = ""

    @property
    def is_multi_select(self) -> bool:
        return len(self.correct_indices) > 1


class AttemptChoiceDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        csv_name: str,
        progress_files: list[Path],
    ) -> None:
        super().__init__(parent)
        self.result: Optional[str] = None
        self.progress_files = progress_files

        self.title("Saved quiz progress found")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        outer = tk.Frame(self, padx=18, pady=16)
        outer.pack(fill="both", expand=True)

        if len(progress_files) == 1:
            text = (
                f'A saved attempt for "{csv_name}" has been found.\n\n'
                "Would you like to continue that attempt or start a new one?"
            )
        else:
            names = "\n".join(f"• {p.name}" for p in progress_files)
            text = (
                f'Multiple saved attempts for "{csv_name}" were found:\n\n'
                f"{names}\n\n"
                "Browse for the attempt you want to continue, or start a new attempt."
            )

        tk.Label(
            outer,
            text=text,
            justify="left",
            anchor="w",
            wraplength=520,
        ).pack(fill="x")

        buttons = tk.Frame(outer)
        buttons.pack(fill="x", pady=(18, 0))

        tk.Button(
            buttons,
            text="Start New Attempt",
            command=lambda: self._finish("new"),
            padx=12,
            pady=6,
        ).pack(side="left")

        right_text = "Continue Old Quiz" if len(progress_files) == 1 else "Browse"
        tk.Button(
            buttons,
            text=right_text,
            command=lambda: self._finish("continue" if len(progress_files) == 1 else "browse"),
            padx=12,
            pady=6,
        ).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", lambda: self._finish("cancel"))
        self.update_idletasks()
        self._center_over_parent(parent)

    def _center_over_parent(self, parent: tk.Misc) -> None:
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - self.winfo_width()) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - self.winfo_height()) // 2)
        self.geometry(f"+{x}+{y}")

    def _finish(self, result: str) -> None:
        self.result = result
        self.destroy()

    def show(self) -> Optional[str]:
        self.wait_window()
        return self.result


class OptionsDialog(tk.Toplevel):
    OPTIONS = (
        ("Image Display", "image_display"),
        ("Free Question Navigation", "free_question_navigation"),
        ("Randomize Questions", "randomize_questions"),
        ("Randomize Answers", "randomize_answers"),
        ("Show Correct Answer After Wrong", "show_correct_after_wrong"),
        ("Timer (per question)", "timer_enabled"),
    )

    def __init__(
        self,
        parent: tk.Misc,
        settings: dict[str, Any],
        on_change: Callable[[str, Any], bool],
        on_reset: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.settings = settings
        self.on_change = on_change
        self.on_reset = on_reset

        self.title("Options")
        self.geometry("475x365")
        self.minsize(410, 250)
        self.transient(parent)

        outer = tk.Frame(self, padx=14, pady=14)
        outer.pack(fill="both", expand=True)

        header_row = tk.Frame(outer)
        header_row.pack(fill="x", pady=(0, 8))

        tk.Label(
            header_row,
            text="Double-click an option to change it.",
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        self.option_list = tk.Listbox(
            outer,
            activestyle="dotbox",
            font=("TkDefaultFont", 11),
            height=8,
        )
        self.option_list.pack(fill="both", expand=True)
        self.option_list.bind("<Double-Button-1>", self._edit_selected)
        self.option_list.bind("<Return>", self._edit_selected)

        close_button = tk.Button(
            outer,
            text="Close",
            command=self.destroy,
            padx=14,
            pady=5,
        )
        close_button.pack(side="right", pady=(10, 0))

        self._refresh_list()
        self.option_list.selection_set(0)
        self.option_list.activate(0)
        self.after_idle(lambda: self.option_list.focus_set())
        self.update_idletasks()
        self._center_over_parent(parent)

    def _center_over_parent(self, parent: tk.Misc) -> None:
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - self.winfo_width()) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - self.winfo_height()) // 2)
        self.geometry(f"+{x}+{y}")

    def _refresh_list(self) -> None:
        selected = self.option_list.curselection()
        selected_index = selected[0] if selected else 0
        self.option_list.delete(0, "end")
        for title, key in self.OPTIONS:
            state = "Enabled" if self.settings.get(key, False) else "Disabled"
            if key == "timer_enabled":
                value = self.settings.get("timer_value", 30)
                unit = self.settings.get("timer_unit", "s")
                self.option_list.insert("end", f"{title}    —    {state} ({value} {unit})")
            else:
                self.option_list.insert("end", f"{title}    —    {state}")
        if self.OPTIONS:
            selected_index = min(selected_index, len(self.OPTIONS) - 1)
            self.option_list.selection_set(selected_index)
            self.option_list.activate(selected_index)

    def _edit_selected(self, _event: Optional[tk.Event] = None) -> str:
        selected = self.option_list.curselection()
        if not selected:
            return "break"

        title, key = self.OPTIONS[selected[0]]
        if key == "timer_enabled":
            self._edit_timer(title)
            return "break"

        current = bool(self.settings.get(key, False))
        chooser = tk.Toplevel(self)
        chooser.title(title)
        chooser.resizable(False, False)
        chooser.transient(self)
        chooser.grab_set()

        outer = tk.Frame(chooser, padx=18, pady=16)
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text=title,
            font=("TkDefaultFont", 11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        def choose(value: bool) -> None:
            if self.on_change(key, value):
                self.settings[key] = value
                self._refresh_list()
                chooser.destroy()

        tk.Button(
            outer,
            text=("✓  Enable" if current else "   Enable"),
            anchor="w",
            width=22,
            command=lambda: choose(True),
            padx=10,
            pady=7,
        ).pack(fill="x", pady=3)

        tk.Button(
            outer,
            text=("   Disable" if current else "✓  Disable"),
            anchor="w",
            width=22,
            command=lambda: choose(False),
            padx=10,
            pady=7,
        ).pack(fill="x", pady=3)

        chooser.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - chooser.winfo_width()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - chooser.winfo_height()) // 2)
        chooser.geometry(f"+{x}+{y}")

    def _edit_timer(self, title: str) -> None:
        chooser = tk.Toplevel(self)
        chooser.title(title)
        chooser.resizable(False, False)
        chooser.transient(self)
        chooser.grab_set()

        outer = tk.Frame(chooser, padx=18, pady=16)
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text=title,
            font=("TkDefaultFont", 11, "bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        value_var = tk.StringVar(value=str(self.settings.get("timer_value", 30)))
        enabled_var = tk.BooleanVar(value=bool(self.settings.get("timer_enabled", False)))
        unit_var = tk.StringVar(value=str(self.settings.get("timer_unit", "s")))

        enable_button = tk.Button(outer, anchor="w", width=17, padx=10, pady=7)
        disable_button = tk.Button(outer, anchor="w", width=17, padx=10, pady=7)
        value_entry = tk.Entry(outer, textvariable=value_var, width=9, justify="center")
        unit_frame = tk.Frame(outer)
        second_button = tk.Button(unit_frame, text="s", width=4, pady=4)
        minute_button = tk.Button(unit_frame, text="m", width=4, pady=4)
        second_button.pack(side="left", padx=(0, 4))
        minute_button.pack(side="left")

        enable_button.grid(row=1, column=0, sticky="ew", pady=3)
        value_entry.grid(row=1, column=1, sticky="e", padx=(12, 0), pady=3)
        disable_button.grid(row=2, column=0, sticky="ew", pady=3)
        unit_frame.grid(row=2, column=1, sticky="e", padx=(12, 0), pady=3)

        def refresh_controls() -> None:
            enabled = enabled_var.get()
            enable_button.config(text=("✓  Enable" if enabled else "   Enable"))
            disable_button.config(text=("   Disable" if enabled else "✓  Disable"))
            field_state = "normal" if enabled else "disabled"
            value_entry.config(state=field_state)
            second_button.config(
                state=field_state,
                text=("✓ s" if unit_var.get() == "s" else "s"),
            )
            minute_button.config(
                state=field_state,
                text=("✓ m" if unit_var.get() == "m" else "m"),
            )

        def commit_value(show_error: bool = True) -> bool:
            raw = value_var.get().strip()
            try:
                value = int(raw)
            except ValueError:
                value = 0
            if value <= 0:
                if show_error:
                    messagebox.showwarning(
                        "Invalid timer value",
                        "Enter a positive whole number for the timer.",
                        parent=chooser,
                    )
                return False
            if self.on_change("timer_value", value):
                self.settings["timer_value"] = value
                value_var.set(str(value))
                self._refresh_list()
                return True
            return False

        def choose_enabled(value: bool) -> None:
            if value and not commit_value(show_error=True):
                return
            if self.on_change("timer_enabled", value):
                self.settings["timer_enabled"] = value
                enabled_var.set(value)
                self._refresh_list()
                refresh_controls()

        def choose_unit(unit: str) -> None:
            if not enabled_var.get():
                return
            if self.on_change("timer_unit", unit):
                self.settings["timer_unit"] = unit
                unit_var.set(unit)
                self._refresh_list()
                refresh_controls()

        enable_button.config(command=lambda: choose_enabled(True))
        disable_button.config(command=lambda: choose_enabled(False))
        second_button.config(command=lambda: choose_unit("s"))
        minute_button.config(command=lambda: choose_unit("m"))
        value_entry.bind("<Return>", lambda _e: commit_value(show_error=True))
        value_entry.bind("<FocusOut>", lambda _e: commit_value(show_error=False) if enabled_var.get() else None)

        tk.Button(
            outer,
            text="Close",
            command=lambda: (commit_value(show_error=False) if enabled_var.get() else None, chooser.destroy()),
            padx=12,
            pady=5,
        ).grid(row=3, column=1, sticky="e", pady=(12, 0))

        refresh_controls()
        chooser.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - chooser.winfo_width()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - chooser.winfo_height()) // 2)
        chooser.geometry(f"+{x}+{y}")


class ResetAttemptConfirmationDialog(tk.Toplevel):
    """Confirm before clearing the current quiz attempt."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.result = False
        self.title("Reset Quiz")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        outer = tk.Frame(self, padx=20, pady=18)
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text=(
                "Are you sure you want to reset this attempt?\n\n"
                "All answers and your current quiz position will be cleared."
            ),
            justify="left",
            anchor="w",
            wraplength=430,
        ).pack(fill="x")

        buttons = tk.Frame(outer)
        buttons.pack(fill="x", pady=(18, 0))

        tk.Button(
            buttons,
            text="Cancel",
            command=lambda: self._finish(False),
            padx=14,
            pady=6,
        ).pack(side="left")

        tk.Button(
            buttons,
            text="Reset",
            command=lambda: self._finish(True),
            padx=14,
            pady=6,
        ).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", lambda: self._finish(False))
        self.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - self.winfo_width()) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - self.winfo_height()) // 2)
        self.geometry(f"+{x}+{y}")

    def _finish(self, result: bool) -> None:
        self.result = result
        self.destroy()

    def show(self) -> bool:
        self.wait_window()
        return self.result


class ResetRandomizationDialog(tk.Toplevel):
    """Ask whether a reset should keep the current randomized quiz ordering."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.result: Optional[str] = None
        self.title("Reset Quiz")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        outer = tk.Frame(self, padx=20, pady=18)
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text=(
                "Randomization is enabled. Reset all quiz progress and keep "
                "the current question/answer organization, or restore the "
                "original CSV organization?"
            ),
            justify="left",
            anchor="w",
            wraplength=430,
        ).pack(fill="x")

        buttons = tk.Frame(outer)
        buttons.pack(fill="x", pady=(18, 0))

        tk.Button(
            buttons,
            text="Keep",
            command=lambda: self._finish("keep"),
            padx=14,
            pady=6,
        ).pack(side="left")

        tk.Button(
            buttons,
            text="Restore Default",
            command=lambda: self._finish("restore"),
            padx=14,
            pady=6,
        ).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", lambda: self._finish("cancel"))
        self.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - self.winfo_width()) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - self.winfo_height()) // 2)
        self.geometry(f"+{x}+{y}")

    def _finish(self, result: str) -> None:
        self.result = result
        self.destroy()

    def show(self) -> Optional[str]:
        self.wait_window()
        return self.result


class QuizApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CSV Quiz Player")
        self.geometry("920x680")
        self.minsize(720, 520)

        self.csv_path: Optional[Path] = None
        self.questions: list[QuizQuestion] = []
        # Display position -> original CSV question index. The CSV-backed question
        # list itself is never reordered or modified.
        self.question_order: list[int] = []
        # For each original CSV question index: displayed answer position ->
        # original CSV answer index. Answer text in self.questions is never reordered.
        self.answer_orders: list[list[int]] = []
        self.current_index = 0
        self.attempt_number = 1
        self.records: list[dict[str, Any]] = []
        self.selected_var = tk.IntVar(value=-1)
        self.multi_selected_vars: dict[int, tk.BooleanVar] = {}
        self.answer_rows: list[tk.Widget] = []
        self.answer_borders: list[tk.Frame] = []
        self.answer_check_labels: dict[int, tk.Label] = {}
        self.answer_option_widgets: dict[int, tuple[tk.Frame, tk.Frame, tk.Widget, tk.Label]] = {}
        self.overlay: Optional[tk.Toplevel] = None
        self.overlay_canvas: Optional[tk.Canvas] = None
        self.overlay_correct: Optional[bool] = None
        self.overlay_reposition_job: Optional[str] = None
        self.overlay_fade_job: Optional[str] = None
        self.overlay_alpha = 0.34
        self.navigator_visible = False
        self.navigator_buttons: list[tk.Button] = []
        self.current_image_path: Optional[Path] = None
        self.image_photo: Optional[Any] = None
        self._pil_source_image: Optional[Any] = None
        self._tk_source_image: Optional[tk.PhotoImage] = None
        self.image_resize_job: Optional[str] = None
        self.image_message = "No image for this question."
        self.config_data = self._load_config()
        self.image_display_enabled = bool(
            self.config_data.get("image_display", False)
        )
        self.free_question_navigation = bool(
            self.config_data.get("free_question_navigation", False)
        )
        self.randomization_enabled = bool(
            self.config_data.get("randomize_questions", False)
        )
        self.answer_randomization_enabled = bool(
            self.config_data.get("randomize_answers", False)
        )
        self.show_correct_after_wrong = bool(
            self.config_data.get("show_correct_after_wrong", False)
        )
        self.timer_enabled = bool(self.config_data.get("timer_enabled", False))
        self.timer_value = int(self.config_data.get("timer_value", 30))
        self.timer_unit = str(self.config_data.get("timer_unit", "s"))
        self.timer_job: Optional[str] = None
        self.timer_remaining_seconds = 0
        self.timer_question_id: Optional[int] = None
        # Timed mode has an explicit session gate. Enabling the option does not
        # start the clock until the user presses Start Quiz / Continue.
        self.timed_quiz_running = False
        self.timed_quiz_started = False
        self.timed_pause_reason = "ready"
        self.options_dialog: Optional[OptionsDialog] = None
        self.answers_hidden = False
        # Persistent eye-button cover mode. Clicking VIEW ANSWERS reveals only
        # the current question; the eye remains slashed and the next question
        # is covered again until the eye button itself disables the mode.
        self.temporarily_revealed_question_id: Optional[int] = None
        self.hide_answers_button: Optional[tk.Button] = None
        self.icon_save: Optional[tk.PhotoImage] = None
        self.icon_eye: Optional[tk.PhotoImage] = None
        self.icon_eye_off: Optional[tk.PhotoImage] = None
        self.icon_reset: Optional[tk.PhotoImage] = None
        self.icon_gear: Optional[tk.PhotoImage] = None

        self._load_toolbar_icons()
        self._build_ui()
        self._apply_image_display_layout()
        self._show_welcome()

    def _load_toolbar_icons(self) -> None:
        self.icon_save = tk.PhotoImage(data=TOOLBAR_ICON_SAVE_PNG)
        self.icon_eye = tk.PhotoImage(data=TOOLBAR_ICON_EYE_PNG)
        self.icon_eye_off = tk.PhotoImage(data=TOOLBAR_ICON_EYE_OFF_PNG)
        self.icon_reset = tk.PhotoImage(data=TOOLBAR_ICON_RESET_PNG)
        self.icon_gear = tk.PhotoImage(data=TOOLBAR_ICON_GEAR_PNG)

    def _build_ui(self) -> None:
        top = tk.Frame(self, padx=14, pady=12)
        top.pack(fill="x")

        self.navigator_toggle = tk.Button(
            top,
            text="☰",
            command=self.toggle_navigator,
            padx=12,
            pady=7,
        )
        self.navigator_toggle.pack(side="left", padx=(0, 8))

        tk.Button(
            top,
            text="Browse Quiz CSV",
            command=self.browse_csv,
            padx=12,
            pady=7,
        ).pack(side="left")

        self.title_label = tk.Label(
            top,
            text="No quiz loaded",
            font=("TkDefaultFont", 11, "bold"),
        )
        self.title_label.pack(side="left", padx=16)

        self.toolbar_button_row = tk.Frame(top)
        self.toolbar_button_row.pack(side="right")

        button_style = {
            "padx": 1,
            "pady": 1,
            "bd": 1,
            "highlightthickness": 0,
            "takefocus": 0,
            "cursor": "hand2",
        }

        self.hide_answers_button = tk.Button(
            self.toolbar_button_row,
            image=self.icon_eye,
            text="Eye",
            command=self.toggle_answer_visibility,
            **button_style,
        )
        self.hide_answers_button.pack(side="left", padx=(0, 4))
        self._update_answer_visibility_button()

        self.reset_button = tk.Button(
            self.toolbar_button_row,
            image=self.icon_reset,
            text="Reset",
            command=self.request_reset_quiz,
            **button_style,
        )
        self.reset_button.pack(side="left", padx=(0, 4))

        self.save_button = tk.Button(
            self.toolbar_button_row,
            image=self.icon_save,
            text="Save",
            command=self.save_progress,
            state="disabled",
            **button_style,
        )
        self.save_button.pack(side="left", padx=(0, 4))

        self.options_button = tk.Button(
            self.toolbar_button_row,
            image=self.icon_gear,
            text="Options",
            command=self.open_options,
            **button_style,
        )
        self.options_button.pack(side="left")

        tk.Frame(self, height=1, bg="#b8b8b8").pack(fill="x")

        self.body = tk.Frame(self)
        self.body.pack(fill="both", expand=True)

        self.navigator_panel = tk.Frame(
            self.body,
            width=235,
            bd=1,
            relief="solid",
            bg="#f1f1f1",
        )
        self.navigator_panel.pack_propagate(False)

        nav_header_row = tk.Frame(self.navigator_panel, bg="#f1f1f1")
        nav_header_row.pack(fill="x")

        nav_header = tk.Label(
            nav_header_row,
            text="Questions",
            anchor="w",
            font=("TkDefaultFont", 11, "bold"),
            bg="#f1f1f1",
            padx=10,
            pady=9,
        )
        nav_header.pack(side="left")

        self.nav_counter = tk.Text(
            nav_header_row,
            height=1,
            width=15,
            wrap="none",
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
            bg="#f1f1f1",
            font=("TkDefaultFont", 8),
            padx=0,
            pady=9,
            takefocus=0,
            cursor="arrow",
        )
        self.nav_counter.pack(side="left")
        self.nav_counter.tag_configure("normal", foreground="#222222")
        self.nav_counter.tag_configure("correct", foreground="#2f9e44")
        self.nav_counter.tag_configure("wrong", foreground="#c92b2b")
        self.nav_counter.config(state="disabled")

        nav_holder = tk.Frame(self.navigator_panel, bg="#f1f1f1")
        nav_holder.pack(fill="both", expand=True)

        self.navigator_canvas = tk.Canvas(
            nav_holder,
            bg="#f1f1f1",
            highlightthickness=0,
            bd=0,
        )
        self.navigator_canvas.pack(side="left", fill="both", expand=True)

        self.navigator_scrollbar = tk.Scrollbar(
            nav_holder,
            orient="vertical",
            command=self.navigator_canvas.yview,
            width=10,
        )
        self.navigator_scrollbar.pack(side="right", fill="y")
        self.navigator_canvas.configure(
            yscrollcommand=self.navigator_scrollbar.set
        )

        self.navigator_grid = tk.Frame(
            self.navigator_canvas,
            bg="#f1f1f1",
            padx=7,
            pady=7,
        )
        self.navigator_window = self.navigator_canvas.create_window(
            (0, 0),
            window=self.navigator_grid,
            anchor="nw",
        )
        self.navigator_grid.bind(
            "<Configure>",
            lambda _e: self.navigator_canvas.configure(
                scrollregion=self.navigator_canvas.bbox("all")
            ),
        )
        self.navigator_canvas.bind(
            "<Configure>",
            lambda e: self.navigator_canvas.itemconfigure(
                self.navigator_window,
                width=e.width,
            ),
        )
        self.navigator_canvas.bind("<MouseWheel>", self._scroll_navigator)
        self.navigator_grid.bind("<MouseWheel>", self._scroll_navigator)

        self.content = tk.Frame(self.body, padx=24, pady=20)
        self.content.pack(side="left", fill="both", expand=True)

        self.quiz_view = tk.Frame(self.content)
        self.quiz_view.pack(fill="both", expand=True)
        self.quiz_view.grid_rowconfigure(0, weight=1)
        self.quiz_view.grid_columnconfigure(0, weight=3)
        self.quiz_view.grid_columnconfigure(1, weight=2)

        self.question_area = tk.Frame(self.quiz_view)
        self.question_area.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 16),
        )

        self.question_header_row = tk.Frame(self.question_area)
        self.question_header_row.pack(fill="x")

        self.question_number_label = tk.Label(
            self.question_header_row,
            text="",
            anchor="w",
            fg="#555555",
        )
        self.question_number_label.pack(side="left")

        self.result_badge = tk.Label(
            self.question_header_row,
            text="",
            fg="white",
            font=("TkDefaultFont", 9, "bold"),
            padx=16,
            pady=3,
        )

        self.timer_label = tk.Label(
            self.question_header_row,
            text="",
            fg="#c92b2b",
            font=("TkDefaultFont", 12, "bold"),
            padx=8,
        )
        if self.timer_enabled:
            self.timer_label.pack(side="right")

        self.prompt_label = tk.Label(
            self.question_area,
            text="",
            justify="left",
            anchor="nw",
            wraplength=820,
            font=("TkDefaultFont", 16, "bold"),
            pady=10,
        )
        self.prompt_label.pack(fill="x")

        self.multi_answer_banner = tk.Label(
            self.question_area,
            text="MULTIPLE ANSWERS — Select all that apply",
            anchor="w",
            justify="left",
            font=("TkDefaultFont", 10, "bold"),
            fg="#7a4b00",
            bg="#fff3bf",
            bd=1,
            relief="solid",
            padx=10,
            pady=7,
        )

        self.answers_frame = tk.Frame(self.question_area)
        self.answers_frame.pack(fill="both", expand=True, pady=(6, 10))

        self.image_panel = tk.Frame(
            self.quiz_view,
            bd=1,
            relief="solid",
            bg="#f4f4f4",
        )
        self.image_panel.grid(row=0, column=1, sticky="nsew")

        tk.Label(
            self.image_panel,
            text="Question image",
            anchor="w",
            font=("TkDefaultFont", 11, "bold"),
            bg="#f4f4f4",
            padx=12,
            pady=10,
        ).pack(fill="x")

        self.image_canvas = tk.Canvas(
            self.image_panel,
            bg="#f4f4f4",
            width=1,
            height=1,
            highlightthickness=0,
            bd=0,
        )
        self.image_canvas.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.image_canvas.bind("<Configure>", self._on_image_panel_resize)

        # Explanation belongs to the question flow, directly below the answer choices,
        # rather than consuming a separate column on the right.
        self.explanation_panel = tk.Frame(
            self.question_area,
            bd=1,
            relief="solid",
            bg="#f4f4f4",
        )
        self.explanation_heading_label = tk.Label(
            self.explanation_panel,
            text="Correct Answer:",
            anchor="w",
            font=("TkDefaultFont", 11, "bold"),
            bg="#f4f4f4",
            padx=12,
            pady=4,
        )
        self.explanation_heading_label.pack(fill="x", pady=(4, 0))
        self.explanation_label = tk.Label(
            self.explanation_panel,
            text="",
            justify="left",
            anchor="nw",
            wraplength=700,
            bg="#f4f4f4",
            padx=12,
            pady=6,
        )
        self.explanation_label.pack(fill="x")

        self.explanation_title_label = tk.Label(
            self.explanation_panel,
            text="Explanation:",
            anchor="w",
            font=("TkDefaultFont", 11, "bold"),
            bg="#f4f4f4",
            padx=12,
            pady=4,
        )
        self.explanation_title_label.pack(fill="x", pady=(2, 0))

        self.explanation_body_label = tk.Label(
            self.explanation_panel,
            text="",
            justify="left",
            anchor="nw",
            wraplength=700,
            bg="#f4f4f4",
            padx=12,
            pady=6,
        )
        self.explanation_body_label.pack(fill="x", pady=(0, 4))

        bottom = tk.Frame(self.content)
        bottom.pack(fill="x", pady=(8, 0))
        # Reserve the action-button cluster first. The status area is deliberately
        # allowed to shrink to almost nothing so Submit / Next never disappear
        # while the main window is resized down to its minimum width.
        bottom.grid_columnconfigure(0, weight=1, minsize=0)
        bottom.grid_columnconfigure(1, weight=0)

        self.status_label = tk.Label(bottom, text="", anchor="w", width=1)
        self.status_label.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.button_cluster = tk.Frame(bottom)
        self.button_cluster.grid(row=0, column=1, sticky="e")
        button_cluster = self.button_cluster

        self.timer_action_button = tk.Button(
            button_cluster,
            text="Start Quiz",
            command=self.start_or_continue_timed_quiz,
            width=11,
            padx=8,
            pady=7,
        )

        self.pause_button = tk.Button(
            button_cluster,
            text="Pause",
            command=self.pause_timed_quiz,
            width=8,
            padx=8,
            pady=7,
        )

        self.submit_button = tk.Button(
            button_cluster,
            text="Submit",
            command=self.submit_answer,
            state="disabled",
            width=11,
            padx=8,
            pady=7,
        )
        self.submit_button.pack(side="left", padx=(0, 4))

        self.next_button = tk.Button(
            button_cluster,
            text="Next",
            command=self.next_question,
            state="disabled",
            width=11,
            padx=8,
            pady=7,
        )
        self.next_button.pack(side="left")

        self.bind("<Configure>", self._on_resize)
        self.bind("<Unmap>", self._on_window_unmap)
        self.bind("<Map>", self._on_window_map)

    def _load_config(self) -> dict[str, Any]:
        config: dict[str, Any] = dict(DEFAULT_CONFIG)
        if CONFIG_PATH.is_file():
            try:
                loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    for key in (
                        "image_display",
                        "free_question_navigation",
                        "randomize_questions",
                        "randomize_answers",
                        "show_correct_after_wrong",
                        "timer_enabled",
                    ):
                        if isinstance(loaded.get(key), bool):
                            config[key] = loaded[key]
                    timer_value = loaded.get("timer_value")
                    if isinstance(timer_value, int) and timer_value > 0:
                        config["timer_value"] = timer_value
                    timer_unit = loaded.get("timer_unit")
                    if timer_unit in ("s", "m"):
                        config["timer_unit"] = timer_unit
            except (OSError, json.JSONDecodeError):
                pass

        # Timer and free navigation cannot be active simultaneously. Prefer the
        # timer if an externally edited config file enables both.
        if config["timer_enabled"] and config["free_question_navigation"]:
            config["free_question_navigation"] = False

        try:
            CONFIG_PATH.write_text(
                json.dumps(config, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
        return config

    def _save_config(self) -> None:
        self.config_data["image_display"] = self.image_display_enabled
        self.config_data["free_question_navigation"] = self.free_question_navigation
        self.config_data["randomize_questions"] = self.randomization_enabled
        self.config_data["randomize_answers"] = self.answer_randomization_enabled
        self.config_data["show_correct_after_wrong"] = self.show_correct_after_wrong
        self.config_data["timer_enabled"] = self.timer_enabled
        self.config_data["timer_value"] = self.timer_value
        self.config_data["timer_unit"] = self.timer_unit
        try:
            CONFIG_PATH.write_text(
                json.dumps(self.config_data, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            messagebox.showerror(
                "Could not save options",
                f"{exc}\n\nThe program folder may not be writable.",
                parent=self,
            )

    def open_options(self) -> None:
        if self.timer_enabled and self.questions and self.timed_quiz_running:
            self._pause_timed_quiz_internal("options")

        if self.options_dialog is not None:
            try:
                if self.options_dialog.winfo_exists():
                    self.options_dialog.deiconify()
                    self.options_dialog.lift()
                    self.options_dialog.focus_force()
                    return
            except tk.TclError:
                pass

        self.options_dialog = OptionsDialog(
            self,
            self.config_data,
            self._option_changed,
            self.reset_quiz_from_options,
        )
        self.options_dialog.bind(
            "<Destroy>",
            lambda event: self._options_dialog_destroyed(event),
        )

    def _options_dialog_destroyed(self, event: tk.Event) -> None:
        if event.widget is self.options_dialog:
            self.options_dialog = None
            if self.timer_enabled and self.questions and not self.timed_quiz_running:
                self._refresh_timer_session_controls()
                if self.timed_quiz_started:
                    self.status_label.config(text="Timed quiz paused. Choose Continue to resume.")

    def _option_changed(self, key: str, value: Any) -> bool:
        if key == "image_display":
            self.image_display_enabled = bool(value)
            self._apply_image_display_layout()
        elif key == "free_question_navigation":
            requested = bool(value)
            if requested and self.timer_enabled:
                messagebox.showwarning(
                    "Free Question Navigation unavailable",
                    "Disable Timer (per question) before enabling Free Question Navigation.",
                    parent=self.options_dialog or self,
                )
                return False
            self.free_question_navigation = requested
            self._enforce_navigation_mode()
            self._refresh_navigator()
        elif key == "randomize_questions":
            requested = bool(value)
            if requested != self.randomization_enabled:
                self._set_question_randomization(requested)
        elif key == "randomize_answers":
            requested = bool(value)
            if requested != self.answer_randomization_enabled:
                self._set_answer_randomization(requested)
        elif key == "show_correct_after_wrong":
            self.show_correct_after_wrong = bool(value)
            if self.questions:
                self._display_question()
        elif key == "timer_enabled":
            requested = bool(value)
            if requested and self.free_question_navigation:
                messagebox.showwarning(
                    "Timer unavailable",
                    "Disable Free Question Navigation before enabling Timer (per question).",
                    parent=self.options_dialog or self,
                )
                return False
            self.timer_enabled = requested
            if requested:
                if not self.timer_label.winfo_manager():
                    self.timer_label.pack(side="right")
                self._enforce_navigation_mode(redisplay=False)
                # Enabling timed mode only arms the quiz. It never starts the
                # clock by itself.
                self.timed_quiz_running = False
                self.timed_quiz_started = any(
                    record.get("submitted") for record in self.records
                ) if self.records else False
                self.timed_pause_reason = "ready"
                self._restart_timer_for_current_question()
                self._refresh_timer_session_controls()
                if self.questions:
                    self._display_question()
            else:
                self.timed_quiz_running = False
                self.timed_quiz_started = False
                self.timed_pause_reason = "ready"
                self._stop_timer(clear=True)
                self.timer_label.pack_forget()
                self._refresh_timer_session_controls()
                # Once the timed-session restriction is gone, any option that is
                # currently disabled may return fully to its normal default map.
                if self.questions:
                    current_question_id = self._current_question_id()
                    if not self.randomization_enabled:
                        self.question_order = list(range(len(self.questions)))
                        try:
                            self.current_index = self.question_order.index(current_question_id)
                        except ValueError:
                            self.current_index = 0
                    if not self.answer_randomization_enabled:
                        self.answer_orders = self._default_answer_orders()
                    self._build_navigator()
                    self._display_question()
        elif key == "timer_value":
            if not isinstance(value, int) or value <= 0:
                return False
            self.timer_value = value
            if self.timer_enabled:
                self._restart_timer_for_current_question()
        elif key == "timer_unit":
            if value not in ("s", "m"):
                return False
            self.timer_unit = str(value)
            if self.timer_enabled:
                self._restart_timer_for_current_question()
        else:
            return False

        self._save_config()
        return True

    def _question_id_at(self, display_index: int) -> int:
        if self.question_order and 0 <= display_index < len(self.question_order):
            return self.question_order[display_index]
        return display_index

    def _current_question_id(self) -> int:
        return self._question_id_at(self.current_index)

    def _timer_duration_seconds(self) -> int:
        multiplier = 60 if self.timer_unit == "m" else 1
        return max(1, int(self.timer_value) * multiplier)

    @staticmethod
    def _format_timer(seconds: int) -> str:
        seconds = max(0, int(seconds))
        minutes, remainder = divmod(seconds, 60)
        return f"{minutes:02d}:{remainder:02d}"

    def _stop_timer(self, clear: bool = False) -> None:
        if self.timer_job is not None:
            try:
                self.after_cancel(self.timer_job)
            except tk.TclError:
                pass
            self.timer_job = None
        self.timer_question_id = None
        if clear:
            self.timer_remaining_seconds = 0
            try:
                self.timer_label.config(text="")
            except tk.TclError:
                pass

    def _pause_timer_job_preserve_time(self) -> None:
        if self.timer_job is not None:
            try:
                self.after_cancel(self.timer_job)
            except tk.TclError:
                pass
            self.timer_job = None

    def _timed_quiz_locked(self) -> bool:
        return bool(
            self.timer_enabled
            and self.questions
            and not self.timed_quiz_running
        )

    def _refresh_timer_session_controls(self) -> None:
        if not hasattr(self, "timer_action_button"):
            return
        if not self.timer_enabled or not self.questions:
            self.timer_action_button.pack_forget()
            self.pause_button.pack_forget()
            return

        # Rebuild the timed controls in one explicit order whenever state changes:
        # Start/Continue -> Pause -> Submit -> Next. Pause is therefore always
        # immediately to the left of Submit.
        self.timer_action_button.pack_forget()
        self.pause_button.pack_forget()

        if self.timed_quiz_running:
            self.pause_button.pack(
                side="left", padx=(0, 4), before=self.submit_button
            )
            self.pause_button.config(state="normal")
        else:
            label = "Continue" if self.timed_quiz_started else "Start Quiz"
            self.timer_action_button.config(text=label, state="normal")
            self.timer_action_button.pack(
                side="left", padx=(0, 4), before=self.submit_button
            )
            self.pause_button.pack(
                side="left", padx=(0, 4), before=self.submit_button
            )
            self.pause_button.config(state="disabled")

    def _apply_timed_quiz_gate(self) -> None:
        self._refresh_timer_session_controls()
        if not self._timed_quiz_locked():
            return
        self._set_answer_controls(False)
        self.submit_button.config(state="disabled")
        self.next_button.config(state="disabled")
        self._refresh_navigator()
        if self.timed_quiz_started:
            self.status_label.config(text="Quiz paused. Choose Continue to resume.")
        else:
            self.status_label.config(text="Timed quiz ready. Choose Start Quiz when you are ready.")

    def start_or_continue_timed_quiz(self) -> None:
        if not self.timer_enabled or not self.questions:
            return
        self.timed_quiz_started = True
        self.timed_quiz_running = True
        self.timed_pause_reason = ""

        question_id = self._current_question_id()
        record = self.records[question_id]
        if not record.get("submitted"):
            if self.timer_question_id != question_id or self.timer_remaining_seconds <= 0:
                self.timer_question_id = question_id
                self.timer_remaining_seconds = self._timer_duration_seconds()
                self.timer_label.config(text=self._format_timer(self.timer_remaining_seconds))
            self._pause_timer_job_preserve_time()
            self.timer_job = self.after(1000, self._timer_tick)
        else:
            self.timer_label.config(text="--:--")

        self._display_question()
        self._refresh_timer_session_controls()

    def _pause_timed_quiz_internal(self, reason: str) -> None:
        if not self.timer_enabled or not self.questions:
            return
        if self.timed_quiz_running:
            self._pause_timer_job_preserve_time()
        self.timed_quiz_running = False
        self.timed_quiz_started = True
        self.timed_pause_reason = reason
        self._apply_timed_quiz_gate()

    def pause_timed_quiz(self) -> None:
        if not self.timer_enabled or not self.questions or not self.timed_quiz_running:
            return
        self._pause_timed_quiz_internal("manual")

    def _restart_timer_for_current_question(self) -> None:
        if not self.timer_enabled or not self.questions or not self.records:
            return
        question_id = self._current_question_id()
        if self.records[question_id].get("submitted"):
            self._stop_timer(clear=False)
            self.timer_label.config(text="--:--")
            return
        self._stop_timer(clear=False)
        self.timer_question_id = question_id
        self.timer_remaining_seconds = self._timer_duration_seconds()
        self.timer_label.config(text=self._format_timer(self.timer_remaining_seconds))
        if self.timed_quiz_running:
            self.timer_job = self.after(1000, self._timer_tick)

    def _sync_timer_for_display(self) -> None:
        if not self.timer_enabled:
            return
        if not self.timer_label.winfo_manager():
            self.timer_label.pack(side="right")
        if not self.questions or not self.records:
            self.timer_label.config(text=self._format_timer(self._timer_duration_seconds()))
            return
        question_id = self._current_question_id()
        if self.records[question_id].get("submitted"):
            self._stop_timer(clear=False)
            self.timer_label.config(text="--:--")
            return

        if not self.timed_quiz_running:
            self._pause_timer_job_preserve_time()
            if self.timer_question_id != question_id or self.timer_remaining_seconds <= 0:
                self.timer_question_id = question_id
                self.timer_remaining_seconds = self._timer_duration_seconds()
            self.timer_label.config(text=self._format_timer(self.timer_remaining_seconds))
            return

        if self.timer_question_id != question_id or self.timer_job is None:
            self._restart_timer_for_current_question()

    def _timer_tick(self) -> None:
        self.timer_job = None
        if (
            not self.timer_enabled
            or not self.timed_quiz_running
            or self.timer_question_id is None
        ):
            return
        if not self.questions or not self.records:
            return
        question_id = self.timer_question_id
        if not (0 <= question_id < len(self.records)) or self.records[question_id].get("submitted"):
            self._stop_timer(clear=False)
            return
        self.timer_remaining_seconds = max(0, self.timer_remaining_seconds - 1)
        self.timer_label.config(text=self._format_timer(self.timer_remaining_seconds))
        if self.timer_remaining_seconds <= 0:
            self._timer_expired(question_id)
            return
        self.timer_job = self.after(1000, self._timer_tick)

    def _timer_expired(self, question_id: int) -> None:
        self.timer_job = None
        self.timer_question_id = None
        if not (0 <= question_id < len(self.questions)):
            return
        record = self.records[question_id]
        if record.get("submitted"):
            return

        # Expiration is always a wrong answer, even if the user happened to
        # have the correct choice(s) selected but did not press Submit in time.
        question = self.questions[question_id]
        selected_indices = self._record_selected_indices(record)
        selected_list = sorted(selected_indices)
        self.records[question_id] = {
            "selected_indices": selected_list,
            "selected_answers": [question.answers[index] for index in selected_list],
            "selected_index": selected_list[0] if len(selected_list) == 1 else -1,
            "selected_answer": question.answers[selected_list[0]] if len(selected_list) == 1 else None,
            "submitted": True,
            "correct": False,
            "timed_out": True,
        }
        self.timer_remaining_seconds = 0
        self.timer_label.config(text="00:00")
        self._refresh_navigator()

        # Do not show the normal result overlay/borders or reveal correctness on
        # screen. Move directly onward and start a fresh per-question timer.
        if self.questions and self._current_question_id() == question_id:
            if self.current_index < len(self.questions) - 1:
                self.current_index += 1
                self._display_question()
            else:
                self.next_question()

    @staticmethod
    def _shuffle_different(values: list[int]) -> list[int]:
        shuffled = list(values)
        if len(shuffled) <= 1:
            return shuffled
        original = shuffled.copy()
        for _ in range(30):
            random.shuffle(shuffled)
            if shuffled != original:
                return shuffled
        return original[1:] + original[:1]

    def _timed_question_order(self, enabled: bool) -> list[int]:
        current = (
            list(self.question_order)
            if len(self.question_order) == len(self.questions)
            else list(range(len(self.questions)))
        )
        open_positions: list[int] = []
        open_question_ids: list[int] = []
        for position, question_id in enumerate(current):
            if self.records[question_id].get("submitted"):
                continue
            open_positions.append(position)
            open_question_ids.append(question_id)
        replacement = (
            self._shuffle_different(open_question_ids)
            if enabled
            else sorted(open_question_ids)
        )
        updated = list(current)
        for position, question_id in zip(open_positions, replacement):
            updated[position] = question_id
        return updated

    def _new_random_question_order(self) -> list[int]:
        order = list(range(len(self.questions)))
        if len(order) > 1:
            original = order.copy()
            # Avoid the rare case where "Enable" appears to do nothing because
            # random.shuffle happened to return the original sequence.
            for _ in range(20):
                random.shuffle(order)
                if order != original:
                    break
            if order == original:
                order = order[1:] + order[:1]
        return order

    def _set_question_randomization(self, enabled: bool) -> None:
        self.randomization_enabled = enabled
        self.config_data["randomize_questions"] = enabled

        if not self.questions:
            return

        current_question_id = self._current_question_id()
        if self.timer_enabled:
            self.question_order = self._timed_question_order(enabled)
        elif enabled:
            self.question_order = self._new_random_question_order()
        else:
            self.question_order = list(range(len(self.questions)))

        try:
            self.current_index = self.question_order.index(current_question_id)
        except ValueError:
            self.current_index = 0

        self._enforce_navigation_mode(redisplay=False)
        self._build_navigator()
        self._display_question()
        if self.timer_enabled:
            self._restart_timer_for_current_question()
        self.status_label.config(
            text=(
                "Unanswered questions randomized; submitted question positions kept."
                if enabled and self.timer_enabled
                else "Unanswered questions restored toward CSV order; submitted positions kept."
                if (not enabled and self.timer_enabled)
                else "Questions randomized."
                if enabled
                else "Original CSV question order restored."
            )
        )

    def _default_answer_orders(self) -> list[list[int]]:
        return [list(range(len(question.answers))) for question in self.questions]

    def _new_random_answer_order(self, question_id: int) -> list[int]:
        order = list(range(len(self.questions[question_id].answers)))
        if len(order) > 1:
            original = order.copy()
            for _ in range(20):
                random.shuffle(order)
                if order != original:
                    break
            if order == original:
                order = order[1:] + order[:1]
        return order

    def _new_random_answer_orders(self) -> list[list[int]]:
        return [self._new_random_answer_order(i) for i in range(len(self.questions))]

    def _answer_order_for(self, question_id: int) -> list[int]:
        if (
            0 <= question_id < len(self.answer_orders)
            and len(self.answer_orders[question_id]) == len(self.questions[question_id].answers)
        ):
            return self.answer_orders[question_id]
        return list(range(len(self.questions[question_id].answers)))

    def _display_answer_index(self, question_id: int, original_answer_index: int) -> int:
        try:
            return self._answer_order_for(question_id).index(original_answer_index)
        except ValueError:
            return -1

    def _set_answer_randomization(self, enabled: bool) -> None:
        self.answer_randomization_enabled = enabled
        self.config_data["randomize_answers"] = enabled

        if not self.questions:
            return

        if self.timer_enabled:
            updated: list[list[int]] = []
            for question_id, question in enumerate(self.questions):
                if self.records[question_id].get("submitted"):
                    updated.append(list(self._answer_order_for(question_id)))
                elif enabled:
                    updated.append(self._new_random_answer_order(question_id))
                else:
                    updated.append(list(range(len(question.answers))))
            self.answer_orders = updated
        elif enabled:
            self.answer_orders = self._new_random_answer_orders()
        else:
            self.answer_orders = self._default_answer_orders()

        self._display_question()
        if self.timer_enabled:
            self._restart_timer_for_current_question()
        self.status_label.config(
            text=(
                "Answers randomized for unanswered questions; submitted answer layouts kept."
                if enabled and self.timer_enabled
                else "Answers restored for unanswered questions; submitted answer layouts kept."
                if (not enabled and self.timer_enabled)
                else "Answers randomized."
                if enabled
                else "Original CSV answer order restored."
            )
        )

    def request_reset_quiz(self) -> None:
        if self.timer_enabled and self.questions and self.timed_quiz_running:
            self._pause_timed_quiz_internal("reset")

        if not self.questions:
            messagebox.showinfo(
                "Reset Quiz",
                "Load a quiz before resetting progress.",
                parent=self,
            )
            return

        dialog = ResetAttemptConfirmationDialog(self)
        if not dialog.show():
            return

        self.reset_quiz_from_options()

    def reset_quiz_from_options(self) -> None:
        if not self.questions:
            messagebox.showinfo(
                "Reset Quiz",
                "Load a quiz before resetting progress.",
                parent=self.options_dialog or self,
            )
            return

        any_randomization = (
            self.randomization_enabled or self.answer_randomization_enabled
        )
        keep_randomization = False
        if any_randomization:
            dialog = ResetRandomizationDialog(self.options_dialog or self)
            choice = dialog.show()
            if choice in (None, "cancel"):
                return
            keep_randomization = choice == "keep"

        self.records = [self._blank_record() for _ in self.questions]
        self.current_index = 0
        if self.timer_enabled:
            self.timed_quiz_running = False
            self.timed_quiz_started = False
            self.timed_pause_reason = "ready"
            self._restart_timer_for_current_question()

        if keep_randomization:
            # Keep both exact ordering maps and both enabled/disabled states.
            pass
        else:
            self.randomization_enabled = False
            self.answer_randomization_enabled = False
            self.config_data["randomize_questions"] = False
            self.config_data["randomize_answers"] = False
            self.question_order = list(range(len(self.questions)))
            self.answer_orders = self._default_answer_orders()

        self._save_config()
        if self.options_dialog is not None:
            try:
                self.options_dialog._refresh_list()
            except tk.TclError:
                pass
        self._build_navigator()
        self._display_question()
        self.status_label.config(
            text=(
                "Quiz reset. Current randomized organization kept."
                if keep_randomization
                else "Quiz reset. Original CSV organization restored."
            )
        )

    def _apply_image_display_layout(self) -> None:
        self._update_side_panel_layout()
        if self.image_display_enabled:
            if self.questions:
                self._display_question_image(
                    self.questions[self._current_question_id()].image_path
                )
            else:
                self._clear_question_image(
                    "Images linked in the CSV will appear here."
                )
        else:
            self._clear_question_image("")

        self.after_idle(self._refresh_responsive_layout)
        if self.overlay is not None:
            self._schedule_overlay_reposition()

    def _update_correct_answer_checks(
        self, question: QuizQuestion, record: dict[str, Any]
    ) -> None:
        """Reveal the correct choice after a wrong answer with a right-side check only."""
        show = bool(
            self.show_correct_after_wrong
            and record.get("submitted")
            and not record.get("correct")
            and not record.get("timed_out")
        )
        correct = set(question.correct_indices) if show else set()

        # The checkmark is reveal-only: it is hidden in every other state.
        for label in self.answer_check_labels.values():
            label.pack_forget()

        if not show:
            return

        normal_fill = self.answers_frame.cget("bg")
        for answer_id in correct:
            widgets = self.answer_option_widgets.get(answer_id)
            if widgets is None:
                continue
            border, row, selector, answer_label = widgets

            # Only the answer revealed because the submission was wrong returns to
            # the original neutral gray border. Correct submissions keep the normal
            # green result styling handled by _apply_answer_result_borders().
            border.config(bg=DEFAULT_ANSWER_BORDER)
            row.config(bg=normal_fill)
            answer_label.config(bg=normal_fill)
            try:
                selector.config(
                    bg=normal_fill,
                    activebackground=normal_fill,
                )
            except tk.TclError:
                pass

            check_label = self.answer_check_labels.get(answer_id)
            if check_label is not None:
                check_label.config(bg=normal_fill)
                check_label.pack(side="right", padx=(10, 0))

    def _update_explanation_panel(
        self, question: QuizQuestion, record: dict[str, Any]
    ) -> None:
        show = bool(
            question.explanation
            and record.get("submitted")
            and not record.get("correct")
            and not record.get("timed_out")
        )
        if show:
            correct_answers = [question.answers[index] for index in question.correct_indices]
            correct_text = "\n".join(correct_answers)
            self.explanation_heading_label.config(text="Correct Answer:")
            self.explanation_label.config(text=correct_text)
            self.explanation_title_label.config(text="Explanation:")
            self.explanation_body_label.config(text=question.explanation)
        else:
            self.explanation_label.config(text="")
            self.explanation_body_label.config(text="")
        self._update_side_panel_layout(show_explanation=show)

    def _update_side_panel_layout(self, show_explanation: Optional[bool] = None) -> None:
        if show_explanation is None:
            show_explanation = bool(self.explanation_label.cget("text"))

        # The image may still occupy the right-hand column, but the explanation now
        # stays in the normal question flow below the answers.
        self.image_panel.grid_remove()
        self.explanation_panel.pack_forget()
        for column in (0, 1, 2):
            self.quiz_view.grid_columnconfigure(column, weight=0, minsize=0)

        self.quiz_view.grid_columnconfigure(0, weight=3)
        next_column = 1
        if self.image_display_enabled:
            self.quiz_view.grid_columnconfigure(next_column, weight=2)
            self.image_panel.grid(row=0, column=next_column, sticky="nsew")
            next_column += 1

        if show_explanation:
            self.explanation_panel.pack(
                fill="x",
                pady=(4, 8),
                after=self.answers_frame,
            )

        self.question_area.grid_configure(
            padx=(0, 16) if next_column > 1 else (0, 0)
        )

    def _refresh_responsive_layout(self) -> None:
        try:
            self.update_idletasks()
            question_width = max(260, self.question_area.winfo_width() - 30)
            self.prompt_label.config(wraplength=question_width)
            answer_wrap = max(220, self.question_area.winfo_width() - 100)
            for widget in self.answer_rows:
                if isinstance(widget, tk.Label) and widget not in self.answer_check_labels.values():
                    widget.config(wraplength=answer_wrap)
            if self.explanation_panel.winfo_manager():
                explanation_wrap = max(220, self.question_area.winfo_width() - 40)
                self.explanation_label.config(wraplength=explanation_wrap)
                self.explanation_body_label.config(wraplength=explanation_wrap)
        except tk.TclError:
            pass

    def _first_unanswered_index(self) -> Optional[int]:
        for display_index in range(len(self.questions)):
            question_id = self._question_id_at(display_index)
            if not self.records[question_id].get("submitted"):
                return display_index
        return None

    def _can_open_question(self, index: int) -> bool:
        if not (0 <= index < len(self.questions)):
            return False
        if self.free_question_navigation:
            return True
        question_id = self._question_id_at(index)
        if self.records[question_id].get("submitted"):
            return True
        return index == self._first_unanswered_index()

    def _enforce_navigation_mode(self, redisplay: bool = True) -> None:
        if self.free_question_navigation or not self.records:
            return
        if self._can_open_question(self.current_index):
            return
        first_unanswered = self._first_unanswered_index()
        if first_unanswered is not None:
            self.current_index = first_unanswered
            if redisplay:
                self._display_question()

    def _set_nav_counter(
        self,
        completed: int,
        correct: int,
        wrong: int,
        total: int,
    ) -> None:
        self.nav_counter.config(state="normal")
        self.nav_counter.delete("1.0", "end")
        self.nav_counter.insert("end", f"{completed} (", "normal")
        self.nav_counter.insert("end", str(correct), "correct")
        self.nav_counter.insert("end", " + ", "normal")
        self.nav_counter.insert("end", str(wrong), "wrong")
        self.nav_counter.insert("end", f") / {total}", "normal")
        self.nav_counter.config(state="disabled")

    def toggle_navigator(self) -> None:
        self.navigator_visible = not self.navigator_visible
        if self.navigator_visible:
            self.navigator_panel.pack(
                side="left",
                fill="y",
                before=self.content,
            )
            self.navigator_toggle.config(text="☰")
            self._refresh_navigator()
        else:
            self.navigator_panel.pack_forget()
            self.navigator_toggle.config(text="☰")

        if self.overlay is not None:
            self._schedule_overlay_reposition()

    def _scroll_navigator(self, event: tk.Event) -> str:
        if self.navigator_visible:
            direction = -1 if event.delta > 0 else 1
            self.navigator_canvas.yview_scroll(direction, "units")
        return "break"

    def _build_navigator(self) -> None:
        for child in self.navigator_grid.winfo_children():
            child.destroy()
        self.navigator_buttons.clear()
        self._set_nav_counter(0, 0, 0, 0)

        for index in range(len(self.questions)):
            row = index // 5
            column = index % 5
            square = tk.Button(
                self.navigator_grid,
                text=str(index + 1),
                width=4,
                height=2,
                bd=1,
                relief="solid",
                overrelief="raised",
                bg="#d8d8d8",
                fg="#777777",
                activebackground="#d8d8d8",
                activeforeground="#777777",
                disabledforeground="#888888",
                font=("TkDefaultFont", 9, "bold"),
                padx=0,
                pady=0,
                takefocus=False,
                command=lambda i=index: self._open_question_from_navigator(i),
            )
            square.grid(row=row, column=column, padx=3, pady=3, sticky="nsew")
            square.bind("<MouseWheel>", self._scroll_navigator)
            self.navigator_buttons.append(square)

        for column in range(5):
            self.navigator_grid.grid_columnconfigure(column, weight=1)

        self._refresh_navigator()

    def _open_question_from_navigator(self, index: int) -> None:
        if self._timed_quiz_locked():
            return
        if not (0 <= index < len(self.questions)):
            return
        if not self._can_open_question(index):
            return

        self.current_index = index
        self._display_question()

    def _refresh_navigator(self) -> None:
        correct_count = sum(
            1 for record in self.records
            if record.get("submitted") and record.get("correct")
        )
        wrong_count = sum(
            1 for record in self.records
            if record.get("submitted") and record.get("correct") is False
        )
        completed_count = correct_count + wrong_count
        total_count = len(self.questions)

        self._set_nav_counter(
            completed_count,
            correct_count,
            wrong_count,
            total_count,
        )

        if not self.navigator_buttons:
            return

        first_unanswered = self._first_unanswered_index()
        timed_locked = self._timed_quiz_locked()
        for index, square in enumerate(self.navigator_buttons):
            record = self.records[self._question_id_at(index)] if index < len(self.questions) else {}

            if index == self.current_index:
                bg = "#777777"
                fg = "white"
                state = "normal"
            elif record.get("submitted"):
                bg = "#36a852" if record.get("correct") else "#cf3d3d"
                fg = "white"
                state = "normal"
            else:
                bg = "#d8d8d8"
                fg = "#555555" if (
                    self.free_question_navigation or index == first_unanswered
                ) else "#888888"
                state = "normal" if (
                    self.free_question_navigation or index == first_unanswered
                ) else "disabled"

            if timed_locked:
                state = "disabled"

            square.config(
                bg=bg,
                fg=fg,
                activebackground=bg,
                activeforeground=fg,
                disabledforeground=fg,
                state=state,
            )

        if self.navigator_visible and 0 <= self.current_index < len(self.navigator_buttons):
            square = self.navigator_buttons[self.current_index]
            self.navigator_canvas.update_idletasks()
            top = square.winfo_y()
            bottom = top + square.winfo_height()
            visible_top = self.navigator_canvas.canvasy(0)
            visible_bottom = visible_top + self.navigator_canvas.winfo_height()
            total_height = max(1, self.navigator_grid.winfo_height())
            if top < visible_top:
                self.navigator_canvas.yview_moveto(max(0.0, top / total_height))
            elif bottom > visible_bottom:
                target = max(0.0, (bottom - self.navigator_canvas.winfo_height()) / total_height)
                self.navigator_canvas.yview_moveto(min(1.0, target))

    def _update_answer_visibility_button(self) -> None:
        if self.hide_answers_button is None:
            return
        self.hide_answers_button.config(
            image=(self.icon_eye_off if self.answers_hidden else self.icon_eye),
            state="normal",
            cursor="hand2",
        )

    def _answers_currently_hidden(self) -> bool:
        if not self.answers_hidden:
            return False
        if not self.questions:
            return True
        return self.temporarily_revealed_question_id != self._current_question_id()

    def toggle_answer_visibility(self) -> None:
        # The eye controls the persistent cover mode. A temporary reveal made by
        # clicking VIEW ANSWERS never changes the eye/icon state.
        self.answers_hidden = not self.answers_hidden
        self.temporarily_revealed_question_id = None
        self._update_answer_visibility_button()
        if self.questions:
            self._display_question()

    def _reveal_hidden_answers(self) -> None:
        if not self._answers_currently_hidden():
            return
        # Reveal only this question. Keep answers_hidden=True so the eye stays
        # slashed and another question receives the cover again.
        self.temporarily_revealed_question_id = self._current_question_id()
        if self.questions:
            self._display_question()
        self.status_label.config(text="Answers revealed for this question. Select your answer.")

    def _paint_clickable_answer_cover(self, canvas: tk.Canvas) -> None:
        # Start with the exact same dotted gray cover used by the eye button.
        self._paint_hidden_answer_cover(canvas)
        try:
            width = max(1, canvas.winfo_width())
            height = max(1, canvas.winfo_height())
            # Keep VIEW ANSWERS prominent, but smaller than the result overlay
            # so the horizontal phrase fits comfortably inside the cover.
            font_size = max(24, min(46, int(width / 18)))
            canvas.create_text(
                width // 2, height // 2,
                text="VIEW ANSWERS",
                fill="#858585",
                font=("TkDefaultFont", font_size, "bold"),
            )
        except tk.TclError:
            pass

    def _show_welcome(self) -> None:
        self._stop_timer(clear=True)
        self.timed_quiz_running = False
        self.timed_quiz_started = False
        self.timed_pause_reason = "ready"
        self._refresh_timer_session_controls()
        self.question_number_label.config(text="")
        self.result_badge.pack_forget()
        self.multi_answer_banner.pack_forget()
        self.prompt_label.config(
            text="Choose a CSV quiz file using the button in the upper-left corner."
        )
        for child in self.answers_frame.winfo_children():
            child.destroy()
        self.status_label.config(text="")
        if self.image_display_enabled:
            self._clear_question_image(
                "Images linked in the CSV will appear here."
            )
        else:
            self._clear_question_image("")
        self._remove_overlay()
        for child in self.navigator_grid.winfo_children():
            child.destroy()
        self.navigator_buttons.clear()

    def _on_resize(self, event: tk.Event) -> None:
        if event.widget is self:
            self.update_idletasks()
            question_width = max(260, self.question_area.winfo_width() - 30)
            self.prompt_label.config(wraplength=question_width)

            answer_wrap = max(220, self.question_area.winfo_width() - 100)
            for widget in self.answer_rows:
                if isinstance(widget, tk.Label):
                    try:
                        widget.config(wraplength=answer_wrap)
                    except tk.TclError:
                        pass

            if self.overlay is not None:
                self._schedule_overlay_reposition()

            if self.image_display_enabled:
                self._schedule_image_render()

    def browse_csv(self) -> None:
        filename = filedialog.askopenfilename(
            title="Choose a quiz CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return

        csv_path = Path(filename).resolve()
        try:
            questions = self._read_quiz(csv_path)
        except Exception as exc:
            messagebox.showerror("Could not open quiz", str(exc), parent=self)
            return

        progress_files = self._find_progress_files(csv_path)
        chosen_progress: Optional[Path] = None
        start_new = True

        if progress_files:
            dialog = AttemptChoiceDialog(self, csv_path.name, progress_files)
            choice = dialog.show()

            if choice in (None, "cancel"):
                return
            if choice == "continue":
                chosen_progress = progress_files[0]
                start_new = False
            elif choice == "browse":
                picked = filedialog.askopenfilename(
                    title="Choose a saved quiz attempt",
                    initialdir=str(APP_DIR),
                    filetypes=[("Quiz progress files", f"{csv_path.stem}-progress-*.txt"),
                               ("Text files", "*.txt")],
                )
                if not picked:
                    return
                chosen_progress = Path(picked).resolve()
                start_new = False

        self.csv_path = csv_path
        self.questions = questions
        self.question_order = list(range(len(questions)))
        self.answer_orders = self._default_answer_orders()

        if start_new:
            self.attempt_number = self._next_attempt_number(csv_path)
            self.current_index = 0
            self.records = [self._blank_record() for _ in questions]
            if self.randomization_enabled:
                self.question_order = self._new_random_question_order()
            if self.answer_randomization_enabled:
                self.answer_orders = self._new_random_answer_orders()
        else:
            try:
                self._load_progress(chosen_progress)
            except Exception as exc:
                messagebox.showerror("Could not load progress", str(exc), parent=self)
                return

        self._enforce_navigation_mode(redisplay=False)

        if self.timer_enabled:
            self.timed_quiz_running = False
            self.timed_quiz_started = (not start_new) or any(
                record.get("submitted") for record in self.records
            )
            self.timed_pause_reason = "ready"
            self._restart_timer_for_current_question()
        else:
            self.timed_quiz_running = False
            self.timed_quiz_started = False

        self.title_label.config(
            text=f"{csv_path.name} | Attempt {self.attempt_number}"
        )
        self.save_button.config(state="normal")
        self._build_navigator()
        self._display_question()

    def _read_quiz(self, csv_path: Path) -> list[QuizQuestion]:
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle))
        except UnicodeDecodeError:
            with csv_path.open("r", encoding="cp1252", newline="") as handle:
                rows = list(csv.reader(handle))

        rows = [row for row in rows if any(cell.strip() for cell in row)]
        if len(rows) < 2:
            raise ValueError("The CSV must contain a header row and at least one question.")

        headers = [cell.strip() for cell in rows[0]]
        normalized = [self._normalize_header(h) for h in headers]

        question_col = 0
        for idx, header in enumerate(normalized):
            if header in QUESTION_HEADER_NAMES:
                question_col = idx
                break

        correct_col: Optional[int] = None
        for idx, header in enumerate(normalized):
            if header in CORRECT_HEADER_NAMES:
                correct_col = idx
                break

        image_col: Optional[int] = None
        for idx, header in enumerate(normalized):
            if header in IMAGE_HEADER_NAMES:
                image_col = idx
                break

        explanation_col: Optional[int] = None
        for idx, header in enumerate(normalized):
            if header in EXPLANATION_HEADER_NAMES:
                explanation_col = idx
                break

        answer_cols = [
            idx for idx in range(len(headers))
            if idx not in {question_col, correct_col, image_col, explanation_col}
        ]
        if not answer_cols:
            raise ValueError("No answer columns were found.")

        questions: list[QuizQuestion] = []
        for row_number, raw_row in enumerate(rows[1:], start=2):
            row = raw_row + [""] * (len(headers) - len(raw_row))
            prompt = row[question_col].strip()
            if not prompt:
                continue

            answers: list[str] = []
            source_cols: list[int] = []
            marked_correct: list[int] = []

            for col in answer_cols:
                value = row[col].strip()
                if not value:
                    continue
                if value.startswith("*"):
                    value = value[1:].lstrip()
                    marked_correct.append(len(answers))
                answers.append(value)
                source_cols.append(col)

            if len(answers) < 2:
                raise ValueError(
                    f"Row {row_number} must contain at least two non-empty answers."
                )

            correct_indices = list(marked_correct)
            if not correct_indices and correct_col is not None:
                key = row[correct_col].strip()
                correct_indices = self._resolve_correct_values(
                    key, answers, source_cols, headers, row_number
                )
            if not correct_indices:
                correct_indices = [0]

            image_path: Optional[Path] = None
            if image_col is not None:
                image_value = row[image_col].strip()
                if image_value:
                    candidate = Path(image_value).expanduser()
                    if not candidate.is_absolute():
                        candidate = csv_path.parent / candidate
                    image_path = candidate.resolve(strict=False)

            explanation = ""
            if explanation_col is not None:
                explanation = row[explanation_col].strip()

            questions.append(
                QuizQuestion(
                    prompt=prompt,
                    answers=answers,
                    correct_indices=correct_indices,
                    image_path=image_path,
                    explanation=explanation,
                )
            )

        if not questions:
            raise ValueError("No usable quiz questions were found.")
        return questions

    @staticmethod
    def _normalize_header(value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().lower().replace("-", " "))

    def _resolve_single_correct_value(
        self,
        key: str,
        answers: list[str],
        source_cols: list[int],
        headers: list[str],
        row_number: int,
    ) -> int:
        token = key.strip()
        if token.isdigit():
            number = int(token)
            if 1 <= number <= len(answers):
                return number - 1

        key_folded = token.casefold()
        for idx, answer in enumerate(answers):
            if answer.casefold() == key_folded:
                return idx

        for idx, source_col in enumerate(source_cols):
            if headers[source_col].strip().casefold() == key_folded:
                return idx

        raise ValueError(
            f'Row {row_number}: Correct value "{token}" does not match an answer.'
        )

    def _resolve_correct_values(
        self,
        key: str,
        answers: list[str],
        source_cols: list[int],
        headers: list[str],
        row_number: int,
    ) -> list[int]:
        if not key:
            raise ValueError(f"Row {row_number} has an empty Correct value.")

        # Keep exact-text/header support even if the value itself contains a comma.
        key_folded = key.casefold()
        for idx, answer in enumerate(answers):
            if answer.casefold() == key_folded:
                return [idx]
        for idx, source_col in enumerate(source_cols):
            if headers[source_col].strip().casefold() == key_folded:
                return [idx]

        parts = [part.strip() for part in key.split(",")]
        if any(not part for part in parts):
            raise ValueError(
                f'Row {row_number}: Correct value "{key}" contains an empty entry.'
            )

        resolved = [
            self._resolve_single_correct_value(
                part, answers, source_cols, headers, row_number
            )
            for part in parts
        ]
        if len(set(resolved)) != len(resolved):
            raise ValueError(
                f'Row {row_number}: Correct value "{key}" repeats the same answer.'
            )
        return sorted(resolved)

    def _record_selected_indices(self, record: dict[str, Any]) -> set[int]:
        raw = record.get("selected_indices")
        if isinstance(raw, list):
            return {value for value in raw if isinstance(value, int) and value >= 0}
        legacy = record.get("selected_index", -1)
        if isinstance(legacy, int) and legacy >= 0:
            return {legacy}
        return set()

    def _measure_answer_stack_height(self, question_id: int) -> int:
        """Measure the normal answer stack without ever displaying it."""
        question = self.questions[question_id]
        measure_frame = tk.Frame(self.answers_frame)
        row_background = self.answers_frame.cget("bg")
        variables: list[tk.Variable] = []

        try:
            answer_order = self._answer_order_for(question_id)
            for answer_id in answer_order:
                border = tk.Frame(
                    measure_frame,
                    bg="#555555",
                    bd=0,
                    padx=2,
                    pady=2,
                )
                border.pack(fill="x", pady=4)

                row = tk.Frame(
                    border,
                    bg=row_background,
                    padx=10,
                    pady=9,
                )
                row.pack(fill="x", expand=True)

                if question.is_multi_select:
                    variable: tk.Variable = tk.BooleanVar(value=False)
                    selector = tk.Checkbutton(
                        row,
                        variable=variable,
                        bg=row_background,
                        activebackground=row_background,
                    )
                else:
                    variable = tk.IntVar(value=-1)
                    selector = tk.Radiobutton(
                        row,
                        variable=variable,
                        value=answer_id,
                        bg=row_background,
                        activebackground=row_background,
                    )
                variables.append(variable)
                selector.pack(side="left", padx=(0, 8))

                tk.Label(
                    row,
                    text=question.answers[answer_id],
                    justify="left",
                    anchor="w",
                    wraplength=max(220, self.question_area.winfo_width() - 100),
                    bg=row_background,
                ).pack(side="left", fill="x", expand=True)

            # The measurement frame is deliberately never packed or gridded, so
            # none of these temporary answer widgets can flash on screen.
            measure_frame.update_idletasks()
            return max(1, measure_frame.winfo_reqheight() + 6)
        finally:
            measure_frame.destroy()

    def _paint_hidden_answer_cover(self, canvas: tk.Canvas) -> None:
        try:
            width = max(1, canvas.winfo_width())
            height = max(1, canvas.winfo_height())
            canvas.delete("all")
            canvas.create_rectangle(0, 0, width + 1, height + 1, fill=ANSWER_HIDE_FILL, outline="")

            dot_spacing = 14
            dot_radius = 1
            row_offset = dot_spacing // 2
            for y in range(8, height, dot_spacing):
                start_x = 8 if ((y // dot_spacing) % 2 == 0) else 8 + row_offset
                for x in range(start_x, width, dot_spacing):
                    canvas.create_oval(
                        x - dot_radius,
                        y - dot_radius,
                        x + dot_radius,
                        y + dot_radius,
                        fill=ANSWER_HIDE_DOT,
                        outline=ANSWER_HIDE_DOT,
                    )
        except tk.TclError:
            pass

    def _display_question(self) -> None:
        self._remove_overlay()
        self._refresh_navigator()
        for child in self.answers_frame.winfo_children():
            child.destroy()
        self.answer_rows.clear()
        self.answer_borders.clear()
        self.answer_check_labels.clear()
        self.answer_option_widgets.clear()
        self.multi_selected_vars.clear()

        if not self.questions:
            self._show_welcome()
            return

        question_id = self._current_question_id()
        question = self.questions[question_id]
        record = self.records[question_id]
        selected_indices = self._record_selected_indices(record)

        self.question_number_label.config(
            text=f"Question {self.current_index + 1} of {len(self.questions)}"
        )
        self.prompt_label.config(text=question.prompt)
        if question.is_multi_select:
            self.multi_answer_banner.pack(fill="x", pady=(0, 8))
        else:
            self.multi_answer_banner.pack_forget()

        if self.image_display_enabled:
            self._display_question_image(question.image_path)
        else:
            self._clear_question_image("")
        self._update_explanation_panel(question, record)

        if not question.is_multi_select and len(selected_indices) == 1:
            self.selected_var.set(next(iter(selected_indices)))
        else:
            self.selected_var.set(-1)

        if self._answers_currently_hidden():
            hidden_height = self._measure_answer_stack_height(question_id)
            hidden_panel = tk.Frame(
                self.answers_frame,
                bg=ANSWER_HIDE_FILL,
                bd=0,
                height=hidden_height,
                highlightthickness=0,
                cursor="hand2",
            )
            hidden_panel.pack(fill="x", expand=False)
            hidden_panel.pack_propagate(False)

            hidden_canvas = tk.Canvas(
                hidden_panel,
                bg=ANSWER_HIDE_FILL,
                bd=0,
                highlightthickness=0,
                relief="flat",
                height=hidden_height,
                cursor="hand2",
            )
            hidden_canvas.pack(fill="both", expand=True)
            hidden_canvas.bind(
                "<Configure>",
                lambda _event, canvas=hidden_canvas: self._paint_clickable_answer_cover(canvas),
            )
            hidden_canvas.bind(
                "<Button-1>",
                lambda _event: self._reveal_hidden_answers(),
            )
            self.after_idle(
                lambda canvas=hidden_canvas: self._paint_clickable_answer_cover(canvas)
                if canvas.winfo_exists() else None
            )

            if record.get("submitted"):
                self._show_result_badge(bool(record.get("correct")))
                self.submit_button.config(state="disabled")
                self.next_button.config(state="normal")
            else:
                self.result_badge.pack_forget()
                self.submit_button.config(state="disabled")
                self.next_button.config(state="disabled")

            self.status_label.config(
                text="Click VIEW ANSWERS or the eye button to show the answer choices."
            )
            self._set_answer_controls(False)

            if self.current_index == len(self.questions) - 1:
                self.next_button.config(text="Finish")
            else:
                self.next_button.config(text="Next")

            self._sync_timer_for_display()
            self._apply_timed_quiz_gate()
            return

        row_background = self.answers_frame.cget("bg")
        answer_order = self._answer_order_for(question_id)
        for answer_id in answer_order:
            answer = question.answers[answer_id]
            border = tk.Frame(
                self.answers_frame,
                bg=DEFAULT_ANSWER_BORDER,
                bd=0,
                padx=2,
                pady=2,
                cursor="hand2",
            )
            border.pack(fill="x", pady=4)

            row = tk.Frame(
                border,
                bg=row_background,
                padx=10,
                pady=9,
                cursor="hand2",
            )
            row.pack(fill="x", expand=True)

            if question.is_multi_select:
                variable = tk.BooleanVar(value=answer_id in selected_indices)
                self.multi_selected_vars[answer_id] = variable
                selector = tk.Checkbutton(
                    row,
                    variable=variable,
                    command=self._multi_selection_changed,
                    bg=row_background,
                    activebackground=row_background,
                )
            else:
                selector = tk.Radiobutton(
                    row,
                    variable=self.selected_var,
                    value=answer_id,
                    command=self._selection_changed,
                    bg=row_background,
                    activebackground=row_background,
                )
            selector.pack(side="left", padx=(0, 8))

            label = tk.Label(
                row,
                text=answer,
                justify="left",
                anchor="w",
                wraplength=max(220, self.question_area.winfo_width() - 100),
                cursor="hand2",
                bg=row_background,
            )
            label.pack(side="left", fill="x", expand=True)

            check_label = tk.Label(
                row,
                text="✅",
                anchor="e",
                bg=row_background,
                fg=CORRECT_ANSWER_BORDER,
                font=("TkDefaultFont", 14, "bold"),
                cursor="hand2",
            )
            # Do not pack it yet. It appears only when a wrong submission reveals
            # the correct answer, so normal and correctly answered questions are unchanged.
            self.answer_check_labels[answer_id] = check_label

            if question.is_multi_select:
                border.bind("<Button-1>", lambda _e, i=answer_id: self._toggle_multi_answer(i))
                row.bind("<Button-1>", lambda _e, i=answer_id: self._toggle_multi_answer(i))
                label.bind("<Button-1>", lambda _e, i=answer_id: self._toggle_multi_answer(i))
                check_label.bind("<Button-1>", lambda _e, i=answer_id: self._toggle_multi_answer(i))
            else:
                border.bind("<Button-1>", lambda _e, i=answer_id: self._select_answer(i))
                row.bind("<Button-1>", lambda _e, i=answer_id: self._select_answer(i))
                label.bind("<Button-1>", lambda _e, i=answer_id: self._select_answer(i))
                check_label.bind("<Button-1>", lambda _e, i=answer_id: self._select_answer(i))

            self.answer_borders.append(border)
            self.answer_option_widgets[answer_id] = (border, row, selector, label)
            self.answer_rows.extend([border, row, selector, label])

        if record.get("submitted"):
            self._set_answer_controls(False)
            self._show_result_badge(bool(record.get("correct")))
            self._apply_answer_result_borders(
                question_id,
                selected_indices,
                bool(record.get("correct")),
            )
            self._update_correct_answer_checks(question, record)
            self.submit_button.config(state="disabled")
            self.next_button.config(state="normal")
            self.status_label.config(
                text=(
                    "Time expired. This question was marked wrong."
                    if record.get("timed_out")
                    else "Answer submitted. Choose Next to continue."
                )
            )
        else:
            self.result_badge.pack_forget()
            self._set_answer_controls(True)
            self.submit_button.config(
                state="normal" if selected_indices else "disabled"
            )
            self.next_button.config(state="disabled")
            self.status_label.config(
                text=(
                    "Select all correct answers, then choose Submit."
                    if question.is_multi_select
                    else "Select one answer."
                )
            )

        if self.current_index == len(self.questions) - 1:
            self.next_button.config(text="Finish")
        else:
            self.next_button.config(text="Next")

        self._sync_timer_for_display()
        self._apply_timed_quiz_gate()

    def _on_image_panel_resize(self, _event: tk.Event) -> None:
        if not self.image_display_enabled:
            return
        if self.current_image_path is None:
            self._draw_image_message()
        else:
            self._schedule_image_render()

    def _schedule_image_render(self) -> None:
        if self.current_image_path is None:
            return

        if self.image_resize_job is not None:
            try:
                self.after_cancel(self.image_resize_job)
            except tk.TclError:
                pass

        self.image_resize_job = self.after(80, self._render_question_image)

    def _clear_question_image(self, message: str) -> None:
        if self.image_resize_job is not None:
            try:
                self.after_cancel(self.image_resize_job)
            except tk.TclError:
                pass
            self.image_resize_job = None

        self.current_image_path = None
        self.image_photo = None
        self._pil_source_image = None
        self._tk_source_image = None
        self.image_message = message
        self._draw_image_message()

    def _draw_image_message(self) -> None:
        try:
            width = max(1, self.image_canvas.winfo_width())
            height = max(1, self.image_canvas.winfo_height())
            self.image_canvas.delete("all")
            self.image_canvas.create_text(
                width / 2,
                height / 2,
                text=self.image_message,
                justify="center",
                width=max(80, width - 30),
                fill="#666666",
            )
        except tk.TclError:
            pass

    def _display_question_image(self, image_path: Optional[Path]) -> None:
        if image_path is None:
            self._clear_question_image("No image for this question.")
            return

        if not image_path.is_file():
            self._clear_question_image(
                f"Image not found:\n{image_path.name}"
            )
            return

        self.current_image_path = image_path
        self.image_photo = None
        self._pil_source_image = None
        self._tk_source_image = None
        self.image_message = "Loading image..."
        self._draw_image_message()

        try:
            if Image is not None and ImageTk is not None:
                with Image.open(image_path) as opened:
                    self._pil_source_image = opened.convert("RGBA").copy()
            else:
                self._tk_source_image = tk.PhotoImage(file=str(image_path))
        except Exception as exc:
            detail = str(exc).strip() or "Unsupported or damaged image file."
            self._clear_question_image(
                f"Could not open image:\n{image_path.name}\n\n{detail}"
            )
            return

        self.after_idle(self._render_question_image)

    def _render_question_image(self) -> None:
        self.image_resize_job = None
        if self.current_image_path is None:
            return

        try:
            available_width = max(1, self.image_canvas.winfo_width() - 12)
            available_height = max(1, self.image_canvas.winfo_height() - 12)

            if available_width < 20 or available_height < 20:
                self._schedule_image_render()
                return

            if self._pil_source_image is not None and ImageTk is not None:
                source_width, source_height = self._pil_source_image.size
                scale = min(
                    available_width / max(1, source_width),
                    available_height / max(1, source_height),
                )
                target_size = (
                    max(1, int(source_width * scale)),
                    max(1, int(source_height * scale)),
                )
                resampling = getattr(Image, "Resampling", Image)
                lanczos = getattr(resampling, "LANCZOS", 1)
                resized = self._pil_source_image.resize(
                    target_size,
                    lanczos,
                )
                self.image_photo = ImageTk.PhotoImage(resized)
            elif self._tk_source_image is not None:
                source_width = max(1, self._tk_source_image.width())
                source_height = max(1, self._tk_source_image.height())
                factor = max(
                    1,
                    (source_width + available_width - 1) // available_width,
                    (source_height + available_height - 1) // available_height,
                )
                self.image_photo = self._tk_source_image.subsample(
                    factor,
                    factor,
                )
            else:
                return

            canvas_width = max(1, self.image_canvas.winfo_width())
            canvas_height = max(1, self.image_canvas.winfo_height())
            self.image_canvas.delete("all")
            self.image_canvas.create_image(
                canvas_width / 2,
                canvas_height / 2,
                image=self.image_photo,
                anchor="center",
            )
        except Exception as exc:
            name = self.current_image_path.name
            self._clear_question_image(
                f"Could not display image:\n{name}\n\n{exc}"
            )

    def _show_result_badge(self, correct: bool) -> None:
        self.result_badge.config(
            text="CORRECT" if correct else "WRONG",
            bg="#21a642" if correct else "#c92b2b",
        )
        if not self.result_badge.winfo_manager():
            self.result_badge.pack(side="right")

    def _apply_answer_result_borders(
        self,
        question_id: int,
        selected_indices: set[int],
        correct: bool,
    ) -> None:
        normal_fill = self.answers_frame.cget("bg")

        # Reset every visible answer before applying submitted-result styling.
        for border, row, selector, answer_label in self.answer_option_widgets.values():
            border.config(bg=DEFAULT_ANSWER_BORDER)
            row.config(bg=normal_fill)
            answer_label.config(bg=normal_fill)
            try:
                selector.config(bg=normal_fill, activebackground=normal_fill)
            except tk.TclError:
                pass

        border_color = CORRECT_ANSWER_BORDER if correct else WRONG_ANSWER_BORDER
        fill_color = CORRECT_ANSWER_FILL if correct else WRONG_ANSWER_FILL
        for original_index in selected_indices:
            widgets = self.answer_option_widgets.get(original_index)
            if widgets is None:
                continue
            border, row, selector, answer_label = widgets
            border.config(bg=border_color)
            row.config(bg=fill_color)
            answer_label.config(bg=fill_color)
            try:
                selector.config(bg=fill_color, activebackground=fill_color)
            except tk.TclError:
                pass

    def _select_answer(self, index: int) -> None:
        if self._timed_quiz_locked() or self._answers_currently_hidden():
            return
        question_id = self._current_question_id()
        if self.records[question_id].get("submitted"):
            return
        self.selected_var.set(index)
        self._selection_changed()

    def _selection_changed(self) -> None:
        if self._timed_quiz_locked() or self._answers_currently_hidden():
            return
        question_id = self._current_question_id()
        if self.records[question_id].get("submitted"):
            return
        selected = self.selected_var.get()
        selected_indices = [selected] if selected >= 0 else []
        self.records[question_id]["selected_indices"] = selected_indices
        self.records[question_id]["selected_index"] = selected if selected >= 0 else -1
        self.records[question_id]["selected_answers"] = [
            self.questions[question_id].answers[selected]
        ] if selected >= 0 else []
        self.records[question_id]["selected_answer"] = (
            self.questions[question_id].answers[selected] if selected >= 0 else None
        )
        self.submit_button.config(state="normal" if selected >= 0 else "disabled")
        self.status_label.config(text="Answer selected. Choose Submit when ready.")

    def _toggle_multi_answer(self, index: int) -> None:
        if self._timed_quiz_locked() or self._answers_currently_hidden():
            return
        question_id = self._current_question_id()
        if self.records[question_id].get("submitted"):
            return
        variable = self.multi_selected_vars.get(index)
        if variable is None:
            return
        variable.set(not variable.get())
        self._multi_selection_changed()

    def _multi_selection_changed(self) -> None:
        if self._timed_quiz_locked() or self._answers_currently_hidden():
            return
        question_id = self._current_question_id()
        if self.records[question_id].get("submitted"):
            return
        selected_indices = sorted(
            answer_id
            for answer_id, variable in self.multi_selected_vars.items()
            if variable.get()
        )
        self.records[question_id]["selected_indices"] = selected_indices
        self.records[question_id]["selected_index"] = (
            selected_indices[0] if len(selected_indices) == 1 else -1
        )
        self.records[question_id]["selected_answers"] = [
            self.questions[question_id].answers[index] for index in selected_indices
        ]
        self.records[question_id]["selected_answer"] = (
            self.questions[question_id].answers[selected_indices[0]]
            if len(selected_indices) == 1 else None
        )
        self.submit_button.config(state="normal" if selected_indices else "disabled")
        if selected_indices:
            self.status_label.config(
                text=f"{len(selected_indices)} answer(s) selected. Select all correct answers, then choose Submit."
            )
        else:
            self.status_label.config(text="Select all correct answers, then choose Submit.")

    def _set_answer_controls(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        cursor = "hand2" if enabled else ""
        for widget in self.answer_rows:
            try:
                widget.config(cursor=cursor)
            except tk.TclError:
                pass
            if isinstance(widget, (tk.Radiobutton, tk.Checkbutton)):
                widget.config(state=state)

    def submit_answer(self) -> None:
        if self._timed_quiz_locked() or self._answers_currently_hidden():
            return
        question_id = self._current_question_id()
        question = self.questions[question_id]
        selected_indices = self._record_selected_indices(self.records[question_id])
        if not selected_indices:
            messagebox.showinfo(
                "Choose an answer",
                (
                    "Please select at least one answer first."
                    if question.is_multi_select
                    else "Please select an answer first."
                ),
                parent=self,
            )
            return

        is_correct = selected_indices == set(question.correct_indices)
        selected_list = sorted(selected_indices)
        self.records[question_id] = {
            "selected_indices": selected_list,
            "selected_answers": [question.answers[index] for index in selected_list],
            "selected_index": selected_list[0] if len(selected_list) == 1 else -1,
            "selected_answer": question.answers[selected_list[0]] if len(selected_list) == 1 else None,
            "submitted": True,
            "correct": is_correct,
            "timed_out": False,
        }

        if self.timer_enabled:
            self._stop_timer(clear=False)
            self.timer_label.config(text="--:--")

        self._set_answer_controls(False)
        self.submit_button.config(state="disabled")
        self.next_button.config(state="normal")
        self.status_label.config(text="Correct." if is_correct else "Wrong.")
        self._show_result_badge(is_correct)
        self._apply_answer_result_borders(
            question_id, selected_indices, is_correct
        )
        self._update_correct_answer_checks(question, self.records[question_id])
        self._update_explanation_panel(question, self.records[question_id])
        self._refresh_navigator()
        self._show_result_overlay(is_correct)

    def _on_window_unmap(self, event: tk.Event) -> None:
        if event.widget is self and self.overlay is not None:
            try:
                self.overlay.withdraw()
            except tk.TclError:
                pass

    def _on_window_map(self, event: tk.Event) -> None:
        if event.widget is self and self.overlay is not None:
            self._schedule_overlay_reposition()

    def _schedule_overlay_reposition(self) -> None:
        if self.overlay is None:
            return

        try:
            # Hide it during maximize, restore, or resize transitions so an
            # old overlay rectangle can never cover the newly sized window.
            self.overlay.withdraw()
        except tk.TclError:
            return

        if self.overlay_reposition_job is not None:
            try:
                self.after_cancel(self.overlay_reposition_job)
            except tk.TclError:
                pass

        # Configure events arrive in a burst. Restore only after they stop.
        self.overlay_reposition_job = self.after(
            120,
            self._restore_overlay_after_resize,
        )

    def _restore_overlay_after_resize(self) -> None:
        self.overlay_reposition_job = None
        if self.overlay is None:
            return

        try:
            if self.state() == "iconic":
                return

            self.update_idletasks()
            self.question_area.update_idletasks()
            self._position_result_overlay()
            self.overlay.attributes("-alpha", self.overlay_alpha)
            self.overlay.deiconify()
            self.overlay.lift()
            self._make_overlay_click_through()

            # Windows can perform one final geometry adjustment after a
            # maximize animation. Correct for that without hiding again.
            self.after(80, self._position_result_overlay)
        except tk.TclError:
            self._remove_overlay()

    def _make_overlay_click_through(self) -> None:
        """Prevent the visual overlay from capturing mouse clicks on Windows."""
        if self.overlay is None or not sys.platform.startswith("win"):
            return

        try:
            import ctypes

            hwnd = self.overlay.winfo_id()
            get_style = ctypes.windll.user32.GetWindowLongW
            set_style = ctypes.windll.user32.SetWindowLongW

            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_NOACTIVATE = 0x08000000

            style = get_style(hwnd, GWL_EXSTYLE)
            set_style(
                hwnd,
                GWL_EXSTYLE,
                style
                | WS_EX_TRANSPARENT
                | WS_EX_TOOLWINDOW
                | WS_EX_NOACTIVATE,
            )
        except (AttributeError, OSError, tk.TclError):
            pass

    def _show_result_overlay(self, correct: bool) -> None:
        self._remove_overlay()
        self.question_area.update_idletasks()

        color = "#21a642" if correct else "#c92b2b"

        overlay = tk.Toplevel(self)
        # Keep the overlay invisible until its final screen position is known.
        # Otherwise Windows may briefly draw it at the top-left of the screen.
        overlay.withdraw()
        overlay.overrideredirect(True)
        overlay.transient(self)
        overlay.configure(bg=color)

        # A separate top-level window can blend with the quiz beneath it.
        # A child Canvas cannot be truly transparent.
        self.overlay_alpha = 0.34
        try:
            overlay.attributes("-alpha", self.overlay_alpha)
        except tk.TclError:
            pass

        canvas = tk.Canvas(
            overlay,
            highlightthickness=0,
            bd=0,
            bg=color,
        )
        canvas.pack(fill="both", expand=True)

        self.overlay = overlay
        self.overlay_canvas = canvas
        self.overlay_correct = correct

        # Finish geometry calculations while the overlay is still hidden.
        self.update_idletasks()
        self.question_area.update_idletasks()
        self._position_result_overlay()

        overlay.deiconify()
        overlay.lift()
        self._make_overlay_click_through()

        # Leave the result visible briefly, then fade it smoothly away.
        self.overlay_fade_job = self.after(
            1000,
            self._fade_result_overlay,
        )

    def _fade_result_overlay(self) -> None:
        self.overlay_fade_job = None
        if self.overlay is None:
            return

        self.overlay_alpha = max(0.0, self.overlay_alpha - 0.01)
        if self.overlay_alpha <= 0.0:
            self._remove_overlay()
            return

        try:
            self.overlay.attributes("-alpha", self.overlay_alpha)
        except tk.TclError:
            self._remove_overlay()
            return

        self.overlay_fade_job = self.after(
            50,
            self._fade_result_overlay,
        )

    def _position_result_overlay(self) -> None:
        if (
            self.overlay is None
            or self.overlay_canvas is None
            or self.overlay_correct is None
        ):
            return

        try:
            if not self.overlay.winfo_exists():
                return

            self.question_area.update_idletasks()
            edge_overlap = 2
            width = max(
                1,
                self.question_area.winfo_width() + (edge_overlap * 2),
            )
            height = max(
                1,
                self.question_area.winfo_height() + (edge_overlap * 2),
            )
            x = self.question_area.winfo_rootx() - edge_overlap
            y = self.question_area.winfo_rooty() - edge_overlap

            self.overlay.geometry(f"{width}x{height}+{x}+{y}")

            color = "#21a642" if self.overlay_correct else "#c92b2b"
            word = "CORRECT" if self.overlay_correct else "WRONG"
            font_size = max(34, min(88, int(width / max(8, len(word)))))

            self.overlay_canvas.config(width=width, height=height, bg=color)
            self.overlay_canvas.delete("all")
            self.overlay_canvas.create_rectangle(
                0,
                0,
                width,
                height,
                fill=color,
                outline="",
            )
            self.overlay_canvas.create_text(
                width / 2,
                height / 2,
                text=word,
                angle=35,
                font=("TkDefaultFont", font_size, "bold"),
                fill="white",
            )
            if self.overlay.state() != "withdrawn":
                self.overlay.lift()
        except tk.TclError:
            self._remove_overlay()

    def _remove_overlay(self) -> None:
        if self.overlay_fade_job is not None:
            try:
                self.after_cancel(self.overlay_fade_job)
            except tk.TclError:
                pass
            self.overlay_fade_job = None

        if self.overlay_reposition_job is not None:
            try:
                self.after_cancel(self.overlay_reposition_job)
            except tk.TclError:
                pass
            self.overlay_reposition_job = None

        if self.overlay is not None:
            try:
                self.overlay.destroy()
            except tk.TclError:
                pass
        self.overlay = None
        self.overlay_canvas = None
        self.overlay_correct = None

    def next_question(self) -> None:
        if self._timed_quiz_locked():
            return
        if not self.records[self._current_question_id()].get("submitted"):
            return

        if self.current_index < len(self.questions) - 1:
            self.current_index += 1
            self._display_question()
            return

        self._remove_overlay()
        correct_count = sum(1 for record in self.records if record.get("correct"))
        submitted_count = sum(1 for record in self.records if record.get("submitted"))
        messagebox.showinfo(
            "Quiz complete",
            f"You answered {correct_count} of {submitted_count} questions correctly.",
            parent=self,
        )
        self.status_label.config(
            text=f"Finished: {correct_count}/{submitted_count} correct."
        )

    @staticmethod
    def _blank_record() -> dict[str, Any]:
        return {
            "selected_indices": [],
            "selected_answers": [],
            "selected_index": -1,
            "selected_answer": None,
            "submitted": False,
            "correct": None,
            "timed_out": False,
        }

    def _progress_path(self) -> Path:
        assert self.csv_path is not None
        return APP_DIR / f"{self.csv_path.stem}-progress-{self.attempt_number}.txt"

    def save_progress(self) -> None:
        if self.csv_path is None or not self.questions:
            return

        path = self._progress_path()
        data = {
            "format_version": 6,
            "csv_name": self.csv_path.name,
            "csv_path": str(self.csv_path),
            "attempt_number": self.attempt_number,
            "current_index": self.current_index,
            "question_order": self.question_order,
            "randomize_questions": self.randomization_enabled,
            "answer_orders": self.answer_orders,
            "randomize_answers": self.answer_randomization_enabled,
            "records": self.records,
        }

        try:
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            messagebox.showerror(
                "Could not save progress",
                f"{exc}\n\nThe program folder may not be writable.",
                parent=self,
            )
            return

        self.status_label.config(text=f"Progress saved to {path.name}")
        messagebox.showinfo(
            "Progress saved",
            f"Your progress was saved as:\n{path}",
            parent=self,
        )

    def _find_progress_files(self, csv_path: Path) -> list[Path]:
        pattern = re.compile(
            rf"^{re.escape(csv_path.stem)}-progress-(\d+)\.txt$",
            re.IGNORECASE,
        )
        found: list[tuple[int, Path]] = []
        for path in APP_DIR.glob(f"{csv_path.stem}-progress-*.txt"):
            match = pattern.match(path.name)
            if match:
                found.append((int(match.group(1)), path))
        return [path for _, path in sorted(found)]

    def _next_attempt_number(self, csv_path: Path) -> int:
        numbers = []
        pattern = re.compile(
            rf"^{re.escape(csv_path.stem)}-progress-(\d+)\.txt$",
            re.IGNORECASE,
        )
        for path in self._find_progress_files(csv_path):
            match = pattern.match(path.name)
            if match:
                numbers.append(int(match.group(1)))
        return max(numbers, default=0) + 1

    def _load_progress(self, path: Optional[Path]) -> None:
        if path is None:
            raise ValueError("No progress file was selected.")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid progress file:\n{exc}") from exc

        if self.csv_path is None:
            raise ValueError("No CSV quiz is loaded.")

        saved_csv_name = str(data.get("csv_name", ""))
        if saved_csv_name.casefold() != self.csv_path.name.casefold():
            raise ValueError(
                f'This progress file belongs to "{saved_csv_name}", '
                f'not "{self.csv_path.name}".'
            )

        records = data.get("records")
        if not isinstance(records, list) or len(records) != len(self.questions):
            raise ValueError(
                "The saved attempt does not match the number of questions in this CSV."
            )

        cleaned_records: list[dict[str, Any]] = []
        for idx, record in enumerate(records):
            if not isinstance(record, dict):
                cleaned_records.append(self._blank_record())
                continue

            raw_selected = record.get("selected_indices")
            if isinstance(raw_selected, list):
                selected_indices = sorted({
                    value for value in raw_selected
                    if isinstance(value, int)
                    and 0 <= value < len(self.questions[idx].answers)
                })
            else:
                legacy_selected = record.get("selected_index", -1)
                selected_indices = (
                    [legacy_selected]
                    if isinstance(legacy_selected, int)
                    and 0 <= legacy_selected < len(self.questions[idx].answers)
                    else []
                )

            submitted = bool(record.get("submitted"))
            correct = (
                set(selected_indices) == set(self.questions[idx].correct_indices)
                if submitted else None
            )
            selected_answers = [
                self.questions[idx].answers[value] for value in selected_indices
            ]
            cleaned_records.append(
                {
                    "selected_indices": selected_indices,
                    "selected_answers": selected_answers,
                    "selected_index": selected_indices[0] if len(selected_indices) == 1 else -1,
                    "selected_answer": selected_answers[0] if len(selected_answers) == 1 else None,
                    "submitted": submitted,
                    "correct": correct,
                    "timed_out": bool(record.get("timed_out", False)),
                }
            )

        attempt = data.get("attempt_number")
        if not isinstance(attempt, int) or attempt < 1:
            match = re.search(r"-progress-(\d+)\.txt$", path.name, re.IGNORECASE)
            attempt = int(match.group(1)) if match else 1

        current = data.get("current_index", 0)
        if not isinstance(current, int):
            current = 0

        saved_order = data.get("question_order")
        valid_saved_order = (
            isinstance(saved_order, list)
            and len(saved_order) == len(self.questions)
            and all(isinstance(value, int) for value in saved_order)
            and sorted(saved_order) == list(range(len(self.questions)))
        )
        saved_randomized = data.get("randomize_questions")

        if valid_saved_order:
            self.question_order = list(saved_order)
            self.randomization_enabled = bool(saved_randomized)
        else:
            # Compatibility with v11 progress files, which had no question-order map.
            old_current_question_id = min(max(current, 0), len(self.questions) - 1)
            if self.randomization_enabled:
                self.question_order = self._new_random_question_order()
                current = self.question_order.index(old_current_question_id)
            else:
                self.question_order = list(range(len(self.questions)))

        saved_answer_orders = data.get("answer_orders")
        valid_saved_answer_orders = (
            isinstance(saved_answer_orders, list)
            and len(saved_answer_orders) == len(self.questions)
            and all(
                isinstance(order, list)
                and len(order) == len(self.questions[qid].answers)
                and all(isinstance(value, int) for value in order)
                and sorted(order) == list(range(len(self.questions[qid].answers)))
                for qid, order in enumerate(saved_answer_orders)
            )
        )
        saved_answers_randomized = data.get("randomize_answers")

        if valid_saved_answer_orders:
            self.answer_orders = [list(order) for order in saved_answer_orders]
            self.answer_randomization_enabled = bool(saved_answers_randomized)
        else:
            # Compatibility with older progress files that had no answer-order map.
            if self.answer_randomization_enabled:
                self.answer_orders = self._new_random_answer_orders()
            else:
                self.answer_orders = self._default_answer_orders()

        self.config_data["randomize_questions"] = self.randomization_enabled
        self.config_data["randomize_answers"] = self.answer_randomization_enabled
        self._save_config()

        self.attempt_number = attempt
        self.current_index = min(max(current, 0), len(self.questions) - 1)
        self.records = cleaned_records


def main() -> None:
    app = QuizApp()
    app.mainloop()


if __name__ == "__main__":
    main()
