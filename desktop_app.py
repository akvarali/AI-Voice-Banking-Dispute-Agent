"""Voice Banking Dispute Agent - desktop version (Tkinter).

Same business logic as the Streamlit app (app.py), but runs as a normal Windows window.
Run with:  python desktop_app.py
"""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from dispute_tool import (
    EXAMPLE_QUESTIONS,
    STATUSES,
    answer_query,
    ensure_data_file,
    load_disputes,
    update_dispute_status,
)
from speech_to_text import (
    RequestError,
    UnknownValueError,
    WaitTimeoutError,
    list_microphones,
    listen_from_microphone,
)
from text_to_speech import speak

DEFAULT_MIC = "Windows default microphone"


class DisputeAgentApp:
    """Main window: ask by voice or text, see the answer, update disputes, view the table."""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Voice Banking Dispute Agent")
        root.geometry("720x620")
        root.minsize(620, 560)

        # Tkinter variables are automatically linked to the widgets that use them
        self.query_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.speak_reply_var = tk.BooleanVar(value=True)

        self._build_ask_section()
        self._build_update_section()
        self._build_table_section()

        # Status bar at the bottom of the window
        ttk.Label(root, textvariable=self.status_var, relief="sunken", anchor="w").pack(fill="x", side="bottom")

        self.refresh_table()

    # ---------- UI building ----------
    def _build_ask_section(self):
        frame = ttk.LabelFrame(self.root, text=" Ask about a dispute ", padding=10)
        frame.pack(fill="x", padx=10, pady=(10, 5))

        ttk.Label(frame, text="Try: " + "  |  ".join(EXAMPLE_QUESTIONS), foreground="gray", wraplength=660).grid(
            row=0, column=0, columnspan=3, sticky="w"
        )

        entry = ttk.Entry(frame, textvariable=self.query_var, font=("Segoe UI", 11))
        entry.grid(row=1, column=0, sticky="ew", pady=5)
        entry.bind("<Return>", lambda _event: self.ask_text())  # Enter key = click "Ask"
        entry.focus()

        self.ask_button = ttk.Button(frame, text="Ask", command=self.ask_text)
        self.ask_button.grid(row=1, column=1, padx=5)
        self.mic_button = ttk.Button(frame, text="🎙 Speak", command=self.ask_voice)
        self.mic_button.grid(row=1, column=2)

        ttk.Checkbutton(frame, text="Read the answer aloud", variable=self.speak_reply_var).grid(
            row=2, column=0, sticky="w"
        )

        # Microphone picker: the Windows default is not always the headset you are using
        mic_row = ttk.Frame(frame)
        mic_row.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Label(mic_row, text="Microphone:").pack(side="left")
        self.mics = self._load_microphones()  # {display name: device index}
        self.mic_combo = ttk.Combobox(mic_row, values=list(self.mics), state="readonly", width=50)
        self.mic_combo.current(0)
        self.mic_combo.pack(side="left", padx=5)

        ttk.Label(frame, text="Answer:").grid(row=3, column=0, sticky="w", pady=(8, 0))
        # A read-only Text widget wraps long answers nicely (a Label would not)
        self.answer_box = tk.Text(frame, height=4, wrap="word", font=("Segoe UI", 11), state="disabled",
                                  background="#eef7ee")
        self.answer_box.grid(row=4, column=0, columnspan=3, sticky="ew")

        frame.columnconfigure(0, weight=1)  # Let the entry box stretch with the window

    def _build_update_section(self):
        frame = ttk.LabelFrame(self.root, text=" Update dispute status ", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame, text="Dispute ID").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text="Status").grid(row=0, column=1, sticky="w")
        ttk.Label(frame, text="Expected days").grid(row=0, column=2, sticky="w")

        self.id_combo = ttk.Combobox(frame, state="readonly", width=12)
        self.id_combo.grid(row=1, column=0, padx=(0, 10))
        self.status_combo = ttk.Combobox(frame, values=STATUSES, state="readonly", width=20)
        self.status_combo.current(0)
        self.status_combo.grid(row=1, column=1, padx=(0, 10))
        self.days_spin = ttk.Spinbox(frame, from_=0, to=60, width=8)
        self.days_spin.set(0)
        self.days_spin.grid(row=1, column=2, padx=(0, 10))

        ttk.Button(frame, text="Save", command=self.save_update).grid(row=1, column=3)

    def _build_table_section(self):
        frame = ttk.LabelFrame(self.root, text=" Current disputes (data/disputes.xlsx) ", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        columns = ("DisputeID", "CustomerName", "Amount", "Status", "ExpectedDays")
        self.table = ttk.Treeview(frame, columns=columns, show="headings", height=6)
        for col in columns:
            self.table.heading(col, text=col)
            self.table.column(col, width=120, anchor="center")
        self.table.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(fill="y", side="right")

        # Clicking a row pre-fills the update form
        self.table.bind("<<TreeviewSelect>>", self.on_row_selected)

    # ---------- Helpers ----------
    @staticmethod
    def _load_microphones() -> dict:
        mics: dict[str, int | None] = {DEFAULT_MIC: None}
        try:
            mics.update({f"{index}: {name}": index for index, name in list_microphones()})
        except Exception:  # PyAudio missing: only the default entry is shown
            pass
        return mics

    def run_in_background(self, work, on_done):
        """Run slow work (mic, internet, speech) in a thread so the window doesn't freeze.

        Tkinter widgets may only be touched from the main thread, so we poll with after()
        and call on_done(result, error) back on the main thread.
        """
        result = {}

        def worker():
            try:
                result["value"] = work()
            except Exception as e:  # Passed to on_done so it can show a friendly message
                result["error"] = e

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        def check():
            if thread.is_alive():
                self.root.after(100, check)
            else:
                on_done(result.get("value"), result.get("error"))

        check()

    def set_busy(self, busy: bool, message: str = "Ready"):
        state = "disabled" if busy else "normal"
        self.ask_button.config(state=state)
        self.mic_button.config(state=state)
        self.status_var.set(message)

    def show_answer(self, text: str):
        self.answer_box.config(state="normal")
        self.answer_box.delete("1.0", "end")
        self.answer_box.insert("1.0", text)
        self.answer_box.config(state="disabled")

    def respond(self, query: str):
        """Business logic (same as Streamlit): text -> dispute ID -> Excel lookup -> answer."""
        reply = answer_query(query)
        self.show_answer(reply)
        if self.speak_reply_var.get():
            self.set_busy(True, "Speaking...")
            self.run_in_background(lambda: speak(reply), lambda _r, _e: self.set_busy(False))

    # ---------- Button actions ----------
    def ask_text(self):
        query = self.query_var.get().strip()
        if not query:
            messagebox.showinfo("No question", 'Please type a question, e.g. "Check dispute D1001".')
            return
        self.respond(query)

    def ask_voice(self):
        self.set_busy(True, "Calibrating microphone... please stay quiet")
        self.show_answer("")
        device_index = self.mics.get(self.mic_combo.get())

        # Called from the background thread once calibration is done; after() hands it to the UI thread
        def on_ready():
            self.root.after(0, lambda: self.status_var.set("🎙 Speak now..."))

        self.run_in_background(
            lambda: listen_from_microphone(device_index=device_index, on_ready=on_ready),
            self.on_voice_done,
        )

    def on_voice_done(self, text, error):
        self.set_busy(False)
        if error is None:
            self.query_var.set(text)  # Show what Google heard in the input box
            self.status_var.set(f'Heard: "{text}"')
            self.respond(text)
        elif isinstance(error, WaitTimeoutError):
            self.show_answer("I didn't hear anything. Please click Speak and try again.")
        elif isinstance(error, UnknownValueError):
            self.show_answer("Sorry, I could not understand. Please speak clearly and try again.")
        elif isinstance(error, RequestError):
            messagebox.showerror("Speech service", f"Google speech service is unavailable:\n{error}")
        elif isinstance(error, (AttributeError, OSError)):
            # AttributeError: PyAudio not installed; OSError: no microphone found
            messagebox.showerror("Microphone", f"Could not use the microphone.\n"
                                               f"Install PyAudio (pip install pyaudio) and check your mic.\n\n{error}")
        else:
            messagebox.showerror("Error", str(error))

    def save_update(self):
        dispute_id = self.id_combo.get()
        if not dispute_id:
            messagebox.showwarning("Update", "Please choose a Dispute ID.")
            return
        try:
            days = int(self.days_spin.get())
        except ValueError:
            messagebox.showwarning("Update", "Expected days must be a whole number.")
            return

        try:
            ok = update_dispute_status(dispute_id=dispute_id, status=self.status_combo.get(), expected_days=days)
        except PermissionError:
            messagebox.showerror("Update", "Could not save. Please close disputes.xlsx in Excel and try again.")
            return

        if ok:
            self.status_var.set(f"{dispute_id} updated to '{self.status_combo.get()}' ({days} days).")
            self.refresh_table()
        else:
            messagebox.showerror("Update", f"Dispute {dispute_id} not found.")

    def refresh_table(self):
        """Reload the Excel file into the table and the Dispute ID dropdown."""
        df = load_disputes()
        self.table.delete(*self.table.get_children())
        for row in df.itertuples(index=False):
            self.table.insert("", "end", values=list(row))
        self.id_combo["values"] = df["DisputeID"].tolist()

    def on_row_selected(self, _event):
        selected = self.table.selection()
        if not selected:
            return
        dispute_id, _name, _amount, status, days = self.table.item(selected[0], "values")
        self.id_combo.set(dispute_id)
        self.status_combo.set(status)
        self.days_spin.set(days)


if __name__ == "__main__":
    ensure_data_file()  # Create data/disputes.xlsx with sample records if missing
    root = tk.Tk()
    DisputeAgentApp(root)
    root.mainloop()
