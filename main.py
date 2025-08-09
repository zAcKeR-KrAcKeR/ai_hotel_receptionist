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
app = FastAPI()
logger = logging.getLogger("uvicorn.error")

app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")
PUBLIC_URL = os.getenv("PUBLIC_BASE_URL", "https://your-render-url.onrender.com").rstrip("/")

@app.api_route("/exotel_webhook", methods=["GET", "POST"])
async def exotel_webhook(request: Request):
    data = await request.form() if request.method == "POST" else request.query_params
    event = data.get("EventType")
    call_sid = data.get("CallSid") or str(uuid.uuid4())
    caller = data.get("From")
    recording_url = data.get("RecordingUrl")
    logger.info(f"Exotel event: {event}, sid: {call_sid}, caller: {caller}")

    if event in ("start", "incomingcall", "newcall"):
        from agents.tts_tool import tts_tool
        greeting_text = "Welcome to Grand Hotel. How may I assist you today?"
        greeting_wav = tts_tool.synthesize_speech(greeting_text)
        greeting_fname = f"greeting_{call_sid}.wav"
        greeting_path = os.path.join(AUDIO_DIR, greeting_fname)
        os.rename(greeting_wav, greeting_path)
        public_url = f"{PUBLIC_URL}/audio/{greeting_fname}"
        exotel_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{public_url}</Play>
    <Record timeout="5" maxDuration="30"/>
</Response>'''
        return Response(content=exotel_xml, media_type="application/xml")

    elif event in ("record", "RecordingDone") and recording_url:
        try:
            reply_audio = orchestrator.process_call(recording_url, caller)
        except Exception:
            xml = "<?xml version='1.0' encoding='UTF-8'?><Response><Say>Sorry, something went wrong. Please try later.</Say><Hangup/></Response>"
            return Response(content=xml, media_type="application/xml")
        if reply_audio and os.path.exists(reply_audio):
            fname = os.path.basename(reply_audio)
            reply_url = f"{PUBLIC_URL}/audio/{fname}"
            xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{reply_url}</Play>
    <Record timeout="5" maxDuration="30"/>
</Response>"""
        else:
            xml = "<?xml version='1.0' encoding='UTF-8'?><Response><Say>Sorry, response failed.</Say><Hangup/></Response>"
        return Response(content=xml, media_type="application/xml")

    elif event in ("completed", "hangup"):
        return Response(
            "<?xml version='1.0' encoding='UTF-8'?><Response><Say>Thank you for calling. Goodbye!</Say></Response>",
            media_type="application/xml"
        )

    return Response(
        "<?xml version='1.0' encoding='UTF-8'?><Response><Say>Thank you for calling. Goodbye!</Say></Response>",
        media_type="application/xml"
    )
