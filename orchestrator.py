import uuid
import os
import logging

from agents.stt_tool import stt_tool
from agents.llm_tools import llm_tool
from agents.tts_tool import AzureTTSTool   # ✅ Class only
from agents.autogen_agents import manager
from utils.audio_handler import AudioHandler
from database.queries import HotelDatabase

logger = logging.getLogger(__name__)

AUDIO_OUTPUT_DIR = "static/audio"
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

class CallOrchestrator:
    def __init__(self):
        self.audio_handler = AudioHandler()
        self.db = HotelDatabase()

    def process_call(self, audio_url: str, user_phone: str):
        inp_file, out_file = None, None
        try:
            logger.info(f"Processing call for user {user_phone}")

            inp_file = self.audio_handler.download_audio_from_url(audio_url)
            if not inp_file:
                logger.error(f"Could not download input audio from {audio_url}")
                return None

            transcript = stt_tool.transcribe_audio(inp_file)
            logger.info(f"Transcribed text: {transcript}")

            intent_result = llm_tool.analyze_intent(transcript)
            logger.debug(f"Intent extraction: {intent_result}")

            msg = (
                f"User said: {transcript}\n"
                f"Entities: {intent_result.get('entities')}\n"
                f"Phone: {user_phone}"
            )
            chat_history = [{"role": "user", "content": msg}]

            result = manager.run(chat_history)
            response_text = result[-1]["content"] if isinstance(result, list) else str(result)
            print("------- AGENT RETURNED REPLY --------", response_text, type(response_text))

            # ✅ Always use AzureTTSTool directly here
            tts_instance = AzureTTSTool()
            out_file = tts_instance.synthesize_speech(str(response_text))
            if not out_file or not os.path.exists(out_file):
                logger.error("TTS failed, output file missing")
                return None

            reply_fname = f"reply_{user_phone}_{uuid.uuid4().hex}.wav"
            final_path = os.path.join(AUDIO_OUTPUT_DIR, reply_fname)
            os.rename(out_file, final_path)
            logger.info(f"Bot reply TTS available at {final_path}")

            self.db.log_conversation(user_phone, transcript, str(response_text))
            return final_path

        except Exception as e:
            logger.error(f"Error processing call for user {user_phone}: {e}")
            return None
        finally:
            if inp_file:
                self.audio_handler.cleanup_temp_file(inp_file)


orchestrator = CallOrchestrator()
