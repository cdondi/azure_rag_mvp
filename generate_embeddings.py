import json
import os
from openai import AzureOpenAI
from dotenv import load_dotenv
import time
from typing import List, Dict

# Load environment variables
load_dotenv()


def setup_azure_openai():
    """Initialize Azure OpenAI client"""
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )

    return client


def generate_embedding(client, text: str) -> List[float]:
    """Generate embedding for a single text chunk"""
    try:
        response = client.embeddings.create(
            input=text, model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def process_chunks_with_embeddings(
    input_file: str = "python_docs_processed.json", max_chunks: int = 10
):
    """Add embeddings to processed document chunks"""

    # Load processed chunks
    with open(input_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    # Limit chunks for testing
    chunks = chunks[:max_chunks]

    # print(f"Loaded {len(chunks)} chunks")
    print(f"Processing {len(chunks)} chunks (limited for testing)")

    # Initialize Azure OpenAI client
    client = setup_azure_openai()

    # Process chunks with rate limiting
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}: {chunk['id']}")

        # Generate embedding
        embedding = generate_embedding(client, chunk["content"])

        if embedding:
            chunk["embedding"] = embedding
            print(f"  - Generated embedding ({len(embedding)} dimensions)")
        else:
            print(f"  - Failed to generate embedding")

        # Rate limiting for free tier - wait 12 seconds as recommended
        if i < len(chunks) - 1:  # Don't sleep after the last item
            print(f"  - Waiting 12 seconds (rate limit)...")
            time.sleep(12)  # 12 seconds between requests for free tier

    return chunks


if __name__ == "__main__":
    # Generate embeddings for all chunks
    chunks_with_embeddings = process_chunks_with_embeddings()

    # Save chunks with embeddings
    output_file = "chunks_with_embeddings.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(chunks_with_embeddings, f, indent=2)

    successful_embeddings = sum(
        1 for chunk in chunks_with_embeddings if "embedding" in chunk
    )

    print(f"\nEmbedding generation complete!")
    print(
        f"Successfully generated {successful_embeddings}/{len(chunks_with_embeddings)} embeddings"
    )
    print(f"Saved to: {output_file}")
