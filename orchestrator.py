import uuid
import os
import logging

from agents.stt_tool import stt_tool
from agents.llm_tools import llm_tool
from agents.tts_tool import AzureTTSTool
from agents.autogen_agents import manager
from utils.audio_handler import AudioHandler
from database.queries import HotelDatabase

logger = logging.getLogger(__name__)
AUDIO_FOLDER = "static/audio"
os.makedirs(AUDIO_FOLDER, exist_ok=True)

class CallOrchestrator:
    def __init__(self):
        self.audio_handler = AudioHandler()
        self.db = HotelDatabase()

    def process_call(self, audio_source, user_phone):
        inp_file = None
        try:
            # Handle local files from Amazon Connect only
            if audio_source.startswith('file://'):
                inp_file = audio_source.replace('file://', '')
            else:
                logger.error("Unsupported audio source for Amazon Connect: Must be local file")
                return None

            if not inp_file or not os.path.exists(inp_file):
                logger.error(f"Audio file not found: {inp_file}")
                return None

            # AI pipeline: STT -> Intent -> LLM -> TTS
            transcript = stt_tool.transcribe_audio(inp_file)
            logger.info(f"Transcript: {transcript}")

            intent_data = llm_tool.analyze_intent(transcript)
            chat_history = [{"role": "user", "content": transcript}]
            result = manager.run(chat_history)
            reply_text = result[-1]["content"] if isinstance(result, list) else str(result)

            print("Agent reply:", reply_text)

            tts = AzureTTSTool()
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
            pass  # Do not clean up inp_file since Amazon Connect local files are already deleted by FastAPI

orchestrator = CallOrchestrator()
