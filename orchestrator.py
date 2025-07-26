from agents.stt_tool import stt_tool
from agents.llm_tools import llm_tool
from agents.tts_tool import tts_tool
from agents.autogen_agents import groupchat, manager
from utils.audio_handler import AudioHandler
from utils.blob_storage import blob_storage
from database.queries import HotelDatabase
import time

class CallOrchestrator:
    def __init__(self):
        self.audio_handler = AudioHandler()
        self.db = HotelDatabase()
    def process_call(self, audio_url: str, user_phone: str):
        inp_file, out_file = None, None
        try:
            inp_file = self.audio_handler.download_audio_from_url(audio_url)
            # Step 1: STT
            transcript = stt_tool.transcribe_audio(inp_file)
            # Step 2: Intent Extraction (with LLM)
            intent_result = llm_tool.analyze_intent(transcript)
            # Step 3: Agentic Chat Handling
            msg = f"User said: {transcript}\nEntities: {intent_result.get('entities')}\nPhone: {user_phone}"
            chat_history=[{"role":"user", "content":msg}]
            result = manager.run(chat_history)
            response_text = result[-1]["content"] if isinstance(result, list) else str(result)
            # Step 4/5: TTS->Blob Storage
            out_file = tts_tool.synthesize_speech(response_text)
            audio_url = blob_storage.upload_audio_file(
                out_file, f"response_{user_phone}_{int(time.time())}.wav"
            )
            self.db.log_conversation(user_phone, transcript, response_text)
            return audio_url
        finally:
            if inp_file: self.audio_handler.cleanup_temp_file(inp_file)
            if out_file: self.audio_handler.cleanup_temp_file(out_file)

orchestrator = CallOrchestrator()
