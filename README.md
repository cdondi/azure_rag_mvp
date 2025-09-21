# Azure RAG Pipeline Documentation

## Project Overview

This project implements a Retrieval-Augmented Generation (RAG) system using Azure services to create an intelligent Q&A system based on Python documentation.

## Core Components

### Data Collection & Processing

#### `data_collection.py`

**Purpose:** Downloads Python documentation from python.org  
**Key Functions:**

- `get_python_org_docs_urls()` - Defines list of Python.org documentation URLs to scrape
- `download_document()` - Downloads individual HTML documents to local storage
- `download_batch()` - Manages bulk downloading with rate limiting

**Output:** HTML files stored in `python_docs/` directory

#### `document_processor.py`

**Purpose:** Converts raw HTML documents into structured, searchable text chunks  
**Key Functions:**

- `clean_python_org_content()` - Extracts clean text from HTML, removes navigation/formatting
- `chunk_text()` - Splits large documents into 500-word chunks with 50-word overlap
- `process_document()` - Processes individual files and adds metadata
- `process_all_documents()` - Batch processes all HTML files

**Output:** `python_docs_processed.json` - Structured JSON with text chunks and metadata

### Embedding Generation

#### `generate_embeddings.py`

**Purpose:** Converts text chunks into vector embeddings using Azure OpenAI  
**Key Functions:**

- `setup_azure_openai()` - Initializes Azure OpenAI client with credentials
- `generate_embedding()` - Converts single text chunk to 1536-dimension vector
- `process_chunks_with_embeddings()` - Batch processes chunks with rate limiting

**Output:** `chunks_with_embeddings_test.json` - Text chunks with vector embeddings

### Search Index Management

#### `azure_search_indexer.py`

**Purpose:** Creates and manages Azure AI Search index with vector search capabilities  
**Key Functions:**

- `create_search_index()` - Creates search index with vector field configuration
- `delete_index_if_exists()` - Manages index cleanup and recreation
- `upload_documents()` - Uploads document chunks and embeddings to Azure AI Search

**Output:** `python-docs-index` in Azure AI Search service

### RAG Pipeline Testing

#### `test_rag_pipeline.py`

**Purpose:** End-to-end testing of the complete RAG system  
**Key Functions:**

- `get_question_embedding()` - Converts user questions to embeddings
- `search_similar_documents()` - Performs vector similarity search in Azure AI Search
- `generate_answer()` - Uses retrieved context to generate answers via Azure OpenAI GPT
- `test_rag_pipeline()` - Orchestrates complete question-answering workflow

**Output:** Generated answers based on retrieved documentation context

### FastAPI Backend

#### `main.py`

**Purpose:** Production-ready FastAPI application providing RESTful API endpoints  
**Key Endpoints:**

- `GET /` - Root endpoint with welcome message
- `GET /health` - Health check endpoint for monitoring and deployment
- `POST /ask` - Main RAG endpoint for question-answering
- `POST /test-embedding` - Test endpoint for embedding generation
- `POST /test-search` - Test endpoint for vector search functionality
- `GET /search-stats` - Endpoint to get search index statistics

**Features:**

- Pydantic models for request validation
- Comprehensive error handling
- Structured JSON responses with source attribution
- Interactive API documentation at `/docs`

#### `services.py`

**Purpose:** Service layer containing business logic for Azure integrations  
**Key Classes:**

**AzureOpenAIService:**

- `get_embedding()` - Converts text to 1536-dimension vectors
- `generate_completion()` - GPT text generation with customizable parameters
- `generate_rag_response()` - Context-aware answer generation using retrieved documents

**AzureSearchService:**

- `vector_search()` - Performs semantic similarity search using embeddings
- `get_search_stats()` - Retrieves index statistics and health information

**Output:** RESTful API service running on `http://localhost:8000`

## Configuration Files

### `.env`

**Purpose:** Stores Azure service credentials and configuration  
**Contents:**

- Azure OpenAI endpoint, API keys, and model deployment names
- Azure AI Search service endpoint and admin keys
- Azure Key Vault URL
- Resource group and API version settings

### `.vscode/settings.json`

**Purpose:** VS Code workspace configuration for Python development  
**Features:**

- Python interpreter path configuration
- Environment variable loading
- Azure cloud integration settings
- Formatting and linting preferences

### `requirements.txt`

**Purpose:** Python package dependencies  
**Key Dependencies:**

- `azure-openai` - Azure OpenAI service integration
- `azure-search-documents` - Azure AI Search client
- `azure-identity` - Azure authentication
- `openai` - OpenAI API client
- `python-dotenv` - Environment variable management
- `beautifulsoup4` - HTML parsing for document processing
- `fastapi` - Modern web framework for building APIs
- `uvicorn` - ASGI server for running FastAPI applications
- `pydantic` - Data validation and settings management
- `requests` - HTTP library for API calls

## Data Flow

1. **Collection:** `data_collection.py` → Downloads HTML files from Python.org
2. **Processing:** `document_processor.py` → Converts to structured text chunks
3. **Embedding:** `generate_embeddings.py` → Creates vector representations
4. **Indexing:** `azure_search_indexer.py` → Uploads to searchable index
5. **API Service:** `main.py` + `services.py` → Provides RESTful endpoints
6. **RAG Pipeline:** User question → embedding → search → context retrieval → GPT generation → response

## Complete RAG Workflow

**User asks question via `/ask` endpoint:**

1. **Question Embedding:** Convert user question to 1536-dimension vector using text-embedding-ada-002
2. **Vector Search:** Find 3 most semantically similar document chunks from Azure AI Search
3. **Context Preparation:** Format retrieved chunks with source metadata
4. **Prompt Engineering:** Combine question + context + system instructions
5. **Answer Generation:** GPT-3.5-Turbo generates contextually-aware response
6. **Response Delivery:** Return structured JSON with answer, sources, and metadata

## Azure Resources Used

- **Azure OpenAI Service:** GPT-3.5-Turbo for text generation, text-embedding-ada-002 for embeddings
- **Azure AI Search:** Vector search index with 50MB free tier storage
- **Azure Key Vault:** Secure credential storage (configured but not actively used)
- **Resource Group:** `rg-rag-mvp-free-2` containing all resources

## Performance Metrics

- **Document Count:** 15 Python.org documentation files
- **Text Chunks:** 202 processed chunks (avg 3,057 characters each)
- **Embeddings:** 10 test embeddings generated (1536 dimensions)
- **Index Storage:** 304.78 KB used (182.05 vector quota units)
- **Response Time:** ~2-3 seconds for complete RAG query
- **API Performance:** FastAPI with async support, auto-generated OpenAPI documentation
- **Rate Limiting:** Handles Azure OpenAI free tier limits (6 requests/minute, 1000 tokens/minute)

## API Usage Examples

### Ask a Question

```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "How do you handle errors in Python?", "max_results": 3}'
```

### Test Embedding Generation

```bash
curl -X POST "http://localhost:8000/test-embedding" \
  -H "Content-Type: application/json" \
  -d '{"text": "Python exception handling"}'
```

### Check Index Statistics

```bash
curl "http://localhost:8000/search-stats"
```

## Development Setup

1. **Environment Setup:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Mac/Linux
   pip install -r requirements.txt
   ```

2. **Configuration:**

   - Create `.env` file with Azure service credentials
   - Update VS Code settings in `.vscode/settings.json`

3. **Run Development Server:**

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access API Documentation:**
   - Interactive docs: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

## Next Steps

This pipeline provides the foundation for:

- **Streamlit Web Interface** - User-friendly frontend for non-technical users
- **Azure App Service Deployment** - Production hosting with CI/CD pipelines
- **Enhanced Document Collection** - Expand beyond 15 docs to comprehensive Python knowledge base
- **Production Scaling** - Upgrade to Standard tier for higher rate limits and performance
- **Monitoring & Analytics** - Application Insights integration for usage tracking
- **Authentication & Authorization** - User management and API key protection
- **Caching Layer** - Redis integration for improved response times
- **Advanced RAG Features** - Query refinement, multi-step reasoning, source ranking
