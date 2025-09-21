import os
import json
import requests
from openai import AzureOpenAI
from dotenv import load_dotenv

"""

"""

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


def get_question_embedding(client, question: str):
    """Convert user question to embedding"""
    try:
        response = client.embeddings.create(
            input=question, model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating question embedding: {e}")
        return None


def search_similar_documents(question_embedding, top_k=3):
    """Search for similar documents using vector similarity"""

    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_KEY")

    url = f"{endpoint}/indexes/python-docs-index/docs/search?api-version=2023-11-01"

    headers = {"Content-Type": "application/json", "api-key": key}

    search_body = {
        "count": True,
        "top": top_k,
        "vectorQueries": [
            {
                "vector": question_embedding,
                "k": top_k,
                "fields": "embedding",
                "kind": "vector",
            }
        ],
        "select": "id,source_file,content,chunk_index",
    }

    try:
        response = requests.post(url, headers=headers, json=search_body)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Search error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Error searching documents: {e}")
        return None


def generate_answer(client, question: str, context_docs):
    """Generate answer using retrieved documents as context"""

    # Combine context from retrieved documents
    context = "\n\n".join([doc["content"] for doc in context_docs])

    # Create prompt with context
    prompt = f"""Based on the following Python documentation context, answer the user's question.

Context:
{context}

Question: {question}

Answer: Provide a helpful answer based on the context above. If the context doesn't contain enough information to answer the question, say so."""

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful Python documentation assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating answer: {e}")
        return None


def test_rag_pipeline(question: str):
    """Test the complete RAG pipeline"""

    print(f"Question: {question}")
    print("=" * 50)

    # Step 1: Initialize OpenAI client
    client = setup_azure_openai()

    # Step 2: Convert question to embedding
    print("Step 1: Converting question to embedding...")
    question_embedding = get_question_embedding(client, question)
    if not question_embedding:
        return

    # Step 3: Search for similar documents
    print("Step 2: Searching for relevant documents...")
    search_results = search_similar_documents(question_embedding)
    if not search_results:
        return

    print(f"Found {len(search_results['value'])} relevant documents:")
    for i, doc in enumerate(search_results["value"]):
        print(f"  {i+1}. {doc['source_file']} (chunk {doc['chunk_index']})")
        print(f"     Preview: {doc['content'][:100]}...")

    # Step 4: Generate answer using context
    print("\nStep 3: Generating answer...")
    answer = generate_answer(client, question, search_results["value"])

    if answer:
        print(f"\nAnswer:\n{answer}")

    return answer


if __name__ == "__main__":
    # Test with a Python-related question
    test_question = "How do you handle errors in Python?"
    test_rag_pipeline(test_question)
