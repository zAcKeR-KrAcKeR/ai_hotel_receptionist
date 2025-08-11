from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
import logging
import os
import uuid
import tempfile
import azure.cognitiveservices.speech as speechsdk

from orchestrator import orchestrator
from dotenv import load_dotenv

AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

load_dotenv()
logger = logging.getLogger("uvicorn.error")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://ai-hotel-receptionist.onrender.com").rstrip("/")

app = FastAPI()
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

def direct_azure_tts(text: str) -> str:
    """Direct Azure TTS without LangChain validation"""
    try:
        speech_key = os.getenv("AZURE_SPEECH_KEY")
        speech_region = os.getenv("AZURE_SPEECH_REGION")
        
        if not speech_key or not speech_region:
            logger.error("Azure Speech credentials missing")
            return ""
            
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
        speech_config.speech_synthesis_voice_name = "en-IN-NeerNeural"
        
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        audio_config = speechsdk.AudioConfig(filename=temp_file.name)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config, audio_config)
        
        synthesizer.speak_text_async(text).get()
        logger.info(f"Direct TTS synthesized to {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        logger.error(f"Direct TTS error: {e}")
        return ""

@app.api_route("/exotel_webhook", methods=["GET", "POST"])
async def exotel_webhook(request: Request):
    try:
        data = await request.form() if request.method == "POST" else request.query_params
        params = dict(data)
        logger.info(f"Exotel Params: {params}")
        
        event = params.get("EventType") or params.get("event") or params.get("CallType") or "start"
        call_sid = params.get("CallSid") or str(uuid.uuid4())
        caller = params.get("From") or params.get("Caller")
        recording_url = params.get("RecordingUrl")

        logger.info(f"Processing event: {event} for caller: {caller}")

        if event.lower() in ("start", "incoming", "call_attempt", "call-attempt"):
            logger.info("Generating greeting TTS...")
            
            # Check Azure credentials first
            azure_key = os.getenv("AZURE_SPEECH_KEY")
            azure_region = os.getenv("AZURE_SPEECH_REGION")
            
            # Try Azure TTS first, but always have a fallback
            greeting_text = "Welcome to Grand Hotel. How can I help you today?"
            wav_path = ""
            
            if azure_key and azure_region:
                try:
                    wav_path = direct_azure_tts(greeting_text)
                    logger.info(f"TTS generated file: {wav_path}")
                except Exception as e:
                    logger.error(f"TTS Error: {e}")
                    wav_path = ""

            # If TTS succeeded, use audio file
            if wav_path and os.path.exists(wav_path):
                try:
                    new_path = os.path.join(AUDIO_DIR, f"greeting_{call_sid}.wav")
                    os.rename(wav_path, new_path)
                    audio_url = f"{PUBLIC_BASE_URL}/audio/greeting_{call_sid}.wav"
                    
                    logger.info(f"Playing greeting audio: {audio_url}")

                    resp = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
    <Record timeout="10" maxLength="30"/>
</Response>"""
                    return Response(content=resp, media_type="application/xml")
                except Exception as e:
                    logger.error(f"Audio file handling error: {e}")

            # If TTS failed or audio handling failed, use fallback Say
            logger.warning("Using fallback Say response")
            resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Welcome to Grand Hotel. How can I help you today?</Say>
    <Record timeout="10" maxLength="30"/>
</Response>"""
            return Response(content=resp, media_type="application/xml")

        elif event.lower() in ("recorded", "recording_done", "record") and recording_url:
            logger.info(f"Processing recording: {recording_url}")
            try:
                reply_audio = orchestrator.process_call(recording_url, caller)

                if reply_audio and os.path.exists(reply_audio):
                    reply_url = f"{PUBLIC_BASE_URL}/audio/{os.path.basename(reply_audio)}"
                    logger.info(f"Playing AI reply: {reply_url}")
                    
                    resp = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{reply_url}</Play>
    <Record timeout="10" maxLength="30"/>
</Response>"""
                    return Response(content=resp, media_type="application/xml")
            except Exception as e:
                logger.error(f"AI processing error: {e}")

            # Fallback for recording processing
            resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Sorry, I didn't catch that. Could you please repeat your request?</Say>
    <Record timeout="10" maxLength="30"/>
</Response>"""
            return Response(content=resp, media_type="application/xml")

        elif event.lower() in ("completed", "hangup", "end"):
            resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for calling Grand Hotel. Goodbye!</Say>
</Response>"""
            return Response(content=resp, media_type="application/xml")

        # Default response for unhandled events
        logger.info(f"Unhandled event: {event}, using default response")
        resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for calling Grand Hotel.</Say>
    <Hangup/>
</Response>"""
        return Response(content=resp, media_type="application/xml")

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        # Always return valid XML even on errors
        resp = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Sorry, a server error occurred. Please try again later.</Say>
    <Hangup/>
</Response>"""
        return Response(content=resp, media_type="application/xml")
