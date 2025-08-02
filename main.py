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

# Serve TTS audio publicly at /audio/
app.mount("/audio", StaticFiles(directory=AUDIO_OUTPUT_DIR), name="audio")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://ai-hotel-receptionist.onrender.com")

@app.api_route("/kookoo_webhook", methods=["GET", "POST"])
async def kookoo_webhook(request: Request):
    is_post = request.method == "POST"
    form = await request.form() if is_post else {}
    params = request.query_params

    def pick(key):
        return form.get(key) if key in form else params.get(key)

    caller = pick("cid")
    event = pick("event")
    recording_url = pick("data")
    sid = pick("sid") or str(uuid.uuid4())

    logger.info(f"Received webhook event '{event}' from caller '{caller}'")

    if event == "NewCall":
        from agents.tts_tool import tts_tool

        greeting_text = "Welcome to Grand Hotel. How can I assist you today?"
        # Pass dict per LangChain schema to avoid ValidationError
        greeting_wav = tts_tool.synthesize_speech({"text": greeting_text})

        if not greeting_wav or not os.path.exists(greeting_wav):
            xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <playtext>{greeting_text}</playtext>
    <record maxduration="30" silence="5"/>
</Response>"""
            return Response(content=xml, media_type="application/xml")

        greeting_fname = f"greeting_{sid}.wav"
        greeting_path = os.path.join(AUDIO_OUTPUT_DIR, greeting_fname)
        os.rename(greeting_wav, greeting_path)
        public_greeting_url = f"{PUBLIC_BASE_URL.rstrip('/')}/audio/{greeting_fname}"

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <playaudio>{public_greeting_url}</playaudio>
    <record maxduration="30" silence="5"/>
</Response>"""
        return Response(content=xml, media_type="application/xml")

    elif event == "Record":
        if not recording_url:
            logger.error(f"No audio URL in Record event for caller '{caller}'")
            xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <playtext>Sorry, no audio was captured. Please speak after the beep next time.</playtext>
    <hangup/>
</Response>"""
            return Response(content=xml, media_type="application/xml")
        try:
            resp_audio_local_path = orchestrator.process_call(recording_url, caller)
        except Exception as e:
            logger.exception(f"Error processing call for user {caller}: {str(e)}")
            xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <playtext>There was a problem processing your request. Please try again later.</playtext>
    <hangup/>
</Response>"""
            return Response(content=xml, media_type="application/xml")

        if resp_audio_local_path and os.path.exists(resp_audio_local_path):
            reply_fname = os.path.basename(resp_audio_local_path)
            reply_url = f"{PUBLIC_BASE_URL.rstrip('/')}/audio/{reply_fname}"
            xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <playaudio>{reply_url}</playaudio>
    <record maxduration="30" silence="5"/>
</Response>"""
        else:
            xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <playtext>Sorry, something went wrong. Please try again later.</playtext>
    <hangup/>
</Response>"""

        return Response(content=xml, media_type="application/xml")

    elif event in ("Disconnect", "Hangup"):
        logger.info(f"Call ended by user {caller}")
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <playtext>Thank you for calling. Goodbye!</playtext>
    <hangup/>
</Response>"""
        return Response(content=xml, media_type="application/xml")

    # Default fallback
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <playtext>Thank you for calling. Goodbye!</playtext>
    <hangup/>
</Response>"""
    return Response(content=xml, media_type="application/xml")
