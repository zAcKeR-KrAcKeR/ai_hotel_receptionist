import os
import azure.cognitiveservices.speech as speechsdk
import logging
from langchain.tools import tool

logger = logging.getLogger(__name__)

class AzureSTTTool:
    def __init__(self):
        self.speech_key = os.getenv("AZURE_SPEECH_KEY")
        self.speech_region = os.getenv("AZURE_SPEECH_REGION")
        if not self.speech_key or not self.speech_region:
            raise ValueError("Azure Speech key/region missing in environment variables")
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key, region=self.speech_region
        )
        self.speech_config.speech_recognition_language = "en-IN"

    @tool("transcribe_audio")
    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Transcribe the given audio file to text using Azure Cognitive Services.
        """
        try:
            audio_config = speechsdk.AudioConfig(filename=audio_file_path)
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config, audio_config=audio_config
            )
            result = recognizer.recognize_once()
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                logger.info(f"STT success: {result.text}")
                return result.text
            else:
                logger.warning(f"STT failed: {result.reason}")
                return ""
        except Exception as e:
            logger.error(f"STT error: {e}")
            return ""

stt_tool = AzureSTTTool()
