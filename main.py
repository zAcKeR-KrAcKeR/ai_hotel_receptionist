from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
import logging
import os
import uuid

from orchestrator import orchestrator
from dotenv import load_dotenv

AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

load_dotenv()
logger = logging.getLogger("uvicorn.error")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://ai-hotel-receptionist.onrender.com").rstrip("/")

app = FastAPI()
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

@app.api_route("/exotel_webhook", methods=["GET", "POST"])
async def exotel_webhook(request: Request):
    try:
        data = await request.form() if request.method == "POST" else request.query_params
        params = dict(data)
        logger.info(f"Exotel Params: {params}")
        
        event = params.get("EventType") or params.get("event") or params.get("CallType") or "start"
        call_sid = params.get("CallSid") or str(uuid.uuid4())
        caller = params.get("From") or params.get("Caller")
        recording_url = params.get("RecordingUrl")

        logger.info(f"Processing event: {event} for caller: {caller}")

        if event.lower() in ("start", "incoming", "call_attempt"):
            logger.info("Generating greeting TTS...")
            
            # Check Azure credentials
            azure_key = os.getenv("AZURE_SPEECH_KEY")
            azure_region = os.getenv("AZURE_SPEECH_REGION")
            
            if not azure_key or not azure_region:
                logger.error("Azure Speech credentials missing!")
                resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Welcome to Grand Hotel. How can I help you today?</Say>
    <Record timeout="10" maxLength="30"/>
</Response>"""
                return Response(content=resp, media_type="application/xml")

            try:
                # ✅ Import and create TTS instance directly
                from agents.tts_tool import AzureTTSTool
                tts_instance = AzureTTSTool()
                greeting_text = "Welcome to Grand Hotel. How can I help you today?"
                
                # ✅ Call synthesize_speech as a regular method
                wav_path = tts_instance.synthesize_speech(greeting_text)
                logger.info(f"TTS generated file: {wav_path}")

                if not wav_path or not os.path.exists(wav_path):
                    logger.warning("TTS failed, using fallback Say")
                    resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Welcome to Grand Hotel. How can I help you today?</Say>
    <Record timeout="10" maxLength="30"/>
</Response>"""
                    return Response(content=resp, media_type="application/xml")

                new_path = os.path.join(AUDIO_DIR, f"greeting_{call_sid}.wav")
                os.rename(wav_path, new_path)
                audio_url = f"{PUBLIC_BASE_URL}/audio/greeting_{call_sid}.wav"
                
                logger.info(f"Playing greeting audio: {audio_url}")

                resp = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Record timeout="10" maxLength="30"/>
</Response>"""
                return Response(content=resp, media_type="application/xml")

            except Exception as tts_error:
                logger.error(f"TTS Error: {tts_error}")
                resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Welcome to Grand Hotel. How can I help you today?</Say>
    <Record timeout="10" maxLength="30"/>
</Response>"""
                return Response(content=resp, media_type="application/xml")

        # Handle other events...
        resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for calling Grand Hotel.</Say>
    <Hangup/>
</Response>"""
        return Response(content=resp, media_type="application/xml")

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Sorry, a server error occurred.</Say>
    <Hangup/>
</Response>"""
        return Response(content=resp, media_type="application/xml")
