import logging
import time

from agents.stt_tool import stt_tool
from agents.llm_tools import llm_tool
from agents.tts_tool import tts_tool
from agents.autogen_agents import manager
from utils.audio_handler import AudioHandler
from utils.blob_storage import blob_storage
from database.queries import HotelDatabase

logger = logging.getLogger(__name__)

class CallOrchestrator:
    def __init__(self):
        self.audio_handler = AudioHandler()
        self.db = HotelDatabase()

    def process_call(self, audio_url: str, user_phone: str):
        inp_file, out_file = None, None
        try:
            logger.info(f"Processing call for user {user_phone}")

            # Download recorded audio
            inp_file = self.audio_handler.download_audio_from_url(audio_url)
            logger.info(f"Downloaded audio file for user {user_phone} from {audio_url}")

            # Speech to Text
            transcript = stt_tool.transcribe_audio(inp_file)
            logger.info(f"STT transcription for user {user_phone}: {transcript}")

            # Intent Extraction
            intent_result = llm_tool.analyze_intent(transcript)
            logger.debug(f"Intent extraction result for {user_phone}: {intent_result}")

            # Agentic chat via AutoGen + LangChain
            msg = (
                f"User said: {transcript}\n"
                f"Entities: {intent_result.get('entities')}\n"
                f"Phone: {user_phone}"
            )
            chat_history = [{"role": "user", "content": msg}]
            result = manager.run(chat_history)
            response_text = result[-1]["content"] if isinstance(result, list) else str(result)
            logger.info(f"Generated response for user {user_phone}: {response_text}")

            # Text-to-Speech synthesis
            out_file = tts_tool.synthesize_speech(response_text)

            # Upload audio to Azure Blob Storage
            blob_name = f"response_{user_phone}_{int(time.time())}.wav"
            audio_url = blob_storage.upload_audio_file(out_file, blob_name)
            if not audio_url:
                logger.error(f"Failed to upload audio blob for user {user_phone}")
                return None

            # Log conversation to DB
            self.db.log_conversation(user_phone, transcript, response_text)

            return audio_url

        except Exception as e:
            logger.error(f"Error processing call for user {user_phone}: {e}")
            return None
        finally:
            if inp_file:
                self.audio_handler.cleanup_temp_file(inp_file)
            if out_file:
                self.audio_handler.cleanup_temp_file(out_file)

orchestrator = CallOrchestrator()
