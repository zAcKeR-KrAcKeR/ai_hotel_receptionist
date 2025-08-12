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
        
        call_type = params.get("CallType", "call-attempt")
        call_sid = params.get("CallSid", str(uuid.uuid4()))
        caller = params.get("From", params.get("CallFrom"))
        recording_url = params.get("RecordingUrl")

        logger.info(f"Processing CallType: {call_type} for caller: {caller}")

        if call_type == "call-attempt":
            logger.info("Handling call-attempt - playing greeting and starting recording")
            
            # ✅ Proper XML response with both greeting and recording
            resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Welcome to Grand Hotel. How can I help you today? Please speak after the beep.</Say>
    <Record timeout="10" maxLength="30"/>
</Response>"""
            
            logger.info("Returning XML with greeting and record")
            return Response(content=resp, media_type="application/xml")
        
        elif call_type == "completed" and recording_url:
            logger.info(f"Processing recording: {recording_url}")
            
            try:
                reply_audio = orchestrator.process_call(recording_url, caller)
                
                if reply_audio and os.path.exists(reply_audio):
                    reply_url = f"{PUBLIC_BASE_URL}/audio/{os.path.basename(reply_audio)}"
                    logger.info(f"AI reply ready: {reply_url}")
                    
                    # ✅ Play AI response and continue recording
                    resp = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{reply_url}</Play>
    <Record timeout="10" maxLength="30"/>
</Response>"""
                    
                    return Response(content=resp, media_type="application/xml")
                else:
                    resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for your inquiry. Is there anything else I can help you with?</Say>
    <Record timeout="10" maxLength="30"/>
</Response>"""
                    
                    return Response(content=resp, media_type="application/xml")
                    
            except Exception as e:
                logger.error(f"Error processing recording: {e}")
                resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Sorry, I didn't catch that. Could you please repeat your request?</Say>
    <Record timeout="10" maxLength="30"/>
</Response>"""
                
                return Response(content=resp, media_type="application/xml")
        
        elif call_type in ("hangup", "completed", "end"):
            logger.info(f"Call ended for caller: {caller}")
            resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for calling Grand Hotel. Goodbye!</Say>
    <Hangup/>
</Response>"""
            
            return Response(content=resp, media_type="application/xml")
        
        # Default case
        logger.info(f"Default case for CallType: {call_type}")
        resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>How can I assist you today?</Say>
    <Record timeout="10" maxLength="30"/>
</Response>"""
        
        return Response(content=resp, media_type="application/xml")

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Sorry, there was an error. Please try again.</Say>
    <Hangup/>
</Response>"""
        return Response(content=resp, media_type="application/xml")
