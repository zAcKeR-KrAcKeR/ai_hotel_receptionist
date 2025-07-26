import os
import azure.cognitiveservices.speech as speechsdk
from langchain.tools import tool
class AzureSTTTool:
    def __init__(self):
        self.speech_key = os.getenv("AZURE_SPEECH_KEY")
        self.speech_region = os.getenv("AZURE_SPEECH_REGION")
        self.speech_config = speechsdk.SpeechConfig(subscription=self.speech_key, region=self.speech_region)
        self.speech_config.speech_recognition_language = "en-IN"
    @tool("transcribe_audio")
    def transcribe_audio(self, audio_file_path: str) -> str:
        audio_config = speechsdk.AudioConfig(filename=audio_file_path)
        recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=audio_config)
        result = recognizer.recognize_once()
        return result.text if result.reason == speechsdk.ResultReason.RecognizedSpeech else ""
stt_tool = AzureSTTTool()

