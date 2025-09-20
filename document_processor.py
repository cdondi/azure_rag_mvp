import os
from bs4 import BeautifulSoup
import re
import json
from typing import List, Dict


def clean_python_org_content(html_content: str) -> str:
    """Extract and clean text content from Python.org documentation"""
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove navigation, sidebar, and footer elements specific to Python.org
    for element in soup(
        [
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "div.sphinxsidebar",
            "div.related",
            "div.footer",
        ]
    ):
        element.decompose()

    # Focus on the main content area
    main_content = (
        soup.find("div", class_="body") or soup.find("div", class_="document") or soup
    )

    # Get text content
    text = main_content.get_text()

    # Clean up whitespace and formatting
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = " ".join(chunk for chunk in chunks if chunk)

    return text


def chunk_text(text: str, max_chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks"""
    words = text.split()
    chunks = []

    for i in range(0, len(words), max_chunk_size - overlap):
        chunk = " ".join(words[i : i + max_chunk_size])
        if chunk.strip() and len(chunk.strip()) > 100:  # Skip very short chunks
            chunks.append(chunk.strip())

    return chunks


def process_document(filepath: str) -> List[Dict]:
    """Process a single HTML document into chunks"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            html_content = f.read()

        filename = os.path.basename(filepath).replace(".html", "")

        # Clean HTML and extract text
        clean_text = clean_python_org_content(html_content)

        # Skip if content is too short
        if len(clean_text) < 200:
            print(f"  - Skipping {filename}: content too short")
            return []

        # Chunk the text
        chunks = chunk_text(clean_text)

        # Create document chunks with metadata
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_data = {
                "id": f"{filename}_chunk_{i}",
                "source_file": filename,
                "chunk_index": i,
                "content": chunk,
                "content_length": len(chunk),
            }
            processed_chunks.append(chunk_data)

        return processed_chunks

    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return []


def process_all_documents(docs_dir: str = "python_docs") -> List[Dict]:
    """Process all HTML documents in the python_docs directory"""
    all_chunks = []

    if not os.path.exists(docs_dir):
        print(f"Directory {docs_dir} not found!")
        return all_chunks

    html_files = [f for f in os.listdir(docs_dir) if f.endswith(".html")]
    print(f"Found {len(html_files)} HTML files to process")

    for filename in html_files:
        filepath = os.path.join(docs_dir, filename)
        print(f"Processing: {filename}")

        chunks = process_document(filepath)
        all_chunks.extend(chunks)
        print(f"  - Created {len(chunks)} chunks")

    return all_chunks


if __name__ == "__main__":
    # Process all documents
    processed_chunks = process_all_documents()

    # Save processed chunks to JSON
    output_file = "python_docs_processed.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(processed_chunks, f, indent=2, ensure_ascii=False)

    print(f"\nProcessing complete!")
    print(f"Total chunks created: {len(processed_chunks)}")
    print(f"Saved to: {output_file}")

    # Show statistics
    if processed_chunks:
        avg_length = sum(chunk["content_length"] for chunk in processed_chunks) / len(
            processed_chunks
        )
        print(f"Average chunk length: {avg_length:.0f} characters")
        print(f"\nSample chunk preview:")
        print(f"ID: {processed_chunks[0]['id']}")
        print(f"Content: {processed_chunks[0]['content'][:300]}...")
