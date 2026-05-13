"""
DocuMind AI — Chat API Routes
===============================
WHY THIS ROUTE?
    This allows the frontend to send queries and receive LLM answers with citations.
"""

from fastapi import APIRouter, HTTPException

from backend.api.schemas.responses import SuccessResponse
from backend.api.schemas.chat import ChatRequest, ChatResponse
from backend.services.chat_service import ChatService

router = APIRouter(
    prefix="/chat",
    tags=["RAG Chat"],
)

from fastapi.responses import StreamingResponse
from typing import Union

@router.post(
    "",
    response_model=None, # Dynamic response type
    summary="Ask a Question",
    description="Queries the document using Retrieval-Augmented Generation (RAG). Supports SSE streaming if stream=True.",
)
async def ask_question(request: ChatRequest) -> Union[SuccessResponse[ChatResponse], StreamingResponse]:
    """Phase 8 — Ask a Question Endpoint with SSE Streaming"""
    try:
        response_data = await ChatService.process_chat(request)
        
        if request.stream:
            return StreamingResponse(
                response_data, # This is an AsyncGenerator
                media_type="text/event-stream"
            )
            
        return SuccessResponse(
            success=True,
            message="Successfully generated answer.",
            data=response_data
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat generation failed: {str(e)}")
