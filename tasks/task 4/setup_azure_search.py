"""
One-time setup script to create the Azure AI Search index for the Lost & Found system.

Usage:
    python setup_azure_search.py

Requires AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY to be set in .env
"""

import sys

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

import config


def create_index() -> None:
    """Create the Azure AI Search index with vector search support."""
    if not config.is_search_available():
        print("ERROR: AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set in .env")
        print("Copy .env.example to .env and fill in your Azure AI Search credentials.")
        sys.exit(1)

    client = SearchIndexClient(
        endpoint=config.AZURE_SEARCH_ENDPOINT,
        credential=AzureKeyCredential(config.AZURE_SEARCH_KEY),
    )

    # Define the vector search configuration
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="my-hnsw-config"),
        ],
        profiles=[
            VectorSearchProfile(
                name="my-vector-profile",
                algorithm_configuration_name="my-hnsw-config",
            ),
        ],
    )

    # Define the index schema
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SimpleField(
            name="item_type",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="category",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="color",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchableField(
            name="brand",
            type=SearchFieldDataType.String,
        ),
        SimpleField(
            name="location",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchableField(
            name="normalized_description",
            type=SearchFieldDataType.String,
        ),
        SearchField(
            name="distinctive_features",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
        ),
        SimpleField(
            name="timestamp",
            type=SearchFieldDataType.DateTimeOffset,
        ),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="my-vector-profile",
        ),
    ]

    index = SearchIndex(
        name=config.AZURE_SEARCH_INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
    )

    # Create or update the index
    result = client.create_or_update_index(index)
    print(f"Index '{result.name}' created/updated successfully.")
    print(f"  Fields: {len(result.fields)}")
    print(f"  Vector search profiles: {len(result.vector_search.profiles)}")


if __name__ == "__main__":
    print(f"Creating Azure AI Search index: '{config.AZURE_SEARCH_INDEX_NAME}'")
    print(f"Endpoint: {config.AZURE_SEARCH_ENDPOINT}")
    print()
    create_index()
    print("\nDone! You can now run the app with: streamlit run app.py")
