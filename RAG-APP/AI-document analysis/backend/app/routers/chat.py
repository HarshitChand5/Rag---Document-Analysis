import re
import json
import asyncio
import logging
from fastapi import APIRouter, HTTPException  # type: ignore
from fastapi.responses import StreamingResponse  # type: ignore
from app.models import ChatRequest, ChatResponse  # type: ignore
from app.services.ai_researcher import get_research_response  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.project_id or not request.question:
        raise HTTPException(status_code=400, detail="project_id and question are required")

    logger.info("Chat request - project: %s", request.project_id)

    try:
        result = await get_research_response(request.project_id, request.question)
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            answer_source=result["answer_source"],
        )
    except Exception as exc:
        logger.error("Chat error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(exc)}")

@router.post("/chat-stream")
async def chat_stream(request: ChatRequest):
    if not request.project_id or not request.question:
        raise HTTPException(status_code=400, detail="project_id and question are required")

    logger.info("Chat stream request - project: %s", request.project_id)

    async def generate():
        try:
            result = await get_research_response(request.project_id, request.question)
            answer = result["answer"]
            sources = result["sources"]
            answer_source = result["answer_source"]

            sentences = re.split(r'(?<=[\.!\?\n])\s+', answer)
            for sentence in sentences:
                if sentence.strip():
                    yield f"data: {sentence} \n\n"
                    await asyncio.sleep(0.03)

            yield f"data: [SOURCE_TYPE]{answer_source}\n\n"
            yield f"data: [SOURCES]{json.dumps(sources)}\n\n"
        except Exception as exc:
            logger.error("Chat stream error: %s", exc)
            yield f"data: [ERROR]{str(exc)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
