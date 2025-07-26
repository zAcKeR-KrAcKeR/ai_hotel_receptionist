import requests, tempfile, os
class AudioHandler:
    @staticmethod
    def download_audio_from_url(audio_url, output_path=None):
        if not output_path:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            output_path = temp_file.name
            temp_file.close()
        r = requests.get(audio_url)
        with open(output_path, "wb") as f:
            f.write(r.content)
        return output_path
    @staticmethod
    def cleanup_temp_file(filepath):
        if filepath and os.path.exists(filepath):
            os.unlink(filepath)

