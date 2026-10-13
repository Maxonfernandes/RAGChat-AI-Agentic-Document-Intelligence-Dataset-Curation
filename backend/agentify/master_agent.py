import logging
from typing import Dict, Any, Optional

from agents import (
    ConversationAgent,
    QueryAgent,
    ExtractionAgent,
    SynthesisAgent,
    ValidationAgent
)
from vector_db import VectorDB
from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    ASTRA_DB_API_TOKEN,
    ASTRA_DB_ENDPOINT,
    ASTRA_DB_KEYSPACE,
    COLLECTION_NAME
)

logger = logging.getLogger("ragchat.master_agent")


class MasterAgent:
    """
    Master Agent orchestrating specialized sub-agents:
    - ConversationAgent
    - QueryAgent
    - ExtractionAgent
    - SynthesisAgent
    - ValidationAgent
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        vector_db: Optional[VectorDB] = None
    ):
        self.api_key = (api_key if api_key is not None else GEMINI_API_KEY).strip()
        self.model_name = (model_name if model_name is not None else GEMINI_MODEL).strip() or "gemini-1.5-flash"
        self.vector_db = vector_db or VectorDB()
        self.context = ""

        # Sub-agents
        self.conversation_agent = ConversationAgent(api_key=self.api_key, model_name=self.model_name)
        self.query_agent = QueryAgent(api_key=self.api_key, model_name=self.model_name)
        self.extraction_agent = ExtractionAgent(vector_db=self.vector_db, api_key=self.api_key, model_name=self.model_name)
        self.synthesis_agent = SynthesisAgent(api_key=self.api_key, model_name=self.model_name)
        self.validation_agent = ValidationAgent(api_key=self.api_key, model_name=self.model_name)

    def update_config(self, config: Dict[str, Any]):
        """Update API keys and reinitialize agents if keys changed."""
        api_key = config.get("gemini_api_key", self.api_key)
        model_name = config.get("gemini_model", self.model_name)
        astra_token = config.get("astra_api_token", self.vector_db.api_token)
        astra_endpoint = config.get("astra_endpoint", self.vector_db.endpoint)
        astra_keyspace = config.get("astra_keyspace", self.vector_db.keyspace)
        collection = config.get("collection_name", self.vector_db.collection_name)

        if (
            astra_token != self.vector_db.api_token
            or astra_endpoint != self.vector_db.endpoint
            or astra_keyspace != self.vector_db.keyspace
            or collection != self.vector_db.collection_name
        ):
            self.vector_db = VectorDB(
                api_token=astra_token,
                endpoint=astra_endpoint,
                keyspace=astra_keyspace,
                collection_name=collection
            )

        self.api_key = api_key
        self.model_name = model_name

        self.conversation_agent = ConversationAgent(api_key=self.api_key, model_name=self.model_name)
        self.query_agent = QueryAgent(api_key=self.api_key, model_name=self.model_name)
        self.extraction_agent = ExtractionAgent(vector_db=self.vector_db, api_key=self.api_key, model_name=self.model_name)
        self.synthesis_agent = SynthesisAgent(api_key=self.api_key, model_name=self.model_name)
        self.validation_agent = ValidationAgent(api_key=self.api_key, model_name=self.model_name)

    def process_prompt(self, prompt: str, override_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Orchestrate agent pipeline:
        1. Classify prompt intent (casual greeting vs document query)
        2. Query planning & instruction generation
        3. Vector DB retrieval
        4. Structured data & summary synthesis
        5. Factual validation
        """
        if override_config:
            self.update_config(override_config)

        prompt_clean = prompt.strip()
        if not prompt_clean:
            return {
                "agent": "conversation",
                "message": "Please enter a question or command.",
                "prompt": "Please enter a question or command.",
                "dataset": [],
                "sources": [],
                "steps": []
            }

        # Step 1: Detect casual / greeting prompts
        lower = prompt_clean.lower()
        casual_triggers = ["hello", "hi", "hey", "who are you", "what can you do", "help", "good morning", "good evening"]
        is_casual = any(lower == trigger or lower.startswith(trigger + " ") for trigger in casual_triggers)

        if is_casual and not any(w in lower for w in ["document", "pdf", "file", "extract", "data", "table", "dataset"]):
            conv_response = self.conversation_agent.process(prompt_clean, self.context)
            self.context += f"\nUser: {prompt_clean}\nAssistant: {conv_response}"
            return {
                "agent": "conversation",
                "message": conv_response,
                "prompt": conv_response,
                "dataset": [],
                "sources": [],
                "steps": [
                    {
                        "agent": "ConversationAgent",
                        "status": "completed",
                        "description": "Handled conversational greeting & capability overview"
                    }
                ]
            }

        # Step 2: Multi-agent execution for document queries & dataset curation
        steps = []
        try:
            # 1. QueryAgent
            instructions = self.query_agent.process(prompt_clean, self.context)
            steps.append({
                "agent": "QueryAgent",
                "status": "completed",
                "description": f"Analyzed retrieval intent: '{instructions.get('query', prompt_clean)}'"
            })

            # 2. ExtractionAgent
            extracted_data = self.extraction_agent.process(instructions, top_k=6)
            steps.append({
                "agent": "ExtractionAgent",
                "status": "completed",
                "description": f"Retrieved {len(extracted_data)} relevant chunk(s) from Vector DB"
            })

            if not extracted_data:
                # Check if database has any documents at all
                total_docs = self.vector_db.count()
                if total_docs == 0:
                    msg = (
                        "No documents found in the vector store yet. "
                        "Please upload a document (PDF, TXT, CSV, or enter a URL) using the upload panel to query it."
                    )
                else:
                    msg = "No matching information was found in your documents for this query. Try rephrasing or searching with different keywords."

                return {
                    "agent": "conversation",
                    "message": msg,
                    "prompt": msg,
                    "dataset": [],
                    "sources": [],
                    "steps": steps
                }

            # 3. SynthesisAgent
            synthesized = self.synthesis_agent.process(
                prompt=prompt_clean,
                extracted_data=extracted_data,
                target_format=instructions.get("target_format", "summary")
            )
            dataset = synthesized.get("dataset", [])
            summary = synthesized.get("summary", "")
            steps.append({
                "agent": "SynthesisAgent",
                "status": "completed",
                "description": f"Synthesized response ({len(dataset)} structured record(s) generated)"
            })

            # 4. ValidationAgent
            validation = self.validation_agent.process(
                prompt=prompt_clean,
                extracted_data=extracted_data,
                synthesized_output=synthesized
            )
            steps.append({
                "agent": "ValidationAgent",
                "status": "completed",
                "description": validation.get("feedback", "Validation passed")
            })

            # Format sources for presentation
            formatted_sources = []
            for item in extracted_data:
                formatted_sources.append({
                    "filename": item.get("filename", "unknown"),
                    "content": item.get("content", "")[:250],
                    "score": item.get("score", 1.0)
                })

            self.context += f"\nUser: {prompt_clean}\nAssistant: {summary}"

            return {
                "agent": "synthesis",
                "message": summary,
                "prompt": summary,
                "dataset": dataset,
                "sources": formatted_sources,
                "steps": steps,
                "validation": validation
            }

        except Exception as e:
            logger.error(f"Error in master agent pipeline: {e}", exc_info=True)
            err_msg = f"An error occurred while processing your query: {str(e)}"
            return {
                "agent": "conversation",
                "message": err_msg,
                "prompt": err_msg,
                "dataset": [],
                "sources": [],
                "steps": steps + [{"agent": "MasterAgent", "status": "error", "description": str(e)}]
            }