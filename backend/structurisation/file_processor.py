import os
import re
import csv
import io
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from utils import ensure_dir, categorize_file, get_file_extension
from config import INPUT_DIR, OUTPUT_DIR, FILE_TYPES

logger = logging.getLogger("ragchat.file_processor")


def chunk_text(text: str, chunk_size: int = 700, chunk_overlap: int = 150) -> List[str]:
    """Split text into overlapping semantic chunks."""
    clean = re.sub(r'\s+', ' ', text).strip()
    if not clean:
        return []
    if len(clean) <= chunk_size:
        return [clean]

    chunks = []
    start = 0
    while start < len(clean):
        end = start + chunk_size
        if end >= len(clean):
            chunks.append(clean[start:])
            break

        # Try to break at a sentence boundary (. ! ?)
        split_pos = -1
        for punct in [". ", "! ", "? ", "\n", "; "]:
            p = clean.rfind(punct, start + int(chunk_size * 0.6), end)
            if p != -1 and p > split_pos:
                split_pos = p + len(punct)

        if split_pos != -1:
            chunks.append(clean[start:split_pos].strip())
            start = split_pos - chunk_overlap if split_pos - chunk_overlap > start else split_pos
        else:
            # Fallback to word boundary
            space_pos = clean.rfind(" ", start + int(chunk_size * 0.7), end)
            if space_pos != -1:
                chunks.append(clean[start:space_pos].strip())
                start = space_pos + 1
            else:
                chunks.append(clean[start:end].strip())
                start = end - chunk_overlap

    return [c for c in chunks if len(c) > 15]


class FileProcessor:
    """Processes uploaded files and URLs into structured text chunks."""
    def __init__(self, input_dir: str = None, output_dir: str = None):
        self.input_dir = input_dir or INPUT_DIR
        self.output_dir = output_dir or OUTPUT_DIR
        ensure_dir(self.input_dir)
        ensure_dir(self.output_dir)

    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Process a single file and return a list of chunk dictionaries:
        [{filename, content, chunk_index, type, metadata}]
        """
        filename = os.path.basename(file_path)
        ext = get_file_extension(file_path)
        file_type = categorize_file(file_path, FILE_TYPES)

        raw_text = ""
        metadata = {"file_type": file_type, "extension": ext}

        try:
            if ext == ".pdf":
                raw_text = self._process_pdf(file_path)
            elif ext in [".txt", ".md"]:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    raw_text = f.read()
            elif ext == ".csv":
                raw_text = self._process_csv(file_path)
            elif ext == ".json":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    try:
                        data = json.load(f)
                        raw_text = json.dumps(data, indent=2)
                    except Exception:
                        raw_text = f.read()
            elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
                raw_text = self._process_image(file_path)
            else:
                # Default text read
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    raw_text = f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raw_text = f"File: {filename} (Content could not be parsed: {e})"

        # Split into chunks
        chunks = chunk_text(raw_text)
        if not chunks:
            chunks = [raw_text[:500]] if raw_text else [f"Empty document: {filename}"]

        processed_chunks = []
        for idx, chunk in enumerate(chunks):
            processed_chunks.append({
                "filename": filename,
                "content": chunk,
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "type": file_type,
                "metadata": metadata
            })

        return processed_chunks

    def _process_pdf(self, file_path: str) -> str:
        """Extract text from PDF using pure python pypdf (with OCR fallback if needed)."""
        text_parts = []
        if PYPDF_AVAILABLE:
            try:
                reader = pypdf.PdfReader(file_path)
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_parts.append(f"[Page {i + 1}]\n{page_text.strip()}")
            except Exception as e:
                logger.warning(f"pypdf extraction error for {file_path}: {e}")

        # If pypdf extracted text, return it
        if text_parts:
            return "\n\n".join(text_parts)

        # Optional OCR fallback if pdf had scanned images
        if OCR_AVAILABLE:
            try:
                import pdf2image
                images = pdf2image.convert_from_path(file_path)
                for i, img in enumerate(images):
                    t = pytesseract.image_to_string(img)
                    if t.strip():
                        text_parts.append(f"[Scanned Page {i + 1}]\n{t.strip()}")
            except Exception as oe:
                logger.warning(f"OCR fallback failed: {oe}")

        return "\n\n".join(text_parts) if text_parts else "Empty or unparseable PDF document."

    def _process_csv(self, file_path: str) -> str:
        """Parse CSV into tabular text chunks."""
        rows = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            header = None
            for i, row in enumerate(reader):
                if i == 0:
                    header = row
                    rows.append(f"Header: {', '.join(header)}")
                else:
                    if header:
                        row_desc = ", ".join([f"{h}: {val}" for h, val in zip(header, row)])
                        rows.append(f"Row {i}: {row_desc}")
                    else:
                        rows.append(f"Row {i}: {', '.join(row)}")
        return "\n".join(rows)

    def _process_image(self, file_path: str) -> str:
        """Extract text from image using OCR if available."""
        if OCR_AVAILABLE:
            try:
                img = Image.open(file_path)
                ocr_text = pytesseract.image_to_string(img).strip()
                if ocr_text:
                    return f"Image OCR Text ({os.path.basename(file_path)}):\n{ocr_text}"
            except Exception as e:
                logger.warning(f"Image OCR failed: {e}")
        return f"Image file: {os.path.basename(file_path)}"

    def process_url(self, url: str) -> List[Dict[str, Any]]:
        """Fetch content from a webpage URL and chunk it."""
        url_text = ""
        try:
            if HTTPX_AVAILABLE:
                with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                    resp = client.get(url, headers={"User-Agent": "Mozilla/5.0 RAGChat/1.0"})
                    html = resp.text
            else:
                import urllib.request
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 RAGChat/1.0"})
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')

            # Clean HTML tags and scripts
            clean = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.I)
            clean = re.sub(r'<style[\s\S]*?</style>', '', clean, flags=re.I)
            clean = re.sub(r'<[^>]+>', ' ', clean)
            url_text = re.sub(r'\s+', ' ', clean).strip()

        except Exception as e:
            logger.error(f"Failed to fetch URL {url}: {e}")
            url_text = f"URL content fetch failed for {url}: {str(e)}"

        chunks = chunk_text(url_text)
        if not chunks:
            chunks = [url_text]

        filename = url.replace("https://", "").replace("http://", "").split("/")[0] or "webpage"
        return [
            {
                "filename": f"url_{filename}",
                "content": c,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "type": "webpage",
                "metadata": {"url": url}
            }
            for i, c in enumerate(chunks)
        ]

    def process_files(self) -> Dict[str, List[Tuple[str, str]]]:
        """Legacy helper for processing all files in input_dir."""
        results: Dict[str, List[Tuple[str, str]]] = {
            "text": [], "image": [], "document": [], "audio": [], "video": []
        }
        for fn in os.listdir(self.input_dir):
            fp = os.path.join(self.input_dir, fn)
            if os.path.isfile(fp):
                cat = categorize_file(fp, FILE_TYPES)
                chunks = self.process_file(fp)
                combined = " ".join([c["content"] for c in chunks])
                if cat in results:
                    results[cat].append((fn, combined))
                else:
                    results["text"].append((fn, combined))
        return results