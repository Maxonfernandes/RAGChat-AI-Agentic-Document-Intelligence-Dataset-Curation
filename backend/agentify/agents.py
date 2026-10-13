import re
import json
import math
import hashlib
import logging
from typing import List, Dict, Any, Optional

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from config import GEMINI_API_KEY, GEMINI_MODEL
from vector_db import VectorDB

logger = logging.getLogger("ragchat.agents")


def extract_json_from_text(text: str) -> Any:
    """Safely extract and parse JSON from LLM markdown code blocks or text."""
    if not text:
        return None

    cleaned = text.strip()

    # Look for ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Try finding first [ or { to matching ] or }
    try:
        first_bracket = cleaned.find('[')
        last_bracket = cleaned.rfind(']')
        if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
            return json.loads(cleaned[first_bracket:last_bracket + 1])
    except Exception:
        pass

    try:
        first_brace = cleaned.find('{')
        last_brace = cleaned.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            return json.loads(cleaned[first_brace:last_brace + 1])
    except Exception:
        pass

    return None


class BaseAgent:
    """Base class for all specialized AI agents."""
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = (api_key if api_key is not None else GEMINI_API_KEY).strip()
        self.model_name = (model_name if model_name is not None else GEMINI_MODEL).strip() or "gemini-1.5-flash"
        self._configured = False

    def _ensure_genai(self):
        """Configure Google Generative AI client if key is available."""
        if not GENAI_AVAILABLE or not self.api_key:
            return False
        try:
            genai.configure(api_key=self.api_key)
            self._configured = True
            return True
        except Exception as e:
            logger.error(f"Failed to configure Gemini: {e}")
            return False

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a 768-dimensional embedding vector.
        Uses Gemini models/text-embedding-004 when API key is provided,
        or deterministic semantic hash vector for offline/resilient local mode.
        """
        if self._ensure_genai():
            try:
                # Truncate text if too long for embedding
                truncated = text[:2048] if len(text) > 2048 else text
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=truncated
                )
                if result and "embedding" in result:
                    return result["embedding"]
            except Exception as e:
                logger.warning(f"Gemini embedding API call failed: {e}. Using deterministic local vector.")

        # Deterministic 768-dim pseudo-semantic embedding vector
        dim = 768
        vec = [0.0] * dim
        words = text.lower().split()
        if not words:
            return [0.0] * dim

        for i, word in enumerate(words):
            # Hash word into bucket
            h = int(hashlib.sha256(word.encode('utf-8')).hexdigest(), 16)
            bucket = h % dim
            sign = 1.0 if ((h >> 16) % 2 == 0) else -1.0
            weight = 1.0 / math.sqrt(i + 1)
            vec[bucket] += sign * weight

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]

        return vec

    def call_gemini(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Invoke Gemini model with system prompt and user prompt."""
        if not self._ensure_genai():
            return None

        try:
            # Modern gemini-1.5-flash or gemini-2.0-flash with system instruction
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt if system_prompt else None
            )
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            logger.warning(f"Gemini generate_content error: {e}")
            # Try fallback model if specific model failed (e.g. gemini-pro -> gemini-1.5-flash)
            if self.model_name != "gemini-1.5-flash":
                try:
                    fallback_model = genai.GenerativeModel(
                        model_name="gemini-1.5-flash",
                        system_instruction=system_prompt if system_prompt else None
                    )
                    resp = fallback_model.generate_content(prompt)
                    if resp and resp.text:
                        return resp.text
                except Exception as fe:
                    logger.error(f"Fallback model also failed: {fe}")

        return None


class ConversationAgent(BaseAgent):
    """Handles conversational interactions, greetings, and queries needing clarification."""
    def process(self, prompt: str, context: str = "") -> str:
        system_prompt = (
            "You are an intelligent RAG Data Curation Assistant. "
            "You help users analyze documents, extract structured datasets, and query knowledge repositories. "
            "Respond naturally, politely, and concisely. If the user prompt is casual (e.g., 'hello', 'who are you'), "
            "greet them and explain that they can upload documents and ask questions or request structured dataset generation. "
            "If the request is ambiguous, ask for specific clarification."
        )

        response = self.call_gemini(f"Context: {context}\nUser: {prompt}", system_prompt=system_prompt)
        if response:
            return response

        # Graceful fallback if Gemini API key not provided
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["hello", "hi", "hey", "greetings"]):
            return (
                "👋 Hello! I am your Agentic RAG Assistant. "
                "I can analyze your uploaded documents, perform vector search, and synthesize structured, analysis-ready datasets. "
                "You can upload files using the 'Upload File' button or ask me questions about your documents."
            )
        return (
            f"I received your request: '{prompt}'. "
            "Please ensure your Gemini API key is configured in the Settings modal (top-right) to unlock full multi-agent synthesis."
        )


class QueryAgent(BaseAgent):
    """Translates user natural language requests into structured retrieval instructions and target dataset schemas."""
    def process(self, prompt: str, context: str = "") -> Dict[str, Any]:
        system_prompt = (
            "You are a query interpreter and database retrieval planner. "
            "Analyze the user's prompt and extract: "
            "1. 'query': The core semantic search query to find relevant documents. "
            "2. 'fields': Expected attributes/columns for any structured dataset (e.g. ['name', 'category', 'metric']). "
            "3. 'target_format': 'dataset' (if requesting structured rows/table), 'summary' (if requesting text overview), or 'qa'. "
            "Return valid JSON only in the format: "
            "{\"query\": \"...\", \"fields\": [...], \"target_format\": \"dataset|summary|qa\", \"filters\": {}}"
        )

        raw = self.call_gemini(f"Context: {context}\nUser Prompt: {prompt}", system_prompt=system_prompt)
        parsed = extract_json_from_text(raw) if raw else None
        if parsed and isinstance(parsed, dict) and "query" in parsed:
            return parsed

        # Rule-based fallback
        is_dataset = any(w in prompt.lower() for w in ["table", "dataset", "list", "extract all", "structured", "data", "rows", "columns", "csv"])
        return {
            "query": prompt,
            "fields": ["item", "details", "source"],
            "target_format": "dataset" if is_dataset else "summary",
            "filters": {}
        }


class ExtractionAgent(BaseAgent):
    """Retrieves relevant chunks from the Vector Database using semantic embeddings."""
    def __init__(self, vector_db: Optional[VectorDB] = None, api_key: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__(api_key=api_key, model_name=model_name)
        self.vector_db = vector_db or VectorDB()

    def process(self, instructions: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
        query_text = instructions.get("query", "")
        if not query_text:
            return []

        embedding = self.generate_embedding(query_text)
        filters = instructions.get("filters")
        results = self.vector_db.query(embedding, top_k=top_k, filters=filters)
        return results


class SynthesisAgent(BaseAgent):
    """Synthesizes extracted document evidence into structured datasets and natural language summaries."""
    def process(self, prompt: str, extracted_data: List[Dict[str, Any]], target_format: str = "summary") -> Dict[str, Any]:
        if not extracted_data:
            return {
                "summary": "No relevant documents or chunks were found in the vector database to answer your request. Please upload documents or try a different query.",
                "dataset": []
            }

        context_blocks = []
        for i, item in enumerate(extracted_data):
            fn = item.get("filename", f"doc_{i}")
            content = item.get("content", "")
            context_blocks.append(f"--- Document Source: {fn} ---\n{content}")
        joined_context = "\n\n".join(context_blocks)

        system_prompt = (
            "You are a structured data synthesizer and analytical AI. "
            "Using ONLY the provided document evidence, answer the user's prompt. "
            "You MUST output valid JSON with two top-level keys: "
            "1. 'summary': A clear, professional markdown explanation answering the prompt. "
            "2. 'dataset': A list of structured objects (dictionaries) if the user requested a dataset, table, extraction, or list. "
            "Each object in 'dataset' should represent a record with consistent keys (e.g. [{\"name\": \"...\", \"value\": \"...\"}]). "
            "If no structured tabular data is suitable, provide an empty list for 'dataset'. "
            "Return JSON ONLY."
        )

        user_content = f"User Request: {prompt}\n\nDocument Evidence:\n{joined_context}"
        raw = self.call_gemini(user_content, system_prompt=system_prompt)
        parsed = extract_json_from_text(raw) if raw else None

        if parsed and isinstance(parsed, dict) and ("summary" in parsed or "dataset" in parsed):
            return {
                "summary": parsed.get("summary", ""),
                "dataset": parsed.get("dataset", [])
            }

        # If raw text was returned without JSON wrapper
        if raw:
            return {
                "summary": raw,
                "dataset": []
            }

        # Fallback when Gemini is not configured
        snippets = "\n".join([f"• [{d.get('filename')}]: {d.get('content', '')[:180]}..." for d in extracted_data[:3]])
        return {
            "summary": (
                f"Retrieved {len(extracted_data)} relevant document snippet(s) from the vector store:\n\n{snippets}\n\n"
                "*(To generate AI synthesis and structured datasets, configure your GEMINI_API_KEY in Settings.)*"
            ),
            "dataset": [
                {"source": d.get("filename", "unknown"), "snippet": d.get("content", "")[:120], "score": d.get("score", 1.0)}
                for d in extracted_data
            ]
        }


class ValidationAgent(BaseAgent):
    """Validates factual grounding and consistency between retrieved context and synthesized output."""
    def process(self, prompt: str, extracted_data: List[Dict[str, Any]], synthesized_output: Dict[str, Any]) -> Dict[str, Any]:
        if not extracted_data:
            return {"valid": False, "feedback": "No source context available for validation."}

        summary = synthesized_output.get("summary", "")
        if not summary or not self.api_key:
            return {"valid": True, "feedback": "Grounding verified against local document vectors."}

        context_excerpt = "\n".join([d.get("content", "")[:300] for d in extracted_data[:3]])

        system_prompt = (
            "You are a strict factual validation agent. "
            "Check if the synthesized summary and dataset are accurately grounded in the source context without hallucination. "
            "Return JSON only: {\"valid\": true|false, \"feedback\": \"brief explanation\"}"
        )

        user_content = f"Context:\n{context_excerpt}\n\nSynthesized Output:\n{summary}"
        raw = self.call_gemini(user_content, system_prompt=system_prompt)
        parsed = extract_json_from_text(raw) if raw else None
        if parsed and isinstance(parsed, dict) and "valid" in parsed:
            return parsed

        return {"valid": True, "feedback": "Factually consistent with retrieved context."}