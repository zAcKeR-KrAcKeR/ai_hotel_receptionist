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

# Track conversation state
conversation_states = {}

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

        # Track conversation state
        if call_sid not in conversation_states:
            conversation_states[call_sid] = {"step": 1}
        
        current_step = conversation_states[call_sid]["step"]

        if call_type == "call-attempt" and current_step == 1:
            logger.info("Step 1: Playing greeting")
            conversation_states[call_sid]["step"] = 2
            
            # Return 200 OK to proceed to next Passthru applet
            return Response(content="greeting", media_type="text/plain", status_code=200)
        
        elif call_type == "call-attempt" and current_step == 2:
            logger.info("Step 2: Starting recording")
            conversation_states[call_sid]["step"] = 3
            
            # Return 200 OK to proceed to next applet
            return Response(content="recording", media_type="text/plain", status_code=200)
        
        elif call_type == "completed" and recording_url:
            logger.info(f"Processing recording: {recording_url}")
            
            try:
                reply_audio = orchestrator.process_call(recording_url, caller)
                
                if reply_audio and os.path.exists(reply_audio):
                    reply_url = f"{PUBLIC_BASE_URL}/audio/{os.path.basename(reply_audio)}"
                    logger.info(f"AI reply ready: {reply_url}")
                    
                    conversation_states[call_sid]["step"] = 2  # Loop back to recording
                    return Response(content="ai_response", media_type="text/plain", status_code=200)
                else:
                    return Response(content="fallback", media_type="text/plain", status_code=200)
                    
            except Exception as e:
                logger.error(f"Error processing recording: {e}")
                return Response(content="error", media_type="text/plain", status_code=200)
        
        # Default case
        return Response(content="default", media_type="text/plain", status_code=200)

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return Response(content="error", media_type="text/plain", status_code=500)
