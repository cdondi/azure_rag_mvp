import json
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def delete_index_if_exists():
    """Delete the index if it already exists"""

    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_KEY")

    url = f"{endpoint}/indexes/python-docs-index?api-version=2023-11-01"

    headers = {"api-key": key}

    try:
        response = requests.delete(url, headers=headers)
        if response.status_code == 204:
            print("Existing index deleted successfully")
        elif response.status_code == 404:
            print("No existing index to delete")
        else:
            print(f"Error deleting index: {response.status_code}")
    except Exception as e:
        print(f"Error deleting index: {e}")


def create_search_index():
    """Create the search index using REST API"""

    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_KEY")

    url = f"{endpoint}/indexes?api-version=2023-11-01"

    headers = {"Content-Type": "application/json", "api-key": key}

    # Index definition with vector search
    index_definition = {
        "name": "python-docs-index",
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "searchable": False},
            {
                "name": "source_file",
                "type": "Edm.String",
                "filterable": True,
                "searchable": False,
            },
            {
                "name": "chunk_index",
                "type": "Edm.Int32",
                "filterable": True,
                "searchable": False,
            },
            {
                "name": "content",
                "type": "Edm.String",
                "searchable": True,
                "analyzer": "standard.lucene",
            },
            {"name": "content_length", "type": "Edm.Int32", "searchable": False},
            {
                "name": "embedding",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "dimensions": 1536,
                "vectorSearchProfile": "myHnswProfile",
            },
        ],
        "vectorSearch": {
            "algorithms": [
                {
                    "name": "myHnsw",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "metric": "cosine",
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                    },
                }
            ],
            "profiles": [{"name": "myHnswProfile", "algorithm": "myHnsw"}],
        },
    }

    try:
        response = requests.post(url, headers=headers, json=index_definition)
        if response.status_code == 201:
            print("Index 'python-docs-index' created successfully")
            return True
        else:
            print(f"Error creating index: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error creating index: {e}")
        return False


def upload_documents():
    """Upload document chunks using REST API"""

    # Load the chunks with embeddings
    with open("chunks_with_embeddings.json", "r", encoding="utf-8") as f:
        chunks = json.load(f)

    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_KEY")

    url = f"{endpoint}/indexes/python-docs-index/docs/index?api-version=2023-11-01"

    headers = {"Content-Type": "application/json", "api-key": key}

    # Prepare documents for upload
    documents = []
    for chunk in chunks:
        if "embedding" in chunk:
            doc = {
                "@search.action": "upload",
                "id": chunk["id"],
                "source_file": chunk["source_file"],
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "content_length": chunk["content_length"],
                "embedding": chunk["embedding"],
            }
            documents.append(doc)

    batch_data = {"value": documents}

    try:
        response = requests.post(url, headers=headers, json=batch_data)
        if response.status_code == 200:
            result = response.json()
            successful_uploads = sum(1 for r in result["value"] if r["status"])
            print(
                f"Successfully uploaded {successful_uploads}/{len(documents)} documents"
            )
            return True
        else:
            print(f"Error uploading documents: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error uploading documents: {e}")
        return False


if __name__ == "__main__":
    print("Deleting existing index if it exists...")
    delete_index_if_exists()

    print("Creating Azure AI Search index...")
    if create_search_index():
        print("\nUploading documents with embeddings...")
        if upload_documents():
            print("\nIndexing complete! Your RAG knowledge base is ready.")
        else:
            print("\nFailed to upload documents.")
    else:
        print("\nFailed to create index.")
