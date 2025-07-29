from fastapi import FastAPI, Request, Response
import logging
from orchestrator import orchestrator
from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI()
logger = logging.getLogger("uvicorn.error")


@app.get("/")
async def health_check():
    return {"status": "OK", "service": "AI Receptionist"}


@app.post("/kookoo_webhook")
async def kookoo_webhook(request: Request):
    form = await request.form()
    caller = form.get("cid")
    recording_url = form.get("data")
    event = form.get("event")
    logger.info(f"Received webhook event '{event}' from caller '{caller}'")

    if event == "NewCall":
        reply = """
        <Response>
            <Say>Welcome to Grand Hotel. How can I assist you today?</Say>
            <Record>
                <MaxDuration>30</MaxDuration>
                <SilenceTimeout>5</SilenceTimeout>
            </Record>
        </Response>
        """
        return Response(content=reply.strip(), media_type="application/xml")

    elif event == "Record":
        if not recording_url:
            logger.warning(f"Missing recording URL in Record event for caller '{caller}'")
            reply = """
            <Response>
                <Say>Sorry, I did not receive your message clearly. Please try again.</Say>
                <Record>
                    <MaxDuration>30</MaxDuration>
                    <SilenceTimeout>5</SilenceTimeout>
                </Record>
            </Response>
            """
            return Response(content=reply.strip(), media_type="application/xml")

        # Call your orchestrator logic (STT -> LLM -> DB -> TTS)
        resp_audio_url = orchestrator.process_call(recording_url, caller)

        if not resp_audio_url:
            logger.error(f"Failed to generate audio URL for caller '{caller}'")
            reply = """
            <Response>
                <Say>Sorry, there was an error. Please call back later.</Say>
            </Response>
            """
        else:
            reply = f"""
            <Response>
                <PlayAudio>{resp_audio_url}</PlayAudio>
                <Record>
                    <MaxDuration>30</MaxDuration>
                    <SilenceTimeout>5</SilenceTimeout>
                </Record>
            </Response>
            """
        return Response(content=reply.strip(), media_type="application/xml")

    elif event == "Disconnect":
        logger.info(f"Call disconnected for caller '{caller}'")
        return Response(content="<Response></Response>", media_type="application/xml")

    else:
        reply = """
        <Response>
            <Say>Thank you for calling. Goodbye!</Say>
        </Response>
        """
        return Response(content=reply.strip(), media_type="application/xml")
