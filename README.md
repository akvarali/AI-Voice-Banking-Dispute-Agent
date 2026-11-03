# 🏦 Voice Banking Dispute Agent

A simple, beginner-friendly voice assistant that answers questions like
**"Check dispute D1001"** by looking up the dispute in an Excel file and replying
in both text and voice.

Two front-ends share the same code and the same Excel file, so you can use either:

| Front-end | Start with | Runs in |
|---|---|---|
| **Web app** (Streamlit) | `streamlit run app.py` | Browser |
| **Desktop app** (Tkinter) | `python desktop_app.py` | Normal Windows window |

---

## 1. How it works

```
 🎙️ You speak             ──►  Streamlit records a WAV file in the browser
 📝 Speech-to-text        ──►  Google Web Speech API (SpeechRecognition library)
 🔎 Find the dispute ID   ──►  Regex finds "D1001" in the text
 📊 Look it up            ──►  pandas reads data/disputes.xlsx
 💬 Build the answer      ──►  e.g. "Your dispute D1001 for $2,500 is currently under review ..."
 🔊 Speak the answer      ──►  pyttsx3 (offline Windows voices) → played in the browser
```

---

## 2. Project structure

```
AI Voice Banking Dispute Agent/
│
├── app.py               # Streamlit web page (UI) – start here
├── desktop_app.py       # Tkinter desktop window (alternative UI)
├── speech_to_text.py    # Voice → text using Google speech recognition
├── dispute_tool.py      # Excel "database": create, search, update disputes
├── text_to_speech.py    # Text → voice using pyttsx3
├── requirements.txt     # Python packages to install
├── README.md            # This file
│
└── data/
    └── disputes.xlsx    # Created automatically on first run
```

| File | What it does |
|---|---|
| `app.py` | Builds the web page: microphone recorder, typed-question box, "Update dispute status" form and the disputes table. |
| `desktop_app.py` | The same features in a Tkinter window: text box, **🎙 Speak** button, answer box, update form and table. |
| `speech_to_text.py` | `transcribe(audio_bytes)` sends a browser recording to Google; `listen_from_microphone()` records from the PC mic (desktop app). |
| `dispute_tool.py` | `ensure_data_file()`, `extract_dispute_id()`, `find_dispute()`, `answer_query()` and `update_dispute_status()`. |
| `text_to_speech.py` | `text_to_speech(text)` returns WAV bytes (web app); `speak(text)` plays through the speakers (desktop app). |

---

## 3. Requirements

- **Windows 10/11**
- **Python 3.10 or newer, 64-bit** (check with `py -3.13 --version`)
- **Internet access** to `google.com` (needed for speech-to-text only)
- A **microphone** and a browser (Chrome or Edge recommended)

Python packages (installed in step 4):

| Package | Why |
|---|---|
| `streamlit` | Web user interface |
| `SpeechRecognition` | Talks to the free Google Web Speech API |
| `PyAudio` | Microphone access for the desktop app |
| `truststore` | Fixes SSL certificate errors behind a company proxy |
| `pandas` + `openpyxl` | Read and write the Excel file |
| `pyttsx3` | Offline text-to-speech |

> No API key or account is required for Google Web Speech.

---

## 4. Setup – step by step

Open **PowerShell** and run each step.

### Step 1 – Go to the project folder

```powershell
cd "C:\Users\F1G40OG\Automation\Learning\AI Voice Agent\AI Voice Banking Dispute Agent"
```

### Step 2 – Create a virtual environment

A virtual environment keeps this project's packages separate from other projects.

```powershell
py -3.13 -m venv .venv
```

> Use `py -3.13` (64-bit) rather than `python`, because `python` on this machine
> points to a 32-bit install that cannot install some packages.

### Step 3 – Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

Your prompt should now start with `(.venv)`.

> If you get *"running scripts is disabled on this system"*, run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` and try again.

### Step 4 – Install the packages

```powershell
$env:PIP_USER = "0"          # this machine's pip defaults to --user, which breaks venvs
pip install -r requirements.txt
```

### Step 5 – Start the app (choose one, or both)

**Option A – Web app (Streamlit)**

```powershell
streamlit run app.py
```

The browser opens automatically at **http://localhost:8501**.
To stop it press **Ctrl + C** in PowerShell.

**Option B – Desktop app (Tkinter)**

```powershell
python desktop_app.py
```

A Windows window opens. Close the window to stop it.

> Tkinter comes with Python on Windows – nothing extra to install.
> Both apps can run at the same time; they share `data\disputes.xlsx`.

On the very first start, `data\disputes.xlsx` is created with sample data.

---

## 5. Using the app

### Desktop app (Tkinter)

```
┌─ Ask about a dispute ──────────────────────────────────────┐
│ [ Check dispute D1001          ] [Ask] [🎙 Speak]    │
│ ☑ Read the answer aloud                              │
│ Answer: Your dispute D1001 is currently under review │
├─ Update dispute status ──────────────────────────────────┤
│ [D1001 ▼] [Under Review ▼] [5 ▲▼] [Save]              │
├─ Current disputes ───────────────────────────────────────┤
│ DisputeID | CustomerName | Amount | Status | Days    │
└─────────────────────────────────────────────────────┘
```

- **Type** a question and press **Enter** (or click **Ask**).
- **Speak**: pick your **Microphone** (e.g. your headset), click **🎙 Speak**, stay quiet while the
  status bar says *"Calibrating microphone..."*, then when it shows *"🎙 Speak now..."* ask your question.
  Recording stops automatically when you pause. What Google heard is placed in the text box.
- Untick **Read the answer aloud** to get text-only answers.
- **Click a row** in the table to pre-fill the update form, change values, click **Save**.

### Web app (Streamlit)

#### Ask by voice
1. Click the **microphone** icon and allow microphone access in the browser.
2. Say clearly: **"Check dispute D1001"**.
3. Click the **stop** icon.
4. Click **Check Dispute**.
5. The app shows what you said, the answer, and plays the answer aloud.

#### Ask by typing (no microphone needed)
1. Expand **"⌨️ Or type your question"**.
2. Type `Check dispute D1003` and click **Ask**.

#### Update a dispute
1. In **"🛠️ Update dispute status"**, choose the Dispute ID, the new Status and Expected days.
2. Click **Save** – the Excel file is updated and the table refreshes.

### Ways to ask a question
The app understands different sentence patterns. The **dispute ID** is found with regex, and
keywords decide how the answer starts (the "intent"):

| You ask | Intent (keyword) | Answer starts with |
|---|---|---|
| "Check dispute D1001" | check (default) | "Your dispute D1001 for $2,500 is currently under review..." |
| "Can you check dispute D1001?" | check (default) | "Your dispute D1001 for $2,500 is currently under review..." |
| "What is the status of dispute D1001?" | status (`status`) | "The status of dispute D1001 for $2,500 is Under Review. It is expected..." |
| "Tell me the latest update on D1001" | update (`latest`, `update`, `progress`, `news`) | "Here is the latest update on dispute D1001 for $2,500. It is currently..." |

To add a new intent, add a line to `INTENT_PATTERNS` and an opener in `build_response()`
in `dispute_tool.py`.

### Accepted ways to say a dispute ID
Speech engines often mis-hear the letter "D" or write numbers as words, so all of these work:

| Spoken / typed | Detected ID |
|---|---|
| "Check dispute D1001" | D1001 |
| "check dispute d 1003" / "D-1003" | D1003 |
| "check dispute the 1004" / "B1004" | D1004 |
| "check dispute 1002" | D1002 |
| "check dispute D one zero zero five" | D1005 |
| "check dispute D1 double zero 1" | D1001 |
| "check dispute D1,001" | D1001 |

For voice input, Google returns several possible transcripts; the app automatically
picks the one that contains a dispute ID.

---

## 6. Sample data

`data/disputes.xlsx` is created automatically if it does not exist:

| DisputeID | CustomerName | Amount | Status | ExpectedDays |
|---|---|---|---|---|
| D1001 | John Smith | 2500 | Under Review | 5 |
| D1002 | Sarah Jones | 1500 | Resolved | 0 |
| D1003 | Michael Lee | 3200 | Pending Documents | 3 |
| D1004 | David Brown | 5000 | Under Review | 7 |
| D1005 | Lisa Clark | 1200 | Closed | 0 |

To start fresh, close the file in Excel, delete `data\disputes.xlsx` and restart the app.

### Example answers

| Status | Answer |
|---|---|
| Under Review | "Your dispute D1001 for $2,500 is currently under review and is expected to be resolved within five working days." |
| Pending Documents | "Your dispute D1003 for $3,200 is pending documents. Please submit the required documents. Once received, it is expected to be resolved within three working days." |
| Resolved | "Your dispute D1002 for $1,500 has been resolved." |
| Closed | "Your dispute D1005 for $1,200 has been closed." |
| Unknown ID | "Sorry, I could not find any dispute with ID D9999." |
| No ID in the question | "Sorry, I could not find a dispute ID. You can ask, for example: ..." |

---

## 7. Using the functions from Python

```python
from dispute_tool import answer_query, update_dispute_status

print(answer_query("Check dispute D1001"))

# Returns True if the dispute was found and saved, otherwise False
update_dispute_status(dispute_id="D1001", status="Resolved", expected_days=0)
```

Quick self-test from PowerShell:

```powershell
python dispute_tool.py
```

---

## 8. Troubleshooting

| Problem | Solution |
|---|---|
| **"Google speech service is unavailable"** | Check your internet connection. On a company network, make sure `truststore` is installed (`pip install truststore`). |
| **"Sorry, I could not understand the audio"** | Speak closer to the mic, reduce background noise, and say the ID slowly ("D – one zero zero one"). |
| **No microphone button / mic blocked** | Allow microphone access in the browser (lock icon in the address bar). Use Chrome or Edge. |
| **`PermissionError` when saving** | `disputes.xlsx` is open in Excel – close it and try again. |
| **No sound for the answer** | The text answer is still shown. Check Windows has a voice installed: *Settings → Time & Language → Speech*. |
| **`streamlit` is not recognized** | Activate the virtual environment first (Step 3). |
| **Desktop: "Could not use the microphone"** | Run `pip install pyaudio`, plug in / enable a mic, and allow apps to use the microphone in *Windows Settings → Privacy → Microphone*. |
| **Desktop: "I didn't hear anything"** | Start speaking within 8 seconds of *"🎙 Speak now..."*, and check the right **Microphone** is selected. |
| **Desktop: words missing / wrong text** | Wait for *"Speak now"* before talking (the first second is used to measure background noise), speak at normal volume, and say the ID clearly: "D – one zero zero one". |
| **Desktop: `No module named tkinter`** | Re-install Python from python.org and tick *"tcl/tk and IDLE"*. |

---

## 9. Notes

- The Excel file is a **simple demo database** – fine for learning, not for many users at once.
- Speech-to-text sends your recording to Google; text-to-speech runs fully offline.
