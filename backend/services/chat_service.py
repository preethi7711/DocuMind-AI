"""
DocuMind AI — Chat Service
============================
WHY WE NEED THIS:
    This service orchestrates the RAG lifecycle:
    1. Retrieve Context
    2. Format Prompts
    3. Call LLM
    4. Build Response with Citations
"""

from loguru import logger

from backend.api.schemas.chat import ChatRequest, ChatResponse
from backend.rag.retriever import Retriever
from backend.rag.prompts import Prompts
from backend.rag.llm_client import get_ollama_client

class ChatService:
    """Orchestrates Retrieval-Augmented Generation."""

    @staticmethod
    def _sanitize_answer(answer: str) -> str:
        """Remove private-analysis wrappers and answer labels from model output."""
        import re

        cleaned = re.sub(r"<analysis>.*?</analysis>", "", answer, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"^\s*(final\s+answer\s*:)\s*", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    @staticmethod
    async def process_chat(request: ChatRequest) -> ChatResponse:
        """
        Executes a RAG query against a specific document.
        """
        if not request.messages:
            raise ValueError("No messages provided in chat request.")
            
        # 1. Get the actual user question (the last message)
        user_question = request.messages[-1].content
        logger.info(f"Processing RAG chat for doc {request.document_id}. Query: '{user_question}'")
        
        # 2. Semantic Retrieval
        # We run the synchronous retrieval in a thread pool to avoid blocking the event loop.
        from fastapi.concurrency import run_in_threadpool
        context, citations, trace = await run_in_threadpool(
            Retriever.retrieve_context, 
            user_question, 
            request.document_id,
            request.debug
        )
        
        # 3. Assemble Prompts
        system_prompt = Prompts.RAG_SYSTEM_PROMPT
        user_prompt = Prompts.RAG_USER_PROMPT.format(
            context=context,
            question=user_question
        )
        
        # 4. LLM Generation
        llm = get_ollama_client()
        
        if request.stream:
            # Phase 8: Streaming SSE
            async def event_generator():
                import json
                
                # Send metadata first (citations, trace)
                yield f"data: {json.dumps({'type': 'citations', 'citations': [c.model_dump() for c in citations]})}\n\n"
                if trace:
                    yield f"data: {json.dumps({'type': 'trace', 'trace': trace})}\n\n"
                    
                # Generate then sanitize before sending. This prevents hidden
                # analysis blocks from flashing in the UI.
                answer = await llm.generate_chat(system_prompt, user_prompt)
                answer = ChatService._sanitize_answer(answer)
                yield f"data: {json.dumps({'type': 'chunk', 'content': answer})}\n\n"
                    
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
            return event_generator()
        else:
            answer = await llm.generate_chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            answer = ChatService._sanitize_answer(answer)
            
            logger.info("Successfully generated RAG response.")
            return ChatResponse(
                answer=answer,
                citations=citations,
                trace=trace
            )
