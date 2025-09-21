from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, validator, Field
import os
from dotenv import load_dotenv
from services import AzureOpenAIService, AzureSearchService
from logging_config import configure_logging, get_logger, HealthChecker
import time
import os

load_dotenv()

# Configure logging
configure_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger("main")


# Enhanced request models for chat
class ChatRequest(BaseModel):
    question: str
    max_results: int = 3

    @validator("question")
    def question_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Question cannot be empty")
        if len(v.strip()) > 500:
            raise ValueError("Question too long (max 500 characters)")
        return v.strip()

    @validator("max_results")
    def max_results_must_be_valid(cls, v):
        if v < 1 or v > 10:
            raise ValueError("max_results must be between 1 and 10")
        return v


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources_used: int
    sources: list
    response_time_ms: int
    status: str = "success"


app = FastAPI(
    title="Python RAG API",
    description="Retrieval-Augmented Generation API for Python Documentation",
    version="1.0.0",
)

# Set up Jinja2 templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Azure OpenAI service
logger.info("Initializing Azure services")
openai_service = AzureOpenAIService()
search_service = AzureSearchService()
health_checker = HealthChecker()

logger.info("RAG application initialized successfully")


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
    """Basic health check endpoint for container orchestration"""
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "service": "rag-api",
        "version": "1.0.0",
        "timestamp": time.time(),
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check for monitoring systems"""
    start_time = time.time()
    logger.info("Detailed health check started")

    try:
        # Check OpenAI service
        openai_health = health_checker.check_openai_service(openai_service)

        # Check search service
        search_health = health_checker.check_search_service(search_service)

        # Overall system health
        overall_healthy = openai_health["healthy"] and search_health["healthy"]

        response_time = int((time.time() - start_time) * 1000)

        result = {
            "status": "healthy" if overall_healthy else "degraded",
            "services": [openai_health, search_health],
            "response_time_ms": response_time,
            "timestamp": time.time(),
        }

        logger.info(
            "Detailed health check completed",
            overall_healthy=overall_healthy,
            response_time_ms=response_time,
        )

        return result

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e), "timestamp": time.time()}


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


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Enhanced chat endpoint with better error handling and validation"""
    import time

    start_time = time.time()

    try:
        logger.info(f"Processing chat request: {request.question[:50]}...")

        # Step 1: Generate question embedding
        question_embedding = openai_service.get_embedding(request.question)
        if question_embedding is None:
            logger.error("Failed to generate embedding for question")
            raise HTTPException(
                status_code=503,
                detail="AI service temporarily unavailable. Please try again.",
            )

        # Step 2: Search for relevant documents
        search_results = search_service.vector_search(
            question_embedding, top_k=request.max_results
        )
        if search_results is None:
            logger.error("Search service failed")
            raise HTTPException(
                status_code=503,
                detail="Search service temporarily unavailable. Please try again.",
            )

        # Step 3: Generate AI response
        answer = openai_service.generate_rag_response(request.question, search_results)
        if answer is None:
            logger.error("Failed to generate AI response")
            raise HTTPException(
                status_code=503,
                detail="AI response generation failed. Please try again.",
            )

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Step 4: Format and return response
        response = ChatResponse(
            question=request.question,
            answer=answer,
            sources_used=len(search_results),
            sources=[
                {
                    "source_file": doc["source_file"],
                    "chunk_index": doc["chunk_index"],
                    "preview": doc["content"][:100] + "...",
                    "relevance": (
                        "high" if i < 2 else "medium"
                    ),  # Mock relevance scoring
                }
                for i, doc in enumerate(search_results)
            ],
            response_time_ms=response_time_ms,
        )

        logger.info(f"Chat request completed in {response_time_ms}ms")

        # For application Insights metrics
        logger.info(
            "RAG request metrics",
            extra={
                "custom_dimensions": {
                    "response_time_ms": response_time_ms,
                    "sources_found": len(search_results),
                    "question_length": len(request.question),
                }
            },
        )

        return response

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred. Please try again."
        )


@app.post("/chat/validate")
async def validate_question(request: dict):
    """Endpoint to validate questions before sending"""
    question = request.get("question", "").strip()

    errors = []

    if not question:
        errors.append("Question cannot be empty")
    elif len(question) > 500:
        errors.append("Question too long (max 500 characters)")
    elif len(question) < 5:
        errors.append("Question too short (min 5 characters)")

    # Check for potentially problematic content
    problematic_words = ["hack", "exploit", "malicious", "illegal"]
    if any(word in question.lower() for word in problematic_words):
        errors.append("Question contains inappropriate content")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "character_count": len(question),
        "estimated_tokens": len(question.split()) * 1.3,  # Rough token estimate
    }


@app.get("/chat/health")
async def chat_health_check():
    """Specific health check for chat functionality"""
    try:
        # Test OpenAI service
        test_embedding = openai_service.get_embedding("test")
        openai_healthy = test_embedding is not None

        # Test search service
        search_stats = search_service.get_search_stats()
        search_healthy = search_stats is not None

        overall_healthy = openai_healthy and search_healthy

        return {
            "status": "healthy" if overall_healthy else "degraded",
            "services": {
                "openai": "healthy" if openai_healthy else "unhealthy",
                "search": "healthy" if search_healthy else "unhealthy",
            },
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e), "timestamp": time.time()}
