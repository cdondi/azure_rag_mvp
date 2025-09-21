import os
from openai import AzureOpenAI
from dotenv import load_dotenv
from typing import List, Optional
import requests
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()


class AzureOpenAIService:
    """
    Service class to handle Azure OpenAI operations
    This code encapsulates all Azure OpenAI operations in a reusable class
    """

    def __init__(self):
        # Initialize the Azure OpenAI client. Load credentials and create the OpenAI client
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )

        # Store deployment names for easy access
        self.embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
        self.chat_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

    def get_embedding(self, text: str) -> Optional[List[float]]:
        # Convert text to vector embedding
        try:
            response = self.client.embeddings.create(
                input=text, model=self.embedding_deployment
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None

    def generate_completion(
        self, messages: List[dict], max_tokens: int = 500
    ) -> Optional[str]:
        # Generate text completion using GPT
        try:
            response = self.client.chat.completions.create(
                model=self.chat_deployment,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating completion: {e}")
            return None

    def generate_rag_response(
        self, question: str, context_documents: List[Dict]
    ) -> Optional[str]:
        """Generate response using retrieved documents as context"""

        # Combine context from retrieved documents
        if context_documents:
            context = "\n\n".join(
                [
                    f"Source: {doc['source_file']} (chunk {doc['chunk_index']})\n{doc['content']}"
                    for doc in context_documents
                ]
            )
            print("::::::::::::::::::::::::: Context 1 :::::::::::::::::::::::::")
            print(context)
        else:
            context = "No relevant context found in the documentation."
            print("::::::::::::::::::::::::: Context 2 :::::::::::::::::::::::::")
            print(context)

        # Create system prompt for RAG
        system_prompt = """You are a helpful Python documentation assistant. Use the provided context from Python documentation to answer questions. 
        If the context contains relevant information, use it to provide a detailed answer.
        If the context doesn't contain enough information, acknowledge this and provide general Python knowledge to help the user.
        Always be helpful and provide practical examples when possible."""

        # Create user prompt with context
        user_prompt = f"""Context from Python documentation:
        {context}

        Question: {question}

        Please provide a helpful answer based on the context above and your knowledge of Python."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        return self.generate_completion(messages, max_tokens=800)


class AzureSearchService:
    # Service class to handle Azure AI Search operations
    def __init__(self):
        # Initialize the Azure Search client

        self.endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.api_key = os.getenv("AZURE_SEARCH_KEY")
        self.index_name = "python-docs-index"

        # Validate configuration
        if not all([self.endpoint, self.api_key]):
            raise ValueError("Azure Search endpoint and API key must be configured")

    def vector_search(
        self, query_embedding: List[float], top_k: int = 3
    ) -> Optional[List[Dict]]:
        # Search for similar documents using vector similarity, given an embedding

        url = f"{self.endpoint}/indexes/{self.index_name}/docs/search?api-version=2023-11-01"

        headers = {"Content-Type": "application/json", "api-key": self.api_key}

        search_body = {
            "count": True,
            "top": top_k,
            "vectorQueries": [
                {
                    "vector": query_embedding,
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
                search_results = response.json()
                return search_results.get("value", [])
            else:
                print(f"Search error: {response.status_code}")
                print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"Error searching documents: {e}")
            return None

    def get_search_stats(self) -> Optional[Dict]:
        # Get basic statistics about the search index

        url = f"{self.endpoint}/indexes/{self.index_name}/stats?api-version=2023-11-01"

        headers = {"api-key": self.api_key}

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Stats error: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error getting stats: {e}")
            return None
