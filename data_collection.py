import requests
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin, urlparse


def get_python_org_docs_urls():
    """Get URLs for Python.org official documentation"""
    base_docs_url = "https://docs.python.org/3/"

    # Key Python documentation sections
    python_doc_urls = [
        f"{base_docs_url}tutorial/introduction.html",
        f"{base_docs_url}tutorial/interpreter.html",
        f"{base_docs_url}tutorial/appetite.html",
        f"{base_docs_url}tutorial/controlflow.html",
        f"{base_docs_url}tutorial/datastructures.html",
        f"{base_docs_url}tutorial/modules.html",
        f"{base_docs_url}tutorial/inputoutput.html",
        f"{base_docs_url}tutorial/errors.html",
        f"{base_docs_url}tutorial/classes.html",
        f"{base_docs_url}tutorial/stdlib.html",
        f"{base_docs_url}tutorial/stdlib2.html",
        f"{base_docs_url}library/functions.html",
        f"{base_docs_url}library/stdtypes.html",
        f"{base_docs_url}library/string.html",
        f"{base_docs_url}library/datetime.html",
        f"{base_docs_url}library/os.html",
        f"{base_docs_url}library/json.html",
        f"{base_docs_url}library/urllib.html",
        f"{base_docs_url}library/pathlib.html",
        f"{base_docs_url}howto/logging.html",
    ]

    return python_doc_urls


def download_document(url, output_dir="python_docs"):
    """Download a single document from Python.org"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        response = requests.get(url)
        response.raise_for_status()

        # Extract filename from URL
        filename = urlparse(url).path.split("/")[-1].replace(".html", "")
        filepath = os.path.join(output_dir, f"{filename}.html")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(response.text)

        print(f"Downloaded: {filename}")
        return filepath

    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None


def download_batch(urls, max_docs=15, delay=1):
    """Download a batch of documents with rate limiting"""
    downloaded = []

    for i, url in enumerate(urls[:max_docs]):
        print(f"Downloading {i+1}/{min(len(urls), max_docs)}: {url}")

        filepath = download_document(url)
        if filepath:
            downloaded.append(filepath)

        time.sleep(delay)

    return downloaded


if __name__ == "__main__":
    urls = get_python_org_docs_urls()
    downloaded_files = download_batch(urls, max_docs=15)
    print(f"\nSuccessfully downloaded {len(downloaded_files)} Python.org documents")
