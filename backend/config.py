import os
from pathlib import Path
from dotenv import load_dotenv

# Find and load .env file from root or backend directory
env_path = Path(__file__).resolve().parent.parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Gemini settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Astra DB settings
ASTRA_DB_API_TOKEN = os.getenv("ASTRA_DB_API_TOKEN", "")
ASTRA_DB_ENDPOINT = os.getenv("ASTRA_DB_ENDPOINT", "")
ASTRA_DB_KEYSPACE = os.getenv("ASTRA_DB_KEYSPACE", "default_keyspace")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "pdf")

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Directories
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = os.getenv("INPUT_DIR", str(BASE_DIR / "structurisation" / "files"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", str(BASE_DIR / "structurisation" / "output"))

# File types
FILE_TYPES = {
    "text": [".txt", ".md", ".csv", ".json"],
    "image": [".jpg", ".jpeg", ".png", ".webp"],
    "document": [".pdf", ".docx"],
    "audio": [".mp3", ".wav"],
    "video": [".mp4", ".avi", ".mkv"]
}

def get_effective_config(headers: dict = None, body_config: dict = None):
    """
    Extract effective API configuration with user input overrides:
    Precedence:
    1. Direct request body config
    2. HTTP request headers (e.g. from frontend UI settings)
    3. Environment variables / .env
    """
    headers = headers or {}
    body_config = body_config or {}

    gemini_key = (
        body_config.get("gemini_api_key")
        or headers.get("x-gemini-api-key")
        or GEMINI_API_KEY
    )
    
    gemini_model = (
        body_config.get("gemini_model")
        or headers.get("x-gemini-model")
        or GEMINI_MODEL
    )
    
    astra_token = (
        body_config.get("astra_api_token")
        or headers.get("x-astra-token")
        or ASTRA_DB_API_TOKEN
    )
    
    astra_endpoint = (
        body_config.get("astra_endpoint")
        or headers.get("x-astra-endpoint")
        or ASTRA_DB_ENDPOINT
    )
    
    astra_keyspace = (
        body_config.get("astra_keyspace")
        or headers.get("x-astra-keyspace")
        or ASTRA_DB_KEYSPACE
    )
    
    collection = (
        body_config.get("collection_name")
        or headers.get("x-collection-name")
        or COLLECTION_NAME
    )

    return {
        "gemini_api_key": gemini_key.strip() if gemini_key else "",
        "gemini_model": gemini_model.strip() if gemini_model else "gemini-1.5-flash",
        "astra_api_token": astra_token.strip() if astra_token else "",
        "astra_endpoint": astra_endpoint.strip() if astra_endpoint else "",
        "astra_keyspace": astra_keyspace.strip() if astra_keyspace else "default_keyspace",
        "collection_name": collection.strip() if collection else "pdf",
    }
