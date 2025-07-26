import os, tempfile
import azure.cognitiveservices.speech as speechsdk
from langchain.tools import tool
class AzureTTSTool:
    def __init__(self):
        self.speech_key = os.getenv("AZURE_SPEECH_KEY")
        self.speech_region = os.getenv("AZURE_SPEECH_REGION")
        self.speech_config = speechsdk.SpeechConfig(subscription=self.speech_key, region=self.speech_region)
        self.speech_config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"
    @tool("synthesize_speech")
    def synthesize_speech(self, text: str) -> str:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        audio_config = speechsdk.AudioConfig(filename=temp_file.name)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=audio_config)
        synthesizer.speak_text_async(text).get()
        return temp_file.name
tts_tool = AzureTTSTool()

