import os
import tempfile
import azure.cognitiveservices.speech as speechsdk
import logging
from langchain.tools import tool

logger = logging.getLogger(__name__)

class AzureTTSTool:
    def __init__(self):
        self.speech_key = os.getenv("AZURE_SPEECH_KEY")
        self.speech_region = os.getenv("AZURE_SPEECH_REGION")
        if not self.speech_key or not self.speech_region:
            raise ValueError("Azure Speech key/region missing in env variables")
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key, region=self.speech_region
        )
        # Choose an Indian/English natural voice
        self.speech_config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"

    @tool("synthesize_speech")
    def synthesize_speech(self, text: str) -> str:
        """
        Synthesize the given text to speech audio using Azure TTS, writes to WAV file, and returns path.
        """
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            audio_config = speechsdk.AudioConfig(filename=temp_file.name)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config, audio_config=audio_config
            )
            synthesizer.speak_text_async(text).get()
            logger.info(f"TTS synthesized audio to {temp_file.name}")
            return temp_file.name
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return ""

tts_tool = AzureTTSTool()
