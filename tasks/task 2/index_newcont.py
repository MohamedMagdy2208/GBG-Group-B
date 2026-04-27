import base64
import os
import sys
from io import BytesIO
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from openai import AzureOpenAI
from PyPDF2 import PdfReader


load_dotenv()


def get_required_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    joined = ", ".join(names)
    raise ValueError(f"Missing required environment variable. Tried: {joined}")


SEARCH_ENDPOINT = get_required_env("SEARCH_ENDPOINT", "AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = get_required_env("SEARCH_KEY", "AZURE_SEARCH_ADMIN_KEY")
INDEX_NAME = os.getenv("INDEX_NAME", "newcont-vector-index")

STORAGE_CONNECTION_STRING = get_required_env("AZURE_STORAGE_CONNECTION_STRING", "STORAGE_CONNECTION_STRING")
BLOB_CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME", "newcont")

AZURE_OPENAI_ENDPOINT = get_required_env("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = get_required_env("AZURE_OPENAI_KEY")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = get_required_env("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = get_required_env("AZURE_OPENAI_API_VERSION")

EMBEDDING_DIMENSIONS = int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "1536"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K = int(os.getenv("TOP_K", "3"))
QUERY_TEXT = os.getenv(
    "AZURE_SEARCH_QUERY",
    "What is the candidate's experience with Python and AI?",
)


openai_client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
)


def print_step(message: str) -> None:
    print(f"\n[STEP] {message}")


def get_embedding(text: str) -> list[float]:
    response = openai_client.embeddings.create(
        input=[text],
        model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    )
    return response.data[0].embedding


def read_pdf_bytes(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts).strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += max(chunk_size - overlap, 1)
    return chunks


def safe_id(blob_name: str, chunk_index: int) -> str:
    raw = f"{blob_name}:{chunk_index}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def create_index() -> None:
    print_step(f"Creating or updating vector index '{INDEX_NAME}'")

    index_client = SearchIndexClient(
        endpoint=SEARCH_ENDPOINT,
        credential=AzureKeyCredential(SEARCH_KEY),
    )

    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="my-hnsw")
        ],
        profiles=[
            VectorSearchProfile(
                name="my-vector-profile",
                algorithm_configuration_name="my-hnsw",
            )
        ],
    )

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="chunk", type=SearchFieldDataType.String),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="blob_name", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="blob_url", type=SearchFieldDataType.String),
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SearchField(
            name="vector_chunk",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name="my-vector-profile",
        ),
    ]

    index = SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vector_search)
    index_client.create_or_update_index(index)
    print(f"[DONE] Index '{INDEX_NAME}' is ready.")


def fetch_blob_pdfs() -> list[dict]:
    print_step(f"Downloading PDFs from blob container '{BLOB_CONTAINER_NAME}'")

    blob_service = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
    container_client = blob_service.get_container_client(BLOB_CONTAINER_NAME)

    pdf_blobs = [
        blob for blob in container_client.list_blobs()
        if blob.name.lower().endswith(".pdf")
    ]

    if not pdf_blobs:
        print("[DONE] No PDF files found in the container.")
        return []

    documents = []
    for blob in pdf_blobs:
        blob_client = container_client.get_blob_client(blob.name)
        print(f"[BLOB] {blob.name}")
        pdf_bytes = blob_client.download_blob().readall()
        text = read_pdf_bytes(pdf_bytes)

        if not text.strip():
            print("  Skipped because no text was extracted.")
            continue

        chunks = chunk_text(text)
        title = Path(blob.name).stem

        print(f"  Extracted {len(chunks)} chunks")
        for chunk_index, chunk in enumerate(chunks):
            vector = get_embedding(chunk)
            documents.append(
                {
                    "id": safe_id(blob.name, chunk_index),
                    "chunk": chunk,
                    "title": title,
                    "source": "pdf",
                    "blob_name": blob.name,
                    "blob_url": blob_client.url,
                    "chunk_index": chunk_index,
                    "vector_chunk": vector,
                }
            )

    print(f"[DONE] Prepared {len(documents)} chunk documents for upload.")
    return documents


def upload_documents(docs: list[dict]) -> None:
    print_step(f"Uploading {len(docs)} chunk documents to '{INDEX_NAME}'")

    if not docs:
        print("[DONE] Nothing to upload.")
        return

    client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_KEY),
    )

    results = client.upload_documents(documents=docs)
    succeeded = sum(1 for item in results if item.succeeded)
    print(f"[DONE] Uploaded {succeeded}/{len(docs)} documents.")


def search_vector(query_text: str) -> None:
    print_step(f"Running vector search for: {query_text!r}")

    client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_KEY),
    )

    query_vector = get_embedding(query_text)
    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=TOP_K,
        fields="vector_chunk",
    )

    results = client.search(
        search_text=None,
        vector_queries=[vector_query],
        select=["title", "chunk", "blob_name", "blob_url", "chunk_index"],
        top=TOP_K,
    )

    print("[RESULTS]")
    found_any = False
    for result in results:
        found_any = True
        print(f"  - title: {result['title']}")
        print(f"    blob: {result['blob_name']}")
        print(f"    url: {result['blob_url']}")
        print(f"    chunk_index: {result['chunk_index']}")
        print(f"    score: {result['@search.score']:.4f}")
        print(f"    chunk: {result['chunk'][:250]}...")

    if not found_any:
        print("  No matching documents were returned.")


def main() -> int:
    try:
        create_index()
        documents = fetch_blob_pdfs()
        upload_documents(documents)
        search_vector(QUERY_TEXT)
        print("\n[SUCCESS] Vector indexing and search completed.")
        return 0
    except Exception as exc:
        print("\n[ERROR]")
        print(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
