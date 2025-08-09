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
        logger.info(f"Exotel webhook params: {params}")

        event = (
            params.get("EventType")
            or params.get("event_type")
            or params.get("CallType")
            or params.get("Direction")
            or "start"
        )
        call_sid = params.get("CallSid") or str(uuid.uuid4())
        caller = params.get("From") or params.get("CallFrom") or params.get("Caller")
        recording_url = params.get("RecordingUrl")

        logger.info(f"[/exotel_webhook] Parsed event={event}, sid={call_sid}, caller={caller}")

        # ---- GREETING LOGIC ----
        if event.lower() in ("start", "newcall", "incomingcall", "incoming", "call-attempt"):
            from agents.tts_tool import AzureTTSTool   # <--- CORRECT!
            tts_tool = AzureTTSTool()
            greeting_text = "Welcome to Grand Hotel. How can I assist you today?"
            greeting_wav = tts_tool.synthesize_speech(greeting_text)

            if not greeting_wav or not os.path.exists(greeting_wav):
                logger.error("TTS synthesis failed, returning fallback Say")
                response_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Welcome to Grand Hotel. How can I assist you today?</Say>
    <Hangup/>
</Response>"""
                return Response(content=response_xml, media_type="application/xml")

            greeting_fname = f"greeting_{call_sid}.wav"
            greeting_path = os.path.join(AUDIO_DIR, greeting_fname)
            os.rename(greeting_wav, greeting_path)
            public_greeting_url = f"{PUBLIC_BASE_URL}/audio/{greeting_fname}"

            response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{public_greeting_url}</Play>
    <Record timeout="5" maxDuration="30"/>
</Response>"""
            return Response(content=response_xml, media_type="application/xml")

        # ---- AI RESPONSE LOGIC ----
        elif event.lower() in ("record", "recordingdone", "recording") and recording_url:
            try:
                reply_audio = orchestrator.process_call(recording_url, caller)
            except Exception as e:
                logger.error(f"orchestrator error: {e}")
                response_xml = """<?xml version='1.0' encoding='UTF-8'?><Response>
                    <Say>Sorry, there was a problem. Please try again later.</Say><Hangup/></Response>"""
                return Response(content=response_xml, media_type="application/xml")

            if reply_audio and os.path.exists(reply_audio):
                fname = os.path.basename(reply_audio)
                reply_url = f"{PUBLIC_BASE_URL}/audio/{fname}"
                response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{reply_url}</Play>
    <Record timeout="5" maxDuration="30"/>
</Response>"""
            else:
                response_xml = """<?xml version='1.0' encoding='UTF-8'?><Response>
                    <Say>Sorry, response failed.</Say><Hangup/></Response>"""
            return Response(content=response_xml, media_type="application/xml")

        # ---- GOODBYE & END ----
        elif event.lower() in ("completed", "hangup", "end"):
            return Response(
                "<?xml version='1.0' encoding='UTF-8'?><Response><Say>Thank you for calling. Goodbye!</Say></Response>",
                media_type="application/xml"
            )

        # ---- DEFAULT / UNKNOWN ----
        return Response(
            "<?xml version='1.0' encoding='UTF-8'?><Response><Say>Thank you for calling.</Say><Hangup/></Response>",
            media_type="application/xml"
        )

    except Exception as e:
        logger.error(f"Fatal server error: {e}")
        response_xml = """<?xml version='1.0' encoding='UTF-8'?><Response>
            <Say>Sorry, a server error occurred.</Say><Hangup/></Response>"""
        return Response(content=response_xml, media_type="application/xml")
