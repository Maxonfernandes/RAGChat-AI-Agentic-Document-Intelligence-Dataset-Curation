import sys
import importlib.util
from pathlib import Path

# Load directly from backend/config.py to prevent circular naming collision
_backend_dir = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("main_backend_config", _backend_dir / "config.py")
_cfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)

GEMINI_API_KEY = _cfg.GEMINI_API_KEY
GEMINI_MODEL = _cfg.GEMINI_MODEL
ASTRA_DB_API_TOKEN = _cfg.ASTRA_DB_API_TOKEN
ASTRA_DB_ENDPOINT = _cfg.ASTRA_DB_ENDPOINT
ASTRA_DB_KEYSPACE = _cfg.ASTRA_DB_KEYSPACE
COLLECTION_NAME = _cfg.COLLECTION_NAME
HOST = _cfg.HOST
PORT = _cfg.PORT
INPUT_DIR = _cfg.INPUT_DIR
OUTPUT_DIR = _cfg.OUTPUT_DIR
FILE_TYPES = _cfg.FILE_TYPES
get_effective_config = _cfg.get_effective_config