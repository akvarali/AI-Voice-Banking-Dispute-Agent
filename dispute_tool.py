"""Dispute "database" helpers: the Excel file data/disputes.xlsx acts as a simple table."""

import re
from pathlib import Path

import pandas as pd

# Paths are relative to this file so the app works from any working directory
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "disputes.xlsx"

SAMPLE_DISPUTES = [
    {"DisputeID": "D1001", "CustomerName": "John Smith", "Amount": 2500, "Status": "Under Review", "ExpectedDays": 5},
    {"DisputeID": "D1002", "CustomerName": "Sarah Jones", "Amount": 1500, "Status": "Resolved", "ExpectedDays": 0},
    {"DisputeID": "D1003", "CustomerName": "Michael Lee", "Amount": 3200, "Status": "Pending Documents", "ExpectedDays": 3},
    {"DisputeID": "D1004", "CustomerName": "David Brown", "Amount": 5000, "Status": "Under Review", "ExpectedDays": 7},
    {"DisputeID": "D1005", "CustomerName": "Lisa Clark", "Amount": 1200, "Status": "Closed", "ExpectedDays": 0},
]

STATUSES = ["Under Review", "Pending Documents", "Resolved", "Closed"]

# Spoken numbers sound more natural than digits ("five working days")
NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]

# Speech engines sometimes write digits as words ("D one zero zero one")
WORD_TO_DIGIT = {word: str(i) for i, word in enumerate(NUMBER_WORDS[:10])}
WORD_TO_DIGIT["oh"] = "0"
DIGIT_WORD_PATTERN = re.compile(r"\b(" + "|".join(WORD_TO_DIGIT) + r")\b", re.IGNORECASE)
REPEAT_PATTERN = re.compile(r"\b(double|triple)\s+(\d)", re.IGNORECASE)  # "double zero" -> "00"

# Four digits, optionally split by single spaces/hyphens ("1001", "10 01", "1-0-0-1")
DIGITS = r"((?:\d[\s\-]?){3}\d)(?!\d)"
# 1st choice: digits after "D" or a word that sounds like D ("the", "dee", "de", "di")
PREFIXED_ID_PATTERN = re.compile(r"\b(?:d|dee|de|di|the)[\s.\-]*" + DIGITS, re.IGNORECASE)
# 2nd choice: any 4-digit number ("dispute 1001", or "D" mis-heard as "B1001")
BARE_ID_PATTERN = re.compile(r"(?<!\d)" + DIGITS)

# Intent = what kind of question was asked; it changes how the answer starts.
# Checked in order, first match wins. Anything else is treated as "check".
INTENT_PATTERNS = [
    ("update", re.compile(r"\b(latest|update|updates|progress|news)\b", re.IGNORECASE)),
    ("status", re.compile(r"\bstatus\b", re.IGNORECASE)),
]

EXAMPLE_QUESTIONS = [
    "Check dispute D1001",
    "Can you check dispute D1001?",
    "What is the status of dispute D1001?",
    "Tell me the latest update on D1001",
]


def ensure_data_file() -> None:
    """Create data/disputes.xlsx with sample records if it does not exist yet."""
    if DATA_FILE.exists():
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(SAMPLE_DISPUTES).to_excel(DATA_FILE, index=False)


def load_disputes() -> pd.DataFrame:
    """Read all disputes from the Excel file."""
    ensure_data_file()
    return pd.read_excel(DATA_FILE, dtype={"DisputeID": str})


def normalize_spoken_text(text: str) -> str:
    """Turn speech-style numbers into digits: 'D one zero zero one' / 'D1,001' -> 'D 1 0 0 1' / 'D1001'."""
    text = DIGIT_WORD_PATTERN.sub(lambda m: WORD_TO_DIGIT[m.group(1).lower()], text)
    text = REPEAT_PATTERN.sub(lambda m: m.group(2) * (2 if m.group(1).lower() == "double" else 3), text)
    return re.sub(r"(?<=\d),(?=\d)", "", text)  # "1,001" -> "1001"


def extract_dispute_id(text: str) -> str | None:
    """Pull a dispute ID like 'D1001' out of free text. Returns None if not found."""
    text = normalize_spoken_text(text)
    match = PREFIXED_ID_PATTERN.search(text) or BARE_ID_PATTERN.search(text)
    if not match:
        return None
    digits = re.sub(r"[\s\-]", "", match.group(1))
    return f"D{digits}"


def detect_intent(text: str) -> str:
    """Return 'update', 'status' or 'check' depending on how the question was phrased."""
    for intent, pattern in INTENT_PATTERNS:
        if pattern.search(text):
            return intent
    return "check"


def find_dispute(dispute_id: str) -> dict | None:
    """Return the dispute row as a dict, or None if the ID is not in the file."""
    df = load_disputes()
    rows = df[df["DisputeID"].str.upper() == dispute_id.upper()]
    if rows.empty:
        return None
    return rows.iloc[0].to_dict()


def days_to_words(days: int) -> str:
    return NUMBER_WORDS[days] if 0 <= days < len(NUMBER_WORDS) else str(days)


def build_response(dispute: dict, intent: str = "check") -> str:
    """Turn a dispute record into a friendly sentence that matches the question type."""
    dispute_id = dispute["DisputeID"]
    status = str(dispute["Status"])
    days = int(dispute["ExpectedDays"])
    day_text = f"{days_to_words(days)} working day{'s' if days != 1 else ''}"

    # The opening line depends on what was asked; the details depend on the status
    if intent == "update":
        opener, subject = f"Here is the latest update on dispute {dispute_id}. ", "It"
    elif intent == "status":
        opener, subject = f"The status of dispute {dispute_id} is {status}. ", "It"
    else:
        opener, subject = "", f"Your dispute {dispute_id}"

    if status == "Resolved":
        details = f"{subject} has been resolved."
    elif status == "Closed":
        details = f"{subject} has been closed."
    elif status == "Pending Documents":
        details = (
            f"{subject} is pending documents. Please submit the required documents. "
            f"Once received, it is expected to be resolved within {day_text}."
        )
    else:  # "Under Review" and any other custom status
        details = f"{subject} is currently {status.lower()} and is expected to be resolved within {day_text}."

    return opener + details


def answer_query(text: str) -> str:
    """Full business logic: text -> dispute ID + intent -> lookup -> response sentence."""
    dispute_id = extract_dispute_id(text)
    if dispute_id is None:
        examples = "; ".join(f'"{q}"' for q in EXAMPLE_QUESTIONS)
        return f"Sorry, I could not find a dispute ID. You can ask, for example: {examples}."

    dispute = find_dispute(dispute_id)
    if dispute is None:
        return f"Sorry, I could not find any dispute with ID {dispute_id}."

    return build_response(dispute, detect_intent(text))


def update_dispute_status(dispute_id: str, status: str, expected_days: int) -> bool:
    """Update a dispute's Status and ExpectedDays in disputes.xlsx.

    Returns True if the dispute was found and saved, False otherwise.
    """
    df = load_disputes()
    mask = df["DisputeID"].str.upper() == dispute_id.upper()
    if not mask.any():
        return False

    df.loc[mask, "Status"] = status
    df.loc[mask, "ExpectedDays"] = int(expected_days)
    df.to_excel(DATA_FILE, index=False)
    return True


if __name__ == "__main__":
    # Quick self-test: python dispute_tool.py
    ensure_data_file()
    for question in EXAMPLE_QUESTIONS + ["check dispute d 1003", "Check dispute D9999"]:
        print(f"Q: {question}\nA: {answer_query(question)}\n")
