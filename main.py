from fastapi import FastAPI, Request, Response
from orchestrator import orchestrator
from dotenv import load_dotenv
load_dotenv()
app = FastAPI()
@app.get("/")
async def health_check():
    return {"status": "OK", "service": "AI Receptionist"}
@app.post("/kookoo_webhook")
async def kookoo_webhook(request: Request):
    form = await request.form()
    caller = form.get("cid")
    recording_url = form.get("data")
    event = form.get("event")
    if event == "NewCall":
        xml="""<?xml version="1.0" encoding="UTF-8"?><Response>
        <playtext>Hello! Welcome to Grand Hotel. Please tell me how I can help you.</playtext>
        <record maxduration="30" silence="3" playbeep="yes"/>
        </Response>"""
        return Response(content=xml, media_type="application/xml")
    elif event == "Record":
        if not recording_url:
            xml="""<?xml version="1.0" encoding="UTF-8"?><Response>
            <playtext>Sorry, I did not receive your message clearly. Please try again.</playtext>
            <record maxduration="30" silence="3" playbeep="yes"/>
            </Response>"""
            return Response(content=xml, media_type="application/xml")
        resp_audio_url = orchestrator.process_call(recording_url, caller)
        if not resp_audio_url:
            xml="""<?xml version="1.0" encoding="UTF-8"?><Response>
            <playtext>Sorry, there was an error. Please call back later.</playtext>
            <hangup/></Response>"""
        else:
            xml=f"""<?xml version="1.0" encoding="UTF-8"?><Response>
            <playaudio>{resp_audio_url}</playaudio>
            <record maxduration="30" silence="3" playbeep="no"/>
            </Response>"""
        return Response(content=xml, media_type="application/xml")
    elif event == "Disconnect":
        return Response(content="""<?xml version="1.0"?><Response><hangup /></Response>""", media_type="application/xml")
    else:
        xml = """<?xml version="1.0"?><Response><playtext>Thank you for calling. Goodbye!</playtext><hangup /></Response>"""
        return Response(content=xml, media_type="application/xml")
