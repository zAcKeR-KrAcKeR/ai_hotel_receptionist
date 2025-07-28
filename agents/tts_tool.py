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
            raise ValueError("Azure Speech credentials not set")
        self.speech_config = speechsdk.SpeechConfig(subscription=self.speech_key, region=self.speech_region)
        self.speech_config.speech_synthesis_voice_name = "en-IN-Neer Neural"

    @tool("synthesize_speech")
    def synthesize_speech(self, text: str) -> str:
        """Synthesize speech from text using Azure TTS and save to WAV file."""
        try:
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            audio_config = speechsdk.AudioConfig(filename=temp_file.name)
            synthesizer = speechsdk.SpeechSynthesizer(self.speech_config, audio_config)
            synthesizer.speak_text_async(text).get()
            logger.info(f"TTS synthesized to {temp_file.name}")
            return temp_file.name
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return ""

tts_tool = AzureTTSTool()
