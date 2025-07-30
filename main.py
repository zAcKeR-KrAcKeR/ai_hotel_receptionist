from fastapi import FastAPI, Request, Response
from orchestrator import process_call
from dotenv import load_dotenv
import logging

load_dotenv()
app = FastAPI()
logger = logging.getLogger("uvicorn.error")

@app.get("/")
async def health_check():
    return {"status": "OK", "service": "AI Receptionist"}

@app.get("/kookoo_webhook")
async def kookoo_webhook(request: Request):
    params = request.query_params

    caller = params.get("cid")
    event = params.get("event")
    recording_url = params.get("data")

    logger.info(f"Received webhook event '{event}' from caller '{caller}'")

    if event == "NewCall":
        xml_response = """
        <Response>
            <Say>Welcome to Grand Hotel. How can I assist you today?</Say>
            <Record>
                <MaxDuration>30</MaxDuration>
                <SilenceTimeout>5</SilenceTimeout>
            </Record>
        </Response>
        """
        return Response(content=xml_response.strip(), media_type="application/xml")

    elif event == "Record":
        if not recording_url:
            logger.error(f"No audio URL passed in Record event for caller '{caller}'")
            return Response(
                content="<Response><Say>Sorry, no audio was captured. Please speak after the beep next time.</Say></Response>",
                media_type="application/xml",
            )

        # Process audio and generate TTS response
        response_audio_url = process_call(recording_url, caller)

        if response_audio_url:
            return Response(content=f"<Response><PlayAudio>{response_audio_url}</PlayAudio></Response>", media_type="application/xml")
        else:
            return Response(content="<Response><Say>Sorry, we could not understand you. Please try again.</Say></Response>", media_type="application/xml")

    elif event == "Disconnect":
        logger.info(f"Call disconnected for caller '{caller}'")
        return Response(content="<Response></Response>", media_type="application/xml")

    return Response(content="<Response><Say>Thank you for calling. Goodbye!</Say></Response>", media_type="application/xml")
