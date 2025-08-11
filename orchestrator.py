import uuid
import os
import logging

from agents.stt_tool import stt_tool
from agents.llm_tools import llm_tool
from agents.tts_tool import AzureTTsTool  # Use class, not tool instance
from agents.autogen_agents import manager
from utils import audio_handler  # adjust to your project structure
from database import database  # adjust import

logger = logging.getLogger(__name__)

AUDIO_FOLDER = "static/audio"
os.makedirs(AUDIO_FOLDER, exist_ok=True)

class CallOrchestrator:
    def __init__(self):
        self.audio_handler = audio_handler.AudioHandler()
        self.db = database

    def process_call(self, audio_url, user_phone):
        inp_file = None
        try:
            inp_file = self.audio_handler.download(audio_url)
            transcript = stt_tool.transcribe_audio(inp_file)
            intent_data = llm_tool.analyze_intent(transcript)

            chat_history = [{"role": "user", "content": transcript}]
            result = manager.run(chat_history)
            reply_text = result[-1]["content"] if isinstance(result, list) else str(result)

            # Debug print for verification
            print("Agent reply:", reply_text)

            tts = AzureTTsTool()
            wav_path = tts.synthesize_speech(reply_text)
            if not wav_path or not os.path.exists(wav_path):
                logger.error("Failed TTS in orchestrator")
                return None

            output_filename = f"reply_{user_phone}_{uuid.uuid4().hex}.wav"
            output_path = os.path.join(AUDIO_FOLDER, output_filename)
            os.rename(wav_path, output_path)

            self.db.log_conversation(user_phone, transcript, reply_text)
            return output_path

        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return None
        finally:
            if inp_file:
                self.audio_handler.cleanup(inp_file)

orchestrator = CallOrchestrator()
