import requests
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

class AudioHandler:
    @staticmethod
    def download_audio_from_url(audio_url, output_path=None):
        try:
            if not output_path:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                output_path = temp_file.name
                temp_file.close()
            r = requests.get(audio_url, timeout=30)
            r.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(r.content)
            logger.info(f"Downloaded audio to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error downloading audio from {audio_url}: {e}")
            return None

    @staticmethod
    def cleanup_temp_file(filepath):
        try:
            if filepath and os.path.exists(filepath):
                os.unlink(filepath)
                logger.info(f"Deleted temporary file {filepath}")
        except Exception as e:
            logger.warning(f"Could not delete temp file {filepath}: {e}")


