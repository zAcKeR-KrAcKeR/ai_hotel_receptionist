from fastapi import FastAPI, Request, Response
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
    # Unified GET/POST param extraction
    is_post = request.method == "POST"
    form = await request.form() if is_post else {}
    params = request.query_params

    def pick(key):
        # prefer form value if present, otherwise fallback to query
        return form.get(key) if key in form else params.get(key)

    caller = pick("cid")
    event = pick("event")
    recording_url = pick("data")

    logger.info(f"Received webhook event '{event}' from caller '{caller}'")

    if event == "NewCall":
        # Send compact, KooKoo-compliant, no-indentation XML
        xml_response = (
            "<Response>"
            "<Say>Welcome to Grand Hotel. How can I assist you today?</Say>"
            "<Record>"
            "<MaxDuration>30</MaxDuration>"
            "<SilenceTimeout>5</SilenceTimeout>"
            "</Record>"
            "</Response>"
        )
        return Response(content=xml_response, media_type="application/xml")

    elif event == "Record":
        if not recording_url:
            logger.error(f"No audio URL passed in Record event for caller '{caller}'")
            return Response(
                content="<Response><Say>Sorry, no audio was captured. Please speak after the beep next time.</Say></Response>",
                media_type="application/xml",
            )
        try:
            resp_audio_url = orchestrator.process_call(recording_url, caller)
        except Exception as e:
            logger.exception(f"Error processing call for user {caller}: {str(e)}")
            return Response(
                content="<Response><Say>There was a problem processing your request. Please try again later.</Say></Response>",
                media_type="application/xml"
            )

        if resp_audio_url:
            xml = f"<Response><PlayAudio>{resp_audio_url}</PlayAudio></Response>"
        else:
            xml = "<Response><Say>Sorry, something went wrong.</Say></Response>"

        return Response(content=xml, media_type="application/xml")

    elif event == "Disconnect":
        logger.info(f"Call disconnected for caller '{caller}'")
        return Response(content="<Response></Response>", media_type="application/xml")

    # Default fallback for unexpected/missing events
    return Response(content="<Response><Say>Thank you for calling. Goodbye!</Say></Response>", media_type="application/xml")
