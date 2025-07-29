from fastapi import FastAPI, Request, Response, Form
import logging
from orchestrator import orchestrator
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
logger = logging.getLogger("uvicorn.error")

@app.get("/")
async def health_check():
    return {"status": "OK", "service": "AI Receptionist"}

@app.api_route("/kookoo_webhook", methods=["GET", "POST"])
async def kookoo_webhook(request: Request):
    if request.method == "GET":
        query = dict(request.query_params)
        caller = query.get("cid")
        event = query.get("event")
    else:
        form = await request.form()
        caller = form.get("cid")
        event = form.get("event")

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
        return Response(content=xml_response, media_type="application/xml")

    elif event == "Record":
        recording_url = form.get("data") if request.method == "POST" else query.get("data")
        if not recording_url:
            return Response(content="<Response><Say>Sorry, no audio was captured.</Say></Response>", media_type="application/xml")

        # Process audio using your orchestrator
        resp_audio_url = orchestrator.process_call(recording_url, caller)

        if resp_audio_url:
            xml = f"<Response><PlayAudio>{resp_audio_url}</PlayAudio></Response>"
        else:
            xml = "<Response><Say>There was a problem processing your request. Please try again later.</Say></Response>"

        return Response(content=xml, media_type="application/xml")

    elif event == "Disconnect":
        logger.info(f"Call disconnected for caller '{caller}'")
        return Response(content="<Response></Response>", media_type="application/xml")

    # Default fallback
    return Response(content="<Response><Say>Thank you for calling.</Say></Response>", media_type="application/xml")
