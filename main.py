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
            logger.info("Handling call-attempt with Passthru - playing greeting")
            
            # ✅ Return XML response for Passthru applet
            resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Welcome to Grand Hotel. How can I help you today? Please speak after the beep.</Say>
    <Record timeout="10" maxLength="30"/>
</Response>"""
            
            logger.info("Returning XML greeting response for Passthru")
            return Response(content=resp, media_type="application/xml")
        
        elif call_type == "completed" and recording_url:
            logger.info(f"Processing completed call with recording: {recording_url}")
            
            try:
                reply_audio = orchestrator.process_call(recording_url, caller)
                
                if reply_audio and os.path.exists(reply_audio):
                    reply_url = f"{PUBLIC_BASE_URL}/audio/{os.path.basename(reply_audio)}"
                    logger.info(f"Generated AI reply audio: {reply_url}")
                    
                    # ✅ Play AI response
                    resp = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{reply_url}</Play>
    <Record timeout="10" maxLength="30"/>
</Response>"""
                    
                    return Response(content=resp, media_type="application/xml")
                else:
                    # ✅ Fallback text response
                    resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for your inquiry. We will get back to you soon.</Say>
    <Hangup/>
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
        
        # ✅ Handle call end
        elif call_type in ("hangup", "completed", "end"):
            logger.info(f"Call ended for caller: {caller}")
            resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for calling Grand Hotel. Goodbye!</Say>
</Response>"""
            
            return Response(content=resp, media_type="application/xml")
        
        # Default response
        logger.info(f"Handling default case for CallType: {call_type}")
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
    <Say>Sorry, a server error occurred. Please try again later.</Say>
    <Hangup/>
</Response>"""
        return Response(content=resp, media_type="application/xml")
