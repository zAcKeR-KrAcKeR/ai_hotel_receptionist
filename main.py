from fastapi import FastAPI, Request, Response, UploadFile, File
from fastapi.staticfiles import StaticFiles
import logging
import os
import uuid
from orchestrator import orchestrator
from dotenv import load_dotenv
import shutil
import tempfile

# Setup
AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)
load_dotenv()

logger = logging.getLogger("uvicorn.error")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://ai-hotel-receptionist.onrender.com").rstrip('/')

app = FastAPI()
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

# 🔥 AMAZON CONNECT WEBHOOK - REAL-TIME INTEGRATION
@app.api_route("/connect_webhook", methods=["GET", "POST"])
async def connect_webhook(request: Request):
    """Handle Amazon Connect Lambda webhook calls with real-time audio processing"""
    try:
        logger.info(f"Connect webhook called: {request.method}")
        
        # Handle different content types from Lambda/Connect
        if request.method == "POST":
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                data = await request.json()
            else:
                form_data = await request.form()
                data = dict(form_data)
        else:
            data = dict(request.query_params)
        
        logger.info(f"Connect webhook data: {data}")
        
        # Extract parameters from Connect/Lambda
        call_type = data.get("CallType", "connect-call")
        call_sid = data.get("CallSid", str(uuid.uuid4()))
        caller = data.get("From", "connect-caller")
        recording_url = data.get("RecordingUrl")
        speech_text = data.get("SpeechText")
        processing_type = data.get("ProcessingType", "webhook")
        contact_id = data.get("ContactId", call_sid)
        
        logger.info(f"Processing Connect request - Type: {processing_type}, Caller: {caller}")
        
        # Real-time processing based on available data
        if recording_url:
            # Process audio from recording URL (Connect streaming)
            logger.info(f"Processing Connect recording: {recording_url}")
            reply_audio = orchestrator.process_call(recording_url, caller)
            
            if reply_audio and os.path.exists(reply_audio):
                # Get both local and Azure Blob URLs
                reply_url = f"{PUBLIC_BASE_URL}/audio/{os.path.basename(reply_audio)}"
                
                # Upload to Azure Blob for Amazon Connect access
                from blob_storage import blob_storage
                blob_url = blob_storage.upload_audio_file(reply_audio)
                
                logger.info(f"Connect AI reply ready - Local: {reply_url}, Blob: {blob_url}")
                
                return {
                    "statusCode": 200,
                    "body": {
                        "message": "AI response generated successfully",
                        "audioUrl": blob_url or reply_url,  # Prefer blob URL for Connect
                        "localAudioUrl": reply_url,
                        "success": True,
                        "callId": contact_id,
                        "processing": "recording_url",
                        "caller": caller
                    }
                }
            else:
                logger.warning("No audio response generated from Connect recording")
                return {
                    "statusCode": 200,
                    "body": {
                        "message": "Thank you for your inquiry. Our team will get back to you shortly.",
                        "success": False,
                        "callId": contact_id,
                        "processing": "failed"
                    }
                }
                
        elif speech_text:
            # Process with speech text (Connect speech-to-text)
            logger.info(f"Processing Connect speech text: {speech_text}")
            
            try:
                # Use your existing AI pipeline with text input
                from agents.llm_tools import llm_tool
                from agents.autogen_agents import manager
                from agents.tts_tool import AzureTTSTool
                from database.queries import HotelDatabase
                
                # Analyze intent and generate response using your existing pipeline
                intent_data = llm_tool.analyze_intent(speech_text)
                chat_history = [{"role": "user", "content": speech_text}]
                result = manager.run(chat_history)
                
                reply_text = result[-1]["content"] if isinstance(result, list) else str(result)
                logger.info(f"AI text response: {reply_text}")
                
                # Generate TTS for the response using your existing TTS
                tts = AzureTTSTool()
                wav_path = tts.synthesize_speech(reply_text)
                
                if wav_path and os.path.exists(wav_path):
                    output_filename = f"connect_reply_{caller}_{uuid.uuid4().hex}.wav"
                    output_path = os.path.join(AUDIO_DIR, output_filename)
                    os.rename(wav_path, output_path)
                    
                    reply_url = f"{PUBLIC_BASE_URL}/audio/{output_filename}"
                    
                    # Upload to Azure Blob for Connect access
                    from blob_storage import blob_storage
                    blob_url = blob_storage.upload_audio_file(output_path)
                    
                    # Log conversation using your existing DB
                    db = HotelDatabase()
                    db.log_conversation(caller, speech_text, reply_text)
                    
                    return {
                        "statusCode": 200,
                        "body": {
                            "message": reply_text,
                            "audioUrl": blob_url or reply_url,
                            "localAudioUrl": reply_url,
                            "success": True,
                            "callId": contact_id,
                            "processing": "speech_text",
                            "caller": caller
                        }
                    }
                else:
                    logger.error("TTS generation failed for Connect speech text")
                    return {
                        "statusCode": 200,
                        "body": {
                            "message": reply_text,
                            "success": True,
                            "callId": contact_id,
                            "processing": "text_only"
                        }
                    }
                    
            except Exception as e:
                logger.error(f"Error processing Connect speech text: {e}")
                return {
                    "statusCode": 500,
                    "body": {
                        "message": "I'm sorry, I couldn't process your request properly. Could you please try again?",
                        "error": str(e),
                        "callId": contact_id
                    }
                }
        else:
            # No audio data available - return Connect-ready greeting
            logger.info("Connect call initiated - returning greeting")
            return {
                "statusCode": 200,
                "body": {
                    "message": "Welcome to Grand Hotel. I'm your AI assistant. How may I help you today?",
                    "ready": True,
                    "callId": contact_id,
                    "processing": "initial_greeting",
                    "instructions": "Please provide speech text or recording URL for processing"
                }
            }
        
    except Exception as e:
        logger.error(f"Connect webhook error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": {
                "message": "I'm experiencing technical difficulties. Please try again.",
                "error": str(e)
            }
        }

# 🔥 AMAZON CONNECT TEST ENDPOINT
@app.get("/connect_test")
async def connect_test():
    """Test endpoint for Amazon Connect integration"""
    return {
        "status": "ready",
        "service": "AI Hotel Receptionist - Amazon Connect Ready",
        "connect_integration": "active",
        "timestamp": str(uuid.uuid4()),
        "endpoints": {
            "webhook": f"{PUBLIC_BASE_URL}/connect_webhook",
            "audio": f"{PUBLIC_BASE_URL}/audio/",
            "test": f"{PUBLIC_BASE_URL}/connect_test"
        },
        "capabilities": [
            "Real-time speech processing",
            "Azure Blob Storage integration", 
            "Lambda webhook support",
            "Hotel booking and inquiry handling"
        ],
        "version": "2.0-connect"
    }

# 🔥 AMAZON CONNECT AUDIO STREAMING (Enhanced)
@app.post("/amazon_connect_audio")
async def amazon_connect_audio(audio: UploadFile = File(...)):
    """Handle direct audio uploads from Amazon Connect with Blob storage"""
    tmp_path = None
    try:
        logger.info("Received audio stream from Amazon Connect")
        
        # Save incoming audio chunk to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            shutil.copyfileobj(audio.file, tmp)
            tmp_path = tmp.name
            
        logger.info(f"Saved Connect audio to {tmp_path}")
        
        # Process audio using orchestrator
        reply_audio_path = orchestrator.process_call(f"file://{tmp_path}", "amazon_connect_caller")
        
        if reply_audio_path and os.path.exists(reply_audio_path):
            # Get local URL
            audio_url = f"{PUBLIC_BASE_URL}/audio/{os.path.basename(reply_audio_path)}"
            
            # Upload to Azure Blob for Connect access
            from blob_storage import blob_storage
            blob_url = blob_storage.upload_audio_file(reply_audio_path)
            
            logger.info(f"Generated AI reply - Local: {audio_url}, Blob: {blob_url}")
            
            return {
                "audio_url": blob_url or audio_url,
                "local_audio_url": audio_url,
                "blob_url": blob_url,
                "success": True,
                "processing": "direct_upload"
            }
        else:
            logger.error("Failed to generate AI reply for Connect audio")
            return {
                "error": "AI processing failed",
                "success": False
            }
            
    except Exception as e:
        logger.error(f"Amazon Connect audio processing error: {e}")
        return {
            "error": str(e),
            "success": False
        }
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

# 🔥 HEALTH CHECK FOR AMAZON CONNECT
@app.get("/health")
async def health_check():
    """Health check endpoint for Amazon Connect monitoring"""
    return {
        "status": "healthy",
        "service": "AI Hotel Receptionist",
        "connect_ready": True,
        "timestamp": str(uuid.uuid4())
    }
