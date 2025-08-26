from fastapi import FastAPI, Request, Response, UploadFile, File
from fastapi.staticfiles import StaticFiles
import logging
import os
import uuid
from orchestrator import orchestrator
from dotenv import load_dotenv
import shutil
import tempfile

AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)
load_dotenv()

logger = logging.getLogger("uvicorn.error")

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://ai-hotel-receptionist.onrender.com").rstrip("/")

app = FastAPI()
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

@app.post("/amazon_connect_audio")
async def amazon_connect_audio(audio: UploadFile = File(...)):
    try:
        logger.info("Received audio from Amazon Connect")

        # Save incoming audio chunk to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            shutil.copyfileobj(audio.file, tmp)
            tmp_path = tmp.name

        logger.info(f"Saved audio to: {tmp_path}")

        # Process audio using orchestrator
        reply_audio_path = orchestrator.process_call(f"file://{tmp_path}", "amazon_connect_caller")

        if reply_audio_path and os.path.exists(reply_audio_path):
            audio_url = f"{PUBLIC_BASE_URL}/audio/{os.path.basename(reply_audio_path)}"
            logger.info(f"Generated AI reply: {audio_url}")
            return {"audio_url": audio_url}

        logger.error("Failed to generate AI reply")
        return {"error": "AI processing failed"}

    except Exception as e:
        logger.error(f"Amazon Connect audio processing error: {e}")
        return {"error": str(e)}

    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
