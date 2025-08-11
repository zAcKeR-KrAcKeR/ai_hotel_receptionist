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

        if event.lower() in ("start", "incoming", "call_attempt"):
            from agents.tts_tool import AzureTTSTool  # ✅ Fixed class name
            tts = AzureTTSTool()
            greeting_text = "Welcome to Grand Hotel. How can I help you today?"
            wav_path = tts.synthesize_speech(greeting_text)

            if not wav_path or not os.path.exists(wav_path):
                resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Welcome to Grand Hotel. How can I help you today?</Say>
    <Hangup/>
</Response>"""
                return Response(content=resp, media_type="application/xml")

            new_path = os.path.join(AUDIO_DIR, f"greeting_{call_sid}.wav")
            os.rename(wav_path, new_path)
            audio_url = f"{PUBLIC_BASE_URL}/audio/greeting_{call_sid}.wav"

            resp = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Record timeout="5" maxLength="30"/>
</Response>"""
            return Response(content=resp, media_type="application/xml")

        elif event.lower() in ("recorded", "recording_done") and recording_url:
            reply_audio = orchestrator.process_call(recording_url, caller)

            if reply_audio and os.path.exists(reply_audio):
                reply_url = f"{PUBLIC_BASE_URL}/audio/{os.path.basename(reply_audio)}"
                resp = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{reply_url}</Play>
    <Record timeout="5" maxLength="30"/>
</Response>"""
                return Response(content=resp, media_type="application/xml")

            resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Sorry, something went wrong.</Say>
    <Hangup/>
</Response>"""
            return Response(content=resp, media_type="application/xml")

        elif event.lower() in ("completed", "hangup", "end"):
            resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for calling. Goodbye.</Say>
</Response>"""
            return Response(content=resp, media_type="application/xml")

        resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for calling.</Say>
    <Hangup/>
</Response>"""
        return Response(content=resp, media_type="application/xml")

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Sorry, an error occurred.</Say>
    <Hangup/>
</Response>"""
        return Response(content=resp, media_type="application/xml")
