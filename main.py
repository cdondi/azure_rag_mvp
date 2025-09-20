from fastapi import FastAPI
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()


@app.get("/")
def read_root():
    return {
        "message": "RAG MVP is running!",
        "azure_configured": bool(os.getenv("AZURE_OPENAI_ENDPOINT")),
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
