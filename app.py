"""Voice Banking Dispute Agent - Streamlit app.

Flow: voice -> Google speech-to-text -> regex dispute ID -> Excel lookup -> response -> pyttsx3 voice.
Run with:  streamlit run app.py
"""

import streamlit as st

from dispute_tool import (
    EXAMPLE_QUESTIONS,
    STATUSES,
    answer_query,
    ensure_data_file,
    load_disputes,
    update_dispute_status,
)
from speech_to_text import RequestError, UnknownValueError, transcribe
from text_to_speech import text_to_speech

# Step 1 on startup: create data/disputes.xlsx with sample records if missing
ensure_data_file()

st.set_page_config(page_title="Voice Dispute Agent", page_icon="🏦", layout="centered")
st.title("🏦 Voice Banking Dispute Agent")
st.caption("You can ask, for example: " + " · ".join(f"**{q}**" for q in EXAMPLE_QUESTIONS))


def respond(query_text: str) -> None:
    """Run the business logic and show + speak the answer."""
    st.markdown(f"**You said:** {query_text}")
    reply = answer_query(query_text)
    st.success(reply)
    try:
        st.audio(text_to_speech(reply), format="audio/wav", autoplay=True)
    except Exception as e:  # TTS voice missing/broken should not hide the text answer
        st.warning(f"Could not generate speech: {e}")


# ---------- Ask by voice ----------
st.subheader("🎙️ Ask by voice")
# Browser microphone recorder; returns a WAV file (or None until something is recorded)
audio = st.audio_input("Click the mic, speak, then click stop")

if audio is not None and st.button("Check Dispute", type="primary", width="stretch"):
    text = None
    with st.spinner("Transcribing..."):
        try:
            text = transcribe(audio.getvalue())
        except UnknownValueError:  # Silence, noise or unclear speech
            st.warning("Sorry, I could not understand the audio. Please speak clearly and try again.")
        except RequestError as e:  # No internet / Google service blocked
            st.error(f"Google speech service is unavailable: {e}")
        except ValueError as e:  # Audio is not WAV/FLAC/AIFF
            st.error(f"Unsupported audio format: {e}")
    if text:
        respond(text)

# ---------- Ask by text (handy for testing without a mic) ----------
with st.expander("⌨️ Or type your question"):
    typed = st.text_input("Question", placeholder="Check dispute D1001")
    if st.button("Ask") and typed.strip():
        respond(typed)

# ---------- Admin: update a dispute ----------
st.divider()
st.subheader("🛠️ Update dispute status")
disputes = load_disputes()

with st.form("update_form"):
    col1, col2, col3 = st.columns(3)
    dispute_id = col1.selectbox("Dispute ID", disputes["DisputeID"].tolist())
    status = col2.selectbox("Status", STATUSES)
    expected_days = col3.number_input("Expected days", min_value=0, max_value=60, value=0, step=1)

    if st.form_submit_button("Save"):
        if update_dispute_status(dispute_id=dispute_id, status=status, expected_days=int(expected_days)):
            st.success(f"{dispute_id} updated to '{status}' ({int(expected_days)} days).")
            disputes = load_disputes()  # Reload so the table below shows the change
        else:
            st.error(f"Dispute {dispute_id} not found.")

# ---------- Current data ----------
st.subheader("📋 Current disputes (data/disputes.xlsx)")
st.dataframe(disputes, hide_index=True, width="stretch")
