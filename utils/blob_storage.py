import os
import logging
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AzureBlobStorage:
    def __init__(self):
        self.account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        self.container = os.getenv("AZURE_CONTAINER_NAME", "audio-files")

        if not self.account_name or not self.account_key:
            raise ValueError("Azure Storage account name/key missing in environment variables")

        connection_str = (
            f"DefaultEndpointsProtocol=https;AccountName={self.account_name};"
            f"AccountKey={self.account_key};EndpointSuffix=core.windows.net"
        )
        self.client = BlobServiceClient.from_connection_string(connection_str)

    def upload_audio_file(self, file_path, blob_name=None):
        if not blob_name:
            blob_name = os.path.basename(file_path)
        try:
            blob_client = self.client.get_blob_client(self.container, blob_name)
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            url = f"https://{self.account_name}.blob.core.windows.net/{self.container}/{blob_name}"
            logger.info(f"Uploaded audio file successfully: {url}")
            return url
        except Exception as ex:
            logger.error(f"Failed to upload blob '{blob_name}': {ex}")
            return None

blob_storage = AzureBlobStorage()
