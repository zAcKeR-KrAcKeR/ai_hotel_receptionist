import os
import uuid
import logging

from agents.stt_tool import stt_tool
from agents.llm_tools import llm_tool
from agents.tts_tool import AzureTTSTool
from agents.autogen_agents import manager
from utils.audio_handler import AudioHandler
from database import database  # adjust import as needed

logger = logging.getLogger(__name__)
OUTPUT_DIR = "static/audio"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class CallOrchestrator:
    def __init__(self):
        self.audio_handler = AudioHandler()
        self.db = database

    def process_call(self, audio_url: str, user_phone: str):
        inp_file = None
        try:
            inp_file = self.audio_handler.download(audio_url)
            transcript = stt_tool.transcribe_audio(inp_file)

            intent = llm_tool.analyze_intent(transcript)

            chat_history = [{"role": "user", "content": transcript}]
            agent_response = manager.run(chat_history)
            if isinstance(agent_response, list):
                reply_text = agent_response[-1].get("content", "")
            else:
                reply_text = str(agent_response)

            tts_tool = AzureTTSTool()
            wav_path = tts_tool.synthesize_speech(reply_text)

            if not wav_path or not os.path.exists(wav_path):
                logger.error("Failed to synthesize speech")
                return None

            final_path = os.path.join(OUTPUT_DIR, f"reply_{user_phone}_{uuid.uuid4().hex}.wav")
            os.rename(wav_path, final_path)

            self.db.log_conversation(user_phone, transcript, reply_text)

            return final_path
        except Exception as e:
            logger.error(f"Error processing call: {e}")
            return None
        finally:
            if inp_file:
                self.audio_handler.cleanup(inp_file)

orchestrator = CallOrchestrator()
