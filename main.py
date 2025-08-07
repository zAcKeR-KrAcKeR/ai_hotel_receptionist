# main.py

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
import logging
import os
import uuid
from orchestrator import orchestrator
from dotenv import load_dotenv

AUDIO_OUTPUT_DIR = "static/audio"
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)
load_dotenv()

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

# Serve audio files publicly (Exotel IVR needs to access them)
app.mount("/audio", StaticFiles(directory=AUDIO_OUTPUT_DIR), name="audio")

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://ai-hotel-receptionist.onrender.com")

@app.post("/exotel_webhook")
async def exotel_webhook(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid")
    caller = form.get("From")
    event = form.get("Status")  # Exotel: "ringing", "in-progress", "completed"
    recording_url = form.get("RecordingUrl")
    logger.info(f"Exotel event '{event}' from '{caller}', CallSid: {call_sid}")

    if event == "ringing":
        # Call is connecting; synthesize and save greeting audio for IVR
        from agents.tts_tool import tts_tool
        greeting_text = "Welcome to Grand Hotel. How can I assist you today?"
        greeting_wav = tts_tool.synthesize_speech(greeting_text)
        greeting_fname = f"greeting_{call_sid or uuid.uuid4().hex}.wav"
        greeting_path = os.path.join(AUDIO_OUTPUT_DIR, greeting_fname)
        os.rename(greeting_wav, greeting_path)
        public_greeting_url = f"{PUBLIC_BASE_URL.rstrip('/')}/audio/{greeting_fname}"
        # Exotel can be set up to play this greeting audio via its Play applet using this public URL
        return Response(content="OK", media_type="text/plain")

    elif event == "completed" and recording_url:
        # Call has ended, with user speech recorded
        try:
            resp_audio_local_path = orchestrator.process_call(recording_url, caller)
            logger.info(f"Processed Exotel recording for {caller}")
        except Exception as e:
            logger.error(f"Error handling Exotel call: {str(e)}")
            return Response(content="Call processing failed", media_type="text/plain")
        return Response(content="Call processed", media_type="text/plain")

    # Optionally handle "in-progress" or other call events here
    return Response(content="No action", media_type="text/plain")
