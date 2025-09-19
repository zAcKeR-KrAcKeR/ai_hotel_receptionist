import uuid
import os
import logging
from agents.stt_tool import stt_tool
from agents.llm_tools import llm_tool
from agents.tts_tool import AzureTTSTool
from agents.autogen_agents import manager
from utils.audio_handler import AudioHandler
from database.queries import HotelDatabase
from blob_storage import blob_storage
import requests
import tempfile

logger = logging.getLogger(__name__)

AUDIO_FOLDER = "static/audio"
os.makedirs(AUDIO_FOLDER, exist_ok=True)

class CallOrchestrator:
    def __init__(self):
        self.audio_handler = AudioHandler()
        self.db = HotelDatabase()

    def process_call(self, audio_source, user_phone):
        """
        Process call with Amazon Connect integration and Azure Blob Storage
        Supports both local files and remote URLs from Connect
        """
        inp_file = None
        temp_file = None
        
        try:
            # Handle different audio sources for Amazon Connect
            if audio_source.startswith('file://'):
                # Local file from Connect audio upload
                inp_file = audio_source.replace('file://', '')
                logger.info(f"Processing local Connect file: {inp_file}")
                
            elif audio_source.startswith('http'):
                # Remote recording URL from Connect
                logger.info(f"Downloading Connect recording: {audio_source}")
                temp_file = self._download_audio(audio_source)
                if temp_file:
                    inp_file = temp_file
                else:
                    logger.error("Failed to download Connect recording")
                    return None
                    
            else:
                logger.error(f"Unsupported audio source for Amazon Connect: {audio_source}")
                return None

            if not inp_file or not os.path.exists(inp_file):
                logger.error(f"Audio file not found: {inp_file}")
                return None

            # Amazon Connect AI pipeline: STT -> Intent -> LLM -> TTS -> Blob Storage
            logger.info("Starting Connect AI pipeline")
            
            # Step 1: Speech-to-Text
            transcript = stt_tool.transcribe_audio(inp_file)
            logger.info(f"Connect STT result: {transcript}")

            if not transcript.strip():
                logger.warning("Empty transcript from Connect audio")
                return self._generate_fallback_response(user_phone)

            # Step 2: Intent Analysis
            intent_data = llm_tool.analyze_intent(transcript)
            logger.info(f"Connect intent analysis: {intent_data}")

            # Step 3: LLM Processing using your existing agents
            chat_history = [{"role": "user", "content": transcript}]
            result = manager.run(chat_history)

            reply_text = result[-1]["content"] if isinstance(result, list) else str(result)
            logger.info(f"Connect AI response: {reply_text}")

            # Step 4: Text-to-Speech
            tts = AzureTTSTool()
            wav_path = tts.synthesize_speech(reply_text)

            if not wav_path or not os.path.exists(wav_path):
                logger.error("Failed TTS for Connect response")
                return self._generate_fallback_response(user_phone)

            # Step 5: Save to local storage
            output_filename = f"connect_reply_{user_phone}_{uuid.uuid4().hex}.wav"
            output_path = os.path.join(AUDIO_FOLDER, output_filename)
            os.rename(wav_path, output_path)

            # Step 6: Upload to Azure Blob Storage for Connect access
            blob_url = blob_storage.upload_audio_file(output_path)
            if blob_url:
                logger.info(f"Connect response uploaded to blob: {blob_url}")
            else:
                logger.warning("Failed to upload to blob, using local file")

            # Step 7: Log conversation to database
            self.db.log_conversation(user_phone, transcript, reply_text)

            logger.info(f"Connect call processing completed: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Connect orchestrator error: {e}", exc_info=True)
            return self._generate_fallback_response(user_phone)

        finally:
            # Clean up temporary files
            if temp_file and temp_file != inp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    logger.info(f"Cleaned up temporary file: {temp_file}")
                except:
                    pass

    def _download_audio(self, url):
        """Download audio file from Amazon Connect recording URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_file.write(response.content)
            temp_file.close()
            
            logger.info(f"Downloaded Connect recording to: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Failed to download Connect audio: {e}")
            return None

    def _generate_fallback_response(self, user_phone):
        """Generate fallback response for Connect when AI processing fails"""
        try:
            fallback_text = "I apologize, but I'm having trouble processing your request right now. Let me connect you with our reception team who can assist you immediately."
            
            tts = AzureTTSTool()
            wav_path = tts.synthesize_speech(fallback_text)
            
            if wav_path and os.path.exists(wav_path):
                output_filename = f"connect_fallback_{user_phone}_{uuid.uuid4().hex}.wav"
                output_path = os.path.join(AUDIO_FOLDER, output_filename)
                os.rename(wav_path, output_path)
                
                # Upload fallback to blob storage
                blob_storage.upload_audio_file(output_path)
                
                return output_path
            else:
                logger.error("Failed to generate fallback TTS")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate fallback response: {e}")
            return None

# Global instance for Amazon Connect integration
orchestrator = CallOrchestrator()
