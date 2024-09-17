from dotenv import load_dotenv
import os
from openai import OpenAI
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient 
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# speicify environment variables path for GCP
env_file = os.path.join(BASE_DIR, ".env")

# FOR LOCAL TESTING USE GOOGLE = False
IS_GOOGLE = True

if IS_GOOGLE:
    # FOR DEPLOYMENT
    import google.auth
    from google.cloud import secretmanager_v1
    
    # to get environmental vraiables from google secret manager
    SECRET_SETTINGS_NAME = "brain-secrets"
    _, project = google.auth.default()
    if project:
        client = secretmanager_v1.SecretManagerServiceClient()

        SETTINGS_NAME = os.environ.get("SETTINGS_NAME", SECRET_SETTINGS_NAME)
        name = f"projects/{project}/secrets/{SETTINGS_NAME}/versions/latest"
        payload = client.access_secret_version(
            name=name).payload.data.decode("UTF-8")
        with open(env_file, "w") as f:
            f.write(payload)
    
    load_dotenv(env_file)

else:
    # LOCAL TESTING
    load_dotenv()

# Initialize MongoDB connection
CHATBOT_MONGO_CONNECTION_STRING = os.environ.get("CHATBOT_MONGO_CONNECTION_STRING")
CHATBOT_MONGO_DATABASE = os.environ.get("CHATBOT_MONGO_DATABASE")
CHATBOT_MONGO_COLLECTION = os.environ.get("CHATBOT_MONGO_COLLECTION")
CHATBOT_MONGO_COLLECTION_STATUS = os.environ.get("CHATBOT_MONGO_COLLECTION_STATUS")
MANAGER_STATUS = os.environ.get("MANAGER_STATUS")

mongo_client = AsyncIOMotorClient(CHATBOT_MONGO_CONNECTION_STRING, uuidRepresentation="standard")
mongodb = mongo_client.sql_database

tnb_mongo_client = AsyncIOMotorClient(os.environ.get('TNB_MONGO_CONNECTION_STRING'), uuidRepresentation="standard")

# mongo_client = MongoClient(CHATBOT_MONGO_CONNECTION_STRING)
# mongodb = mongo_client.sql_database
# TNB and OCR
OCR_API_KEY = os.getenv("OCR_API_KEY")
OCR_API_SECRET = os.getenv("OCR_API_SECRET")

# Initialize OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DEFAULT_EMBEDDINGS_MODEL = "text-embedding-ada-002"
DEFAULT_CHAT_MODEL = "gpt-4o-mini"
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize Langchain
LANGCHAIN_API_KEY = os.environ.get("LANGCHAIN_API_KEY")
LANGCHAIN_TRACING_V2 = "true"
LANGCHAIN_PROJECT = "Customer Support Bot Tutorial"
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

# Initialize telegram API Key
TELEGRAM_API_KEY = os.environ.get("TELEGRAM_API_KEY")
TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME")

## SURIA PROJECT
# GOOGLE_APPLICATION_CREDENTIALS_1 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_1")
# CREDENTIALS to get from directory suria_db_creds.json
if IS_GOOGLE:
    # FOR DEPLOYMENT
    suria_db_creds_file = os.path.join(BASE_DIR, "suria_db_creds.json")
    SURIA_DB_CREDS_SECRET_NAME = "suria-db-secret"
    SURIA_DB_CREDS_NAME = os.environ.get("SURIA_DB_CREDS_NAME", SURIA_DB_CREDS_SECRET_NAME)
    suria_db_creds_name = f"projects/{project}/secrets/{SURIA_DB_CREDS_NAME}/versions/latest"
    suria_db_creds_payload = client.access_secret_version(
        name=suria_db_creds_name).payload.data.decode("UTF-8")
    
    with open(suria_db_creds_file, "w") as f:
        f.write(suria_db_creds_payload)

SURIA_DB_SERVICE_ACCOUNT_FILE = 'suria_db_creds.json'
# SURIA_DB_SERVICE_ACCOUNT_FILE='authentication/suria-db-access.json'

# Database instance connection details
INSTANCE_CONNECTION_NAME_1 = os.getenv("INSTANCE_CONNECTION_NAME_1")
DB_NAME_1=os.getenv("DB_NAME_1")
IAM_USER_1=os.getenv("IAM_USER_1")
# GCS bucket (test-suria)
GCS_BUCKET_NAME=os.getenv("GCS_BUCKET_NAME")


## SIP-CDE PROJECT
# GOOGLE_APPLICATION_CREDENTIALS_2 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_2")
# CREDENTIALS to get from directory sip_cde_db_creds.json 
if IS_GOOGLE:
    # FOR DEPLOYMENT
    cde_db_creds_file = os.path.join(BASE_DIR, "sip_cde_db_creds.json")
    CDE_DB_CREDS_SECRET_NAME = "sip-cde-db-secret"
    CDE_DB_CREDS_NAME = os.environ.get("CDE_DB_CREDS_SECRET_NAME", CDE_DB_CREDS_SECRET_NAME)
    cde_db_creds_name = f"projects/{project}/secrets/{CDE_DB_CREDS_NAME}/versions/latest"
    cde_db_creds_payload = client.access_secret_version(
        name=cde_db_creds_name).payload.data.decode("UTF-8")
    
    with open(cde_db_creds_file, "w") as f:
        f.write(cde_db_creds_payload)

SIP_CDE_DB_SERVICE_ACCOUNT_FILE = 'sip_cde_db_creds.json'
# SIP_CDE_DB_SERVICE_ACCOUNT_FILE='authentication/sip-cde-db-access.json'

# Database instance connection details
INSTANCE_CONNECTION_NAME_2 = os.getenv("INSTANCE_CONNECTION_NAME_2")
DB_NAME_2=os.getenv("DB_NAME_2")
IAM_USER_2=os.getenv("IAM_USER_2")


# GOOGLE GEMINI CREDENTIALS 
# CREDENTIALS to get from directory gemini_creds.json
if IS_GOOGLE:
    # FOR DEPLOYMENT
    gemini_creds_file = os.path.join(BASE_DIR, "gemini_creds.json")
    GEMINI_CREDS_SECRET_NAME = "gemini-ocr-secret"
    gemini_creds_name = f"projects/{project}/secrets/{GEMINI_CREDS_SECRET_NAME}/versions/latest"
    gemini_creds_payload = client.access_secret_version(
        name=gemini_creds_name).payload.data.decode("UTF-8")
    
    with open(gemini_creds_file, "w") as f:
        f.write(gemini_creds_payload)
GEMINI_SERVICE_ACCOUNT_FILE = 'gemini_creds.json'