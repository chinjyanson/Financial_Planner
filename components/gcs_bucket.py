from google.cloud import storage
import os
import io
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

from google.oauth2 import service_account

async def set_google_credentials(cred_path=None):
    """Set the GOOGLE_APPLICATION_CREDENTIALS environment variable."""
    if cred_path:
        credentials = service_account.Credentials.from_service_account_file(cred_path)
        return credentials
        # if os.path.exists(cred_path):
        #     os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
        # else:
        #     print(f"Credentials file not found at {cred_path}")
        #     raise FileNotFoundError(f"Credentials file not found at {cred_path}")
    else:
        raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS is not set. Please set the environment variable or provide the path to the credentials file.")
    # elif "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
    #     raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS is not set. Please set the environment variable or provide the path to the credentials file.")

async def upload_file_to_gcs(file_bytes: io.BytesIO, file_extension: str, destination_blob_name: str, bucket_name: str, credentials: service_account.Credentials):
    """Uploads a file to the bucket."""
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    file_bytes.seek(0)  # Ensure the BytesIO object is at the start
    blob.upload_from_file(file_bytes, content_type=f'application/{file_extension}')

    print(f"File uploaded to {destination_blob_name}.")
    storage_client.close()

async def generate_download_link(bucket_name: str, blob_name: str, credentials: service_account.Credentials, expiration_hours=1) -> str:
    """Generates a signed URL for downloading a file from Google Cloud Storage."""
    if not bucket_name:
        raise ValueError("Bucket name must be specified.")

    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    # Generate a signed URL for the blob that is valid for the specified duration
    url = blob.generate_signed_url(expiration=timedelta(hours=expiration_hours))
    storage_client.close()    
    return url



async def upload_and_download_file(cred_path: str, file_bytes : io.BytesIO, file_extension: str, blob_name: str, bucket_name: str) -> str:
    """ Uploads and downloads the file from gcs bucket, returns download link

    cred_path (str): path to authentication json file for Google cloud service
    file_bytes (str): files that are converted to bytes to be uploaded to GCS
    file_extension (str): the extension name of the files (e.g. .pdf, .png, .jpeg)
    blob_name (str): Name of the file to be uploaded
    bucket_name (str): name of the database to be uploaded to in google cloud
    
    """

    credentials = await set_google_credentials(cred_path=cred_path)
    await upload_file_to_gcs(file_bytes=file_bytes, file_extension=file_extension, destination_blob_name=blob_name, bucket_name=bucket_name, credentials=credentials)
    # Generate a download link
    download_link = await generate_download_link(bucket_name=bucket_name, blob_name=blob_name, credentials=credentials, expiration_hours=1)
    return download_link