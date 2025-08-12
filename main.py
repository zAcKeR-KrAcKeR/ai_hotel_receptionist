from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
import logging
import os
import uuid
import json

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
            logger.info("Handling call-attempt - providing greeting")
            
            # ✅ Return JSON that answers the call and plays greeting
            response_data = {
                "fetch_after_attempt": False,
                "destination": {
                    "numbers": []  # ✅ Empty - no agents to call
                },
                "record": True,
                "recording_channels": "single", 
                "max_conversation_duration": 300,
                "start_call_playback": {
                    "playback_to": "both",
                    "type": "text",
                    "value": "Welcome to Grand Hotel. How can I help you today? Please speak after the beep."
                }
            }
            
            logger.info(f"Returning greeting response: {response_data}")
            return Response(
                content=json.dumps(response_data),
                media_type="application/json"
            )
        
        elif call_type == "completed" and recording_url:
            logger.info(f"Processing completed call with recording: {recording_url}")
            
            try:
                reply_audio = orchestrator.process_call(recording_url, caller)
                
                if reply_audio and os.path.exists(reply_audio):
                    reply_url = f"{PUBLIC_BASE_URL}/audio/{os.path.basename(reply_audio)}"
                    logger.info(f"Generated AI reply audio: {reply_url}")
                    
                    response_data = {
                        "fetch_after_attempt": False,
                        "destination": {
                            "numbers": []
                        },
                        "start_call_playback": {
                            "playback_to": "both",
                            "type": "audio_url", 
                            "value": reply_url
                        }
                    }
                    
                    return Response(
                        content=json.dumps(response_data),
                        media_type="application/json"
                    )
                else:
                    response_data = {
                        "fetch_after_attempt": False,
                        "destination": {
                            "numbers": []
                        },
                        "start_call_playback": {
                            "playback_to": "both",
                            "type": "text",
                            "value": "Thank you for your inquiry. We will get back to you soon."
                        }
                    }
                    
                    return Response(
                        content=json.dumps(response_data),
                        media_type="application/json"
                    )
                    
            except Exception as e:
                logger.error(f"Error processing recording: {e}")
        
        # Default response
        logger.info(f"Handling default case for CallType: {call_type}")
        response_data = {
            "fetch_after_attempt": False,
            "destination": {
                "numbers": []
            }
        }
        
        return Response(
            content=json.dumps(response_data),
            media_type="application/json"
        )

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        error_response = {
            "fetch_after_attempt": False,
            "destination": {
                "numbers": []
            }
        }
        return Response(
            content=json.dumps(error_response),
            media_type="application/json"
        )
