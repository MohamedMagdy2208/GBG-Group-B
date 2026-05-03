import os
from dotenv import load_dotenv

load_dotenv()


# Required values are validated where they are used so imports and local
# unit tests do not fail before the app can show a helpful setup error.
def require_env_vars(*names: str) -> dict[str, str]:
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"Missing required environment variable(s): {joined}. "
            "Copy .env.example to .env and set the required values."
        )
    return {name: os.environ[name] for name in names}


def get_required_env(name: str) -> str:
    return require_env_vars(name)[name]


def get_bool_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


# Azure OpenAI
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_OPENAI_EMBEDDING_API_VERSION = os.getenv(
    "AZURE_OPENAI_EMBEDDING_API_VERSION",
    "2024-02-01",
)
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    "",
)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "")

# LangSmith (optional)
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "true")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "chinook-chatbot")

os.environ["LANGSMITH_TRACING"] = LANGSMITH_TRACING
if LANGSMITH_API_KEY:
    os.environ["LANGSMITH_API_KEY"] = LANGSMITH_API_KEY
os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT

# Limits
MAX_QUESTION_LENGTH = 500
MAX_RESULT_ROWS = int(os.getenv("MAX_RESULT_ROWS", "50"))
SQL_QUERY_TIMEOUT_SECONDS = 30
MAX_CHAT_HISTORY_MESSAGES = int(os.getenv("MAX_CHAT_HISTORY_MESSAGES", "6"))
MAX_CHAT_HISTORY_CHARS = int(os.getenv("MAX_CHAT_HISTORY_CHARS", "1200"))

# Optional retrieval mode for selecting the most relevant few-shot examples.
USE_EMBEDDING_RETRIEVAL = get_bool_env("USE_EMBEDDING_RETRIEVAL", "false")
FEWSHOT_TOP_K = int(os.getenv("FEWSHOT_TOP_K", "8"))
