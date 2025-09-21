from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from services import AzureOpenAIService, AzureSearchService

load_dotenv()

app = FastAPI(
    title="Python RAG API",
    description="Retrieval-Augmented Generation API for Python Documentation",
    version="1.0.0",
)

# Set up Jinja2 templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Azure OpenAI service
openai_service = AzureOpenAIService()
search_service = AzureSearchService()


# Request models for better API documentation and validation
class QueryRequest(BaseModel):
    question: str
    max_results: int = 3


class TextRequest(BaseModel):
    text: str


@app.get("/")
def read_root(request: Request):
    """Root endpoint - basic welcome message"""
    return templates.TemplateResponse("chat.html", {"request": request})


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring and deployment"""
    return {"status": "healthy", "service": "rag-api", "version": "1.0.0"}


@app.post("/ask")
def ask_question(request: QueryRequest):
    """
    Main RAG endpoint: Ask a question about Python and get an AI-generated answer
    1. Query → Convert question to embedding
    2. Search → Find relevant document chunks
    3. Generate → Create answer using GPT with context
    4. Respond → Return structured answer with sources
    """

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        # Step 1: Convert question to embedding
        question_embedding = openai_service.get_embedding(question)
        if question_embedding is None:
            raise HTTPException(
                status_code=500, detail="Failed to generate question embedding"
            )

        # Step 2: Search for relevant documents
        search_results = search_service.vector_search(
            question_embedding, top_k=request.max_results
        )
        if search_results is None:
            raise HTTPException(status_code=500, detail="Search operation failed")

        # Step 3: Generate answer using retrieved context
        answer = openai_service.generate_rag_response(question, search_results)
        if answer is None:
            raise HTTPException(status_code=500, detail="Failed to generate response")

        # Step 4: Return structured response
        return {
            "question": question,
            "answer": answer,
            "sources_used": len(search_results),
            "sources": [
                {
                    "source_file": doc["source_file"],
                    "chunk_index": doc["chunk_index"],
                    "preview": doc["content"][:100] + "...",
                }
                for doc in search_results
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.post("/test-embedding")
def test_embedding(text: dict):
    """Test endpoint to verify embedding generation works"""
    input_text = text.get("text", "")

    if not input_text:
        raise HTTPException(status_code=400, detail="Text field is required")

    embedding = openai_service.get_embedding(input_text)

    if embedding is None:
        raise HTTPException(status_code=500, detail="Failed to generate embedding")

    return {
        "text": input_text,
        "embedding_dimensions": len(embedding),
        "embedding_preview": embedding[:5],  # Show first 5 values
    }


@app.post("/test-search")
def test_search(query: dict):
    """Test endpoint to verify search functionality works"""
    query_text = query.get("query", "")

    if not query_text:
        raise HTTPException(status_code=400, detail="Query field is required")

    # Step 1: Convert query to embedding
    query_embedding = openai_service.get_embedding(query_text)
    if query_embedding is None:
        raise HTTPException(
            status_code=500, detail="Failed to generate query embedding"
        )

    # Step 2: Search for similar documents
    search_results = search_service.vector_search(query_embedding, top_k=3)
    if search_results is None:
        raise HTTPException(status_code=500, detail="Search failed")

    return {
        "query": query_text,
        "results_found": len(search_results),
        "results": [
            {
                "source": doc["source_file"],
                "chunk": doc["chunk_index"],
                "preview": doc["content"][:150] + "...",
            }
            for doc in search_results
        ],
    }


@app.get("/search-stats")
def get_search_stats():
    """Get statistics about the search index"""
    stats = search_service.get_search_stats()
    if stats is None:
        raise HTTPException(status_code=500, detail="Failed to get search statistics")

    return stats
