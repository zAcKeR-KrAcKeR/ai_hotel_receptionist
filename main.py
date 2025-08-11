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
PUBLIC_BASE_URL = os.getenv("PUBLIC_URL", "https://your-deployment-url").rstrip("/")

app = FastAPI()
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

@app.api_route("/exotel_webhook", methods=["GET", "POST"])
async def exotel_webhook(request: Request):
    try:
        data = await request.form() if request.method == "POST" else request.query_params
        params = dict(data)
        logger.info(f"Exotel webhook params: {params}")
        event = params.get("EventType") or params.get("event") or params.get("CallType") or "start"
        call_sid = params.get("CallSid") or str(uuid.uuid4())
        caller = params.get("From") or params.get("Caller")

        if event.lower() in ("start", "incoming", "call_attempt"):
            from agents.tts_tool import AzureTTSTool
            tts_tool = AzureTTSTool()
            greeting_text = "Welcome to Grand Hotel. How may I assist you?"
            greeting_wav = tts_tool.synthesize_speech(greeting_text)

            if not greeting_wav or not os.path.exists(greeting_wav):
                xml_resp = "<Response><Say>Welcome to Grand Hotel</Say><Hangup/></Response>"
                return Response(content=xml_resp, media_type="application/xml")

            wav_name = f"greeting_{call_sid}.wav"
            new_path = os.path.join(AUDIO_DIR, wav_name)
            os.rename(greeting_wav, new_path)
            audio_url = f"{PUBLIC_BASE_URL}/audio/{wav_name}"

            xml_resp = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Record timeout="5" maxLength="30"/>
</Response>"""

            return Response(content=xml_resp, media_type="application/xml")

        elif event.lower() in ("recorded", "recording_completed"):
            recording_url = params.get("RecordingUrl")
            reply_wav = orchestrator.process_call(recording_url, caller)
            if reply_wav and os.path.exists(reply_wav):
                reply_name = os.path.basename(reply_wav)
                reply_url = f"{PUBLIC_BASE_URL}/audio/{reply_name}"
                xml_resp = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{reply_url}</Play>
    <Record timeout="5" maxLength="30"/>
</Response>"""
                return Response(content=xml_resp, media_type="application/xml")

            xml_resp = "<Response><Say>Sorry, something went wrong.</Say><Hangup/></Response>"
            return Response(content=xml_resp, media_type="application/xml")

        else:
            xml_resp = "<Response><Say>Thank you for calling. Goodbye.</Say></Response>"
            return Response(content=xml_resp, media_type="application/xml")
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        xml_resp = "<Response><Say>Sorry, a server error occurred.</Say><Hangup/></Response>"
        return Response(content=xml_resp, media_type="application/xml")
