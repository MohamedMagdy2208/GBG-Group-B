"""
Configuration module — reads all Azure service credentials from environment variables.

If Azure keys are not set, the system runs in demo/mock mode with simulated AI responses.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── Azure OpenAI ────────────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
AZURE_OPENAI_DEPLOYMENT_GPT4O = os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4O", "gpt-4o")
AZURE_OPENAI_DEPLOYMENT_EMBEDDING = os.getenv("AZURE_OPENAI_DEPLOYMENT_EMBEDDING", "text-embedding-3-small")

# ─── Azure AI Vision ─────────────────────────────────────────────────
AZURE_VISION_ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT", "")
AZURE_VISION_KEY = os.getenv("AZURE_VISION_KEY", "")

# ─── Azure AI Search ─────────────────────────────────────────────────
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "lost-found-items")

# ─── Azure AI Document Intelligence ──────────────────────────────────
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
AZURE_DOCUMENT_INTELLIGENCE_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")

# ─── Azure Blob Storage ──────────────────────────────────────────────
AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING", "")
AZURE_BLOB_CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER_NAME", "lost-found-photos")

# ─── Local paths ─────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "lost_found.db")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def is_demo_mode() -> bool:
    """Return True if Azure OpenAI keys are not configured (run in mock/demo mode)."""
    return not (AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY)


def is_vision_available() -> bool:
    """Return True if Azure AI Vision credentials are configured."""
    return bool(AZURE_VISION_ENDPOINT and AZURE_VISION_KEY)


def is_search_available() -> bool:
    """Return True if Azure AI Search credentials are configured."""
    return bool(AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY)


def is_blob_available() -> bool:
    """Return True if Azure Blob Storage credentials are configured."""
    return bool(AZURE_BLOB_CONNECTION_STRING)
