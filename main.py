from fastapi import FastAPI, Request, Response, UploadFile, File
from fastapi.staticfiles import StaticFiles
import logging
import os
import uuid
from orchestrator import orchestrator
from dotenv import load_dotenv
from datetime import datetime
import shutil
import tempfile

AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

load_dotenv()

logger = logging.getLogger("uvicorn.error")

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://ai-hotel-receptionist.onrender.com").rstrip("/")

app = FastAPI(
    title="AI Hotel Receptionist API",
    description="An AI-powered hotel receptionist that handles calls via Exotel and Amazon Connect",
    version="1.0.0"
)

app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

# Track conversation state for multiple applets
conversation_states = {}

# ========== ROOT ROUTE - FIXES 404 ERROR ==========
@app.get("/")
async def root():
    return {
        "message": "AI Hotel Receptionist API is running!",
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "exotel_webhook": "/exotel_webhook",
            "amazon_connect_audio": "/amazon_connect_audio",
            "docs": "/docs"
        }
    }

# ========== HEALTH CHECK ENDPOINT ==========
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "AI Hotel Receptionist",
        "active_conversations": len(conversation_states),
        "uptime": "running"
    }

# ========== EXOTEL WEBHOOK INTEGRATION ==========
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
        
        # Initialize conversation state
        if call_sid not in conversation_states:
            conversation_states[call_sid] = {"step": 1}
        
        current_step = conversation_states[call_sid]["step"]
        
        if call_type == "call-attempt" and current_step == 1:
            logger.info("Step 1: Playing greeting and starting recording")
            conversation_states[call_sid]["step"] = 2
            
            # ✅ CORRECT XML format for greeting + recording
            resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Welcome to Grand Hotel. How can I help you today? Please speak after the beep.</Say>
    <Record maxLength="30" timeout="5" />
</Response>"""
            
            logger.info("Returning proper XML greeting with recording")
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
    <Record maxLength="30" timeout="5" />
</Response>"""
                    
                    return Response(content=resp, media_type="application/xml")
                
                else:
                    # ✅ Fallback response
                    resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for your inquiry. Is there anything else I can help you with?</Say>
    <Record maxLength="30" timeout="5" />
</Response>"""
                    
                    return Response(content=resp, media_type="application/xml")
            
            except Exception as e:
                logger.error(f"Error processing recording: {e}")
                
                resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Sorry, I didn't catch that. Could you please repeat your request?</Say>
    <Record maxLength="30" timeout="5" />
</Response>"""
                
                return Response(content=resp, media_type="application/xml")
        
        elif call_type in ("hangup", "completed", "end"):
            logger.info(f"Call ended for caller: {caller}")
            
            # Clean up conversation state
            if call_sid in conversation_states:
                del conversation_states[call_sid]
            
            resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for calling Grand Hotel. Goodbye!</Say>
</Response>"""
            
            return Response(content=resp, media_type="application/xml")
        
        # Handle subsequent call-attempt calls (multiple applets)
        elif call_type == "call-attempt" and current_step > 1:
            logger.info(f"Subsequent call-attempt (step {current_step}) - waiting for recording")
            
            # ✅ Just continue recording without repeating greeting
            resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Record maxLength="30" timeout="5" />
</Response>"""
            
            return Response(content=resp, media_type="application/xml")
        
        # Default case
        logger.info(f"Default case for CallType: {call_type}")
        
        resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>How can I assist you today?</Say>
    <Record maxLength="30" timeout="5" />
</Response>"""
        
        return Response(content=resp, media_type="application/xml")
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        
        resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Sorry, there was an error. Please try again.</Say>
</Response>"""
        
        return Response(content=resp, media_type="application/xml")

# ========== AMAZON CONNECT INTEGRATION ==========
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
        # Clean up temporary file
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)

# ========== ADDITIONAL API INFO ENDPOINT ==========
@app.get("/info")
async def api_info():
    return {
        "name": "AI Hotel Receptionist",
        "description": "An AI-powered hotel receptionist system with multi-provider support",
        "features": [
            "Exotel webhook integration",
            "Amazon Connect support", 
            "Speech-to-Text processing",
            "AI-powered responses",
            "Text-to-Speech synthesis",
            "Conversation state management"
        ],
        "supported_formats": ["WAV", "MP3"],
        "providers": ["Exotel", "Amazon Connect"],
        "endpoints": {
            "/": "API welcome message",
            "/health": "Health check with conversation stats",
            "/exotel_webhook": "Exotel call handling webhook",
            "/amazon_connect_audio": "Process audio from Amazon Connect",
            "/docs": "Interactive API documentation",
            "/info": "API information and features"
        }
    }
