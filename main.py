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
            logger.info("Handling call-attempt - answering call directly")
            
            # ✅ Answer the call by "connecting" back to the caller
            response_data = {
                "fetch_after_attempt": False,
                "destination": {
                    "numbers": [caller]  # ✅ Call back the same caller to "answer"
                },
                "record": True,
                "recording_channels": "single",
                "max_conversation_duration": 300,
                "start_call_playback": {
                    "playback_to": "callee",  # ✅ Play to the person being called
                    "type": "text",
                    "value": "Welcome to Grand Hotel. How can I help you today? Please speak after the beep."
                }
            }
            
            logger.info(f"Returning call answer response: {response_data}")
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
                    
                    # ✅ Play AI response back to caller
                    response_data = {
                        "fetch_after_attempt": False,
                        "destination": {
                            "numbers": [caller]  # Call back to deliver AI response
                        },
                        "start_call_playback": {
                            "playback_to": "callee",
                            "type": "audio_url", 
                            "value": reply_url
                        }
                    }
                    
                    return Response(
                        content=json.dumps(response_data),
                        media_type="application/json"
                    )
                else:
                    # ✅ Fallback text response
                    response_data = {
                        "fetch_after_attempt": False,
                        "destination": {
                            "numbers": [caller]
                        },
                        "start_call_playback": {
                            "playback_to": "callee",
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
                # Return fallback response on error
                response_data = {
                    "fetch_after_attempt": False,
                    "destination": {
                        "numbers": [caller]
                    },
                    "start_call_playback": {
                        "playback_to": "callee",
                        "type": "text",
                        "value": "Sorry, I didn't catch that. Could you please repeat your request?"
                    }
                }
                
                return Response(
                    content=json.dumps(response_data),
                    media_type="application/json"
                )
        
        # ✅ Handle other call types
        elif call_type in ("hangup", "completed", "end"):
            logger.info(f"Call ended for caller: {caller}")
            response_data = {
                "fetch_after_attempt": False,
                "destination": {
                    "numbers": []  # No further action needed
                }
            }
            
            return Response(
                content=json.dumps(response_data),
                media_type="application/json"
            )
        
        # Default response for unhandled call types
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
        # ✅ Always return valid JSON even on errors
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
